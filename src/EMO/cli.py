from dataclasses import dataclass
import logging
from utils import Config
from DBAC.api import DbOperator
from EMO.models import MODEL_APPROACHES, Models
import EMO.augmentation as augmentation

log = logging.getLogger("EFC")


@dataclass
class SubStep:
    disp = False
    capture = False
    accepted = False

    def __bool__(self):
        return self.disp or self.capture

    def __str__(self):
        return f"disp:{self.disp} capture:{self.capture} accepted:{self.accepted}"

    def turn_off(self):
        self.disp = False
        self.capture = False


@dataclass
class Step:
    err = SubStep()
    configure_lngs = SubStep()
    configure_approach = SubStep()
    run_emo = SubStep()
    model_selection = SubStep()
    examples = SubStep()
    done = SubStep()


class CLI:
    def __init__(self, sout):
        self.config = Config()
        self.err_msg = ""
        self.step = Step()
        self.discretizer = None
        self.sout = sout
        self.models_creator = Models()
        self.db = DbOperator()
        self.db.refresh()
        self.__setup_discretizer()

    def __setup_discretizer(self):
        """If discretizer is specified in Config but not available show an Error"""
        self.DICSRETIZERS = {
            "yeo-johnson": augmentation.transformation_yeo_johnson,
            "decision-tree": augmentation.decision_tree_discretizer,
        }
        if disc := self.config["EMO"].get("discretizer"):
            if disc not in self.DICSRETIZERS.keys():
                self.err_msg = (
                    f"Discretizer '{disc}' not in {list(self.DICSRETIZERS.keys())} "
                )
                self.step.done.disp = True

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

    def configure_emo_lngs(self, parsed_cmd: list):
        if self.step.configure_lngs.disp:
            self.__lngs = self.db.get_unique_languages()
            self.set_output_prompt("By index: ")
            self.send_output(
                (
                    "Languages to be used for training the model\n"
                    + "\n".join([f"{i+1}. {v}" for i, v in enumerate(self.__lngs)])
                    + "\n"
                    + self.sout.mw.CONSOLE_PROMPT
                )
            )
            self.step.configure_lngs.disp = False
            self.step.configure_lngs.capture = True
        elif self.step.configure_lngs.capture:
            if parsed_cmd == [""]:
                self.step.configure_lngs.turn_off()
                self.step.done.disp = True
                self.err_msg = ""
                return
            try:
                self.selected_lngs = tuple(self.__lngs[int(i) - 1] for i in parsed_cmd)
                self.step.configure_lngs.turn_off()
                self.step.configure_approach.disp = True
                log.debug(f"Selected languages: {self.selected_lngs}")
            except Exception as e:
                self.err_msg = str(e)
                self.step.err.disp = True

    def configure_emo_approach(self, parsed_cmd: list):
        if self.step.configure_approach.disp:
            self.cls()
            self.set_output_prompt("By index: ")
            self.send_output(
                (
                    "Select approach\n"
                    + "\n".join([f"{i+1}. {v}" for i, v in enumerate(MODEL_APPROACHES)])
                )
            )
            self.step.configure_approach.disp = False
            self.step.configure_approach.capture = True
        elif self.step.configure_approach.capture:
            if parsed_cmd == [""]:
                self.step.configure_approach.turn_off()
                self.step.done.disp = True
                self.err_msg = ""
                return
            try:
                self.selected_approach = MODEL_APPROACHES[int(parsed_cmd[0]) - 1]
                self.step.configure_approach.turn_off()
                self.step.run_emo.disp = True
                log.debug(f"Selected approach: {self.selected_approach}")
            except Exception as e:
                self.err_msg = str(e)
                self.step.err.disp = True

    def run_emo(self, parsed_cmd: list):
        self.step.run_emo.disp = False
        self.cls()
        self.send_output("Starting EFC Optimizer... OK")

        data_prepare_success, msg = self.prepare_data()
        if not data_prepare_success:
            self.step.err.disp = True
            self.err_msg = msg
            return

        # CST model must be trained on raw data
        self.prt_res(
            self.models_creator.prep_CST, "Preparing CST model... ", self.db.db
        )
        self.prt_res(self.models_creator.eval_CST, "Evaluating CST model... ")

        self.prepare_augmentation()
        self.prepare_models()
        self.available_models = self.models_creator.models.keys()
        self.step.model_selection.disp = True

    def prepare_data(self):
        self.prt_res(self.db.refresh, "Loading data... ")
        self.send_output("Filtering... ")
        self.db.filter_for_efc_model(self.selected_lngs)
        if len(self.db.db) >= self.config["EMO"]["min_records"]:
            self.send_output("OK", include_newline=False)
            self.send_output(f"{len(self.db.db)} records submitted")
        else:
            self.send_output("FAILED", include_newline=False)
            msg = f"Not enough records in database: {len(self.db.db)}/{self.config['EMO']['min_records']}. Exiting..."
            return False, msg
        self.prt_res(
            self.db.add_efc_metrics, "Creating metrics... ", fill_timespent=True
        )
        self.prt_res(
            self.db.remove_cols_for_efc_model,
            "Dropping obsolete columns... ",
            drop_lng=self.selected_approach == MODEL_APPROACHES[0],
        )
        if self.selected_approach == MODEL_APPROACHES[1]:
            self.prt_res(
                self.db.encode_language_columns,
                "Encoding Language columns...",
                lngs=self.selected_lngs,
            )
            # Rearrange columns
            self.db.db = self.db.db[
                [c for c in self.db.db.columns if c != "SCORE"] + ["SCORE"]
            ]
        return True, "OK"

    def prepare_augmentation(self):
        self.db.db = self.prt_res(
            augmentation.cap_quantiles, "Capping quantiles... ", self.db.db
        )
        if discretizer := self.DICSRETIZERS.get(self.config["EMO"].get("discretizer")):
            self.db.db, self.discretizer = self.prt_res(
                discretizer,
                f"Applying {self.config['EMO']['discretizer']} Discretization... ",
                self.db.db,
            )

    def prepare_models(self):
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

    def show_training_summary(self):
        out = ["MODEL |  EVA  |  MAE  |  MTD  |  PACE  "]
        for model, metrics in self.models_creator.evaluation.items():
            ev, mae, mtd, actual, preds = metrics
            d = sum(actual) / len(actual) - sum(p[0] for p in preds) / len(preds)
            if d >= 10:
                pace = "fast"
            elif d <= -10:
                pace = "slow"
            else:
                pace = "normal"
            out.append(
                f"{model:^5} | {ev:^5.0%} | {mae:^5.0f} | {mtd:^5.0f} | {pace:^6}"
            )
        self.send_output("\n".join(out))

    def model_selection(self, parsed_cmd: list):
        if self.step.model_selection.disp:
            self.set_output_prompt("Pick a model: ")
            self.cls()
            self.show_training_summary()
            self.step.model_selection.capture = True
            self.step.model_selection.disp = False
        elif self.step.model_selection.capture:
            sel_model = parsed_cmd[0].upper()
            if not sel_model:
                self.send_output("Model Selection cancelled")
                self.step.model_selection.turn_off()
                self.step.done.disp = True
            elif sel_model not in self.available_models:
                self.cls()
                self.send_output("Selected model is not available. Try again")
                self.set_output_prompt("Press Enter to continue...")
                self.step.model_selection.disp = True
                self.step.model_selection.capture = False
            else:
                self.selected_model = sel_model
                self.step.model_selection.turn_off()
                self.step.examples.disp = True
                self.send_output("Preparing examples...")

    def show_examples(self, parsed_cmd: list):
        if self.step.examples.disp:
            self.set_output_prompt("Approve [Y/n]: ")
            self.cls()
            self.send_output(f"______ {self.selected_model} ______")
            *_, values, preds = self.models_creator.evaluation[self.selected_model]

            diffs = (preds - values) / values
            self.send_output("PRED | TRUE | DIFF%")
            for i in range(min(len(values), 10)):
                self.send_output(
                    f"{preds[i][0]:^4.0f} | {values[i][0]:^4.0f} | {diffs[i][0]:>4.0%}"
                )
            self.step.examples.disp = False
            self.step.examples.capture = True
        elif self.step.examples.capture:
            if parsed_cmd[0].lower() in {"yes", "y", "1"}:
                self.update_config_with_new_model()
                self.step.examples.accepted = True
            else:
                self.step.examples.turn_off()
                self.step.model_selection.disp = True
                self.model_selection([])

    def update_config_with_new_model(self):
        self.models_creator.save_model(
            self.selected_model,
            discretizer=self.discretizer,
            lng_cols=self.selected_lngs,
            approach=self.selected_approach,
        )
        self.set_output_prompt("Press Enter to continue...")
        self.send_output(
            f"Applied new {self.selected_approach} model: {self.selected_model}"
        )
        self.step.done.disp = True
