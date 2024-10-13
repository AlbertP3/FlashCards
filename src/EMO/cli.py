from dataclasses import dataclass
import logging
from utils import fcc_queue
from cfg import config
from DBAC.api import DbOperator
from EMO.models import Models, EMOApproaches
import EMO.augmentation as augmentation

log = logging.getLogger("EMO")


@dataclass
class Steps:
    model_display = "model_display"
    model_selection = "model_selection"
    examples_display = "examples_display"
    done = "done"
    decide_model = "decide_model"
    decide_exit = "decide_exit"


class CLI:
    def __init__(self, sout):
        self.config = config
        self.err_msg = ""
        self.step = None
        self.discretizer = None
        self.sout = sout
        self.__verify_discretizer()
        self.models_creator = Models()
        self.db = DbOperator()
        self.accepted = False

    def __verify_discretizer(self):
        self.DICSRETIZERS = {
            "yeo-johnson": augmentation.transformation_yeo_johnson,
            "decision-tree": augmentation.decision_tree_discretizer,
        }
        if disc := self.config["EMO"].get("discretizer"):
            if disc not in self.DICSRETIZERS.keys():
                raise KeyError(
                    f"Discretizer '{disc}' not in {list(self.DICSRETIZERS.keys())} "
                )

    def send_output(self, text: str, include_newline=True):
        if include_newline:
            self.sout.console.append(text)
            self.sout.mw.CONSOLE_LOG.append(text)
        else:
            new_text = self.sout.console.toPlainText() + text
            self.sout.console.setText(new_text)
            self.sout.mw.CONSOLE_LOG = new_text.split("\n")

    def set_output_prompt(self, t):
        self.sout.mw.CONSOLE_PROMPT = t

    def cls(self, *args, **kwargs):
        self.sout.console.setText("")
        self.sout.mw.CONSOLE_LOG = []

    def prt_res(self, func, msg, *args, **kwargs):
        self.send_output(msg)
        res = func(*args, **kwargs)
        self.send_output("OK", include_newline=False)
        return res

    def set_emo_lngs(self, lngs: list):
        self.selected_lngs = lngs
        log.debug(f"Selected languages: {self.selected_lngs}")

    def set_emo_approach(self, approach: str):
        if approach not in {i.value for i in EMOApproaches}:
            raise KeyError(f"Unknown approach: '{approach}'. ")
        self.selected_approach = approach
        log.debug(f"Selected approach: {self.selected_approach}")

    def run_emo(self):
        self.cls()
        self.send_output("Starting EFC Optimizer... OK")
        self._prepare_data()
        # CST model must be trained on raw data
        self.prt_res(
            self.models_creator.prep_CST, "Preparing CST model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_CST, "Evaluating CST model... ")

        self._prepare_augmentation()
        self._prepare_models()
        self.available_models = self.models_creator.models.keys()

    def _prepare_data(self):
        self.prt_res(self.db.refresh, "Loading data... ")
        self.send_output("Filtering... ")
        self.db.filter_for_efc_model(self.selected_lngs)
        if len(self.db.db) >= self.config["EMO"]["min_records"]:
            self.send_output("OK", include_newline=False)
            self.send_output(f"{len(self.db.db)} records submitted")
        else:
            self.send_output("FAILED", include_newline=False)
            raise Exception(
                f"Not enough records in database: {len(self.db.db)}/{self.config['EMO']['min_records']}. "
            )
        self.prt_res(
            self.db.add_efc_metrics, "Creating metrics... ", fill_timespent=True
        )
        self.prt_res(
            self.db.remove_cols_for_efc_model,
            "Dropping obsolete columns... ",
            drop_lng=self.selected_approach == EMOApproaches.universal.value,
        )
        if self.selected_approach == EMOApproaches.language_specific.value:
            self.prt_res(
                self.db.encode_language_columns,
                "Encoding Language columns...",
                lngs=self.selected_lngs,
            )
            # Rearrange columns
            self.db.db = self.db.db[
                [c for c in self.db.db.columns if c != "SCORE"] + ["SCORE"]
            ]

    def _prepare_augmentation(self):
        self.db.db = self.prt_res(
            augmentation.cap_quantiles, "Capping quantiles... ", self.db.db
        )
        if discretizer := self.DICSRETIZERS[self.config["EMO"]["discretizer"]]:
            self.db.db, self.discretizer = self.prt_res(
                discretizer,
                f"Applying {self.config['EMO']['discretizer']} Discretization... ",
                self.db.db,
            )
            log.debug(f"Applied {self.config['EMO']['discretizer']} Discretization")

    def _prepare_models(self):
        self.prt_res(
            self.models_creator.prep_LASSO, "Preparing LASSO model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_LASSO, "Evaluating LASSO model... ")
        self.prt_res(
            self.models_creator.prep_SVR, "Preparing SVR model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_SVR, "Evaluating SVR model... ")
        self.prt_res(
            self.models_creator.prep_RFR, "Preparing RFR model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_RFR, "Evaluating RFR model... ")
        self.prt_res(
            self.models_creator.prep_XGB, "Preparing XGB model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_XGB, "Evaluating XGB model... ")

    def _show_training_summary(self):
        out = ["MODEL |  EVA  |  MAE  |  MTD  |  PACE  "]
        for model, metrics in self.models_creator.evaluation.items():
            ev, mae, mtd, actual, preds = metrics
            d = sum(actual) / len(actual) - sum(p[0] for p in preds) / len(preds)
            if d >= 2:
                pace = "fast"
            elif d <= -2:
                pace = "slow"
            else:
                pace = "normal"
            out.append(
                f"{model:^5} | {ev:^5.0%} | {mae:^5.0f} | {mtd:^5.0f} | {pace:^6}"
            )
        self.send_output("\n".join(out))

    def show_model_stats(self):
        self.set_output_prompt("Pick a model: ")
        self.cls()
        self._show_training_summary()
        self.step = Steps.model_selection

    def model_selection(self, parsed_cmd: list):
        sel_model = parsed_cmd[0].upper()
        if not sel_model:
            self.step = Steps.done
            fcc_queue.put("Model Selection cancelled")
        elif sel_model not in self.available_models:
            self.cls()
            self.send_output("Selected model is not available. Try again")
            self.set_output_prompt("Press Enter to continue...")
            self.step = Steps.model_display
        else:
            self.selected_model = sel_model
            self.step = Steps.examples_display
            self.send_output("Preparing examples...")
            self.show_examples()

    def show_examples(self):
        self.set_output_prompt("Approve [Y/n]: ")
        self.cls()
        self.send_output(f"_______ {self.selected_model} _______")
        *_, values, preds = self.models_creator.evaluation[self.selected_model]

        diffs = (preds - values) / values
        self.send_output("PRED | TRUE | DIFF%")
        for i in range(min(len(values), 10)):
            self.send_output(
                f"{preds[i][0]:^4.0f} | {values[i][0]:^4.0f} | {diffs[i][0]:>4.0%}"
            )
        self.step = Steps.decide_model

    def decide_model(self, parsed_cmd: list):
        if parsed_cmd[0].lower() in {"yes", "y", "1"}:
            self._update_config_with_new_model()
            self.accepted = True
            self.step = Steps.done
        else:
            self.show_model_stats()

    def _update_config_with_new_model(self):
        self.models_creator.save_model(
            self.selected_model,
            discretizer=self.discretizer,
            lng_cols=self.selected_lngs,
            approach=self.selected_approach,
        )
        self.set_output_prompt("Press Enter to continue...")
        fcc_queue.put(
            f"Applied new {self.selected_approach} model: {self.selected_model}"
        )

    def prepare_exit(self):
        self.cls()
        self.set_output_prompt("Are you sure you want to exit? [Y/n]: ")
        self.send_output("")
        self.step = Steps.decide_exit
