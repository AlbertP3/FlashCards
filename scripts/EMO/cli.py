from utils import Config, register_log
from db_api import db_interface
import EMO.models as models
import EMO.augmentation as augmentation



class CLI():
    
    def __init__(self, sout):
        self.config = Config()
        self.sout = sout
        self.models_creator = models.Models()
        self.dbapi = db_interface()
        self.STEP_RUN_EMO = False
        self.STEP_MODEL_SELECTION = False
        self.STEP_APPROVE_CHANGES = False
        self.STEP_SAVE_SUCCESS = False


    def send_output(self, text:str, include_newline=True):
        if include_newline:
            self.sout.console.append(text)
        else:
            self.sout.console.setText(self.sout.console.toPlainText()+text)


    def set_output_prompt(self, t):
        self.sout.mw.CONSOLE_PROMPT = t


    def cls(self):
        self.sout.cls()


    def prt_res(self, func, msg, *args, **kwargs):
        self.send_output(msg)
        res = func(*args, **kwargs)
        self.send_output('OK', include_newline=False)
        return res


    def run_emo(self, parsed_cmd:list):
        self.send_output('Starting EFC Optimizer... OK') 
        self.STEP_RUN_EMO = False

        data_prepare_success = self.prepare_data()
        if not data_prepare_success: return

        # self.prepare_augmentation()
        self.prepare_models()
        self.available_models = self.models_creator.models.keys()
        self.cls()
        self.show_training_summary()

        self.STEP_MODEL_SELECTION = True
        self.set_output_prompt('Pick a model: ')
        self.send_output(self.sout.mw.CONSOLE_PROMPT)


    def prepare_data(self):
        self.prt_res(self.dbapi.refresh, 'Loading data... ')

        self.send_output('Filtering... ')
        self.dbapi.filter_for_efc_model()
        if len(self.dbapi.db) > 100:
            self.send_output('OK', include_newline=False)
            self.send_output(f'{len(self.dbapi.db)} records submitted')
        else:
            self.send_output('FAIL', include_newline=False)
            self.send_output(f'Not enough records in database: {len(self.dbapi.db)}/100. Exiting...')
            return False

        self.prt_res(self.dbapi.add_efc_metrics, 'Creating metrics... ', fill_timespent=True)
        self.prt_res(self.dbapi.remove_cols_for_efc_model, 'Dropping obsolete columns... ')
        return True


    def prepare_augmentation(self):
        self.dbapi.db = self.prt_res(augmentation.cap_quantiles, 'Capping quantiles... ', self.dbapi.db)
        self.dbapi.db = self.prt_res(augmentation.decision_tree_discretizer, 'Applying decision tree discretizer... ', self.dbapi.db)


    def prepare_models(self):
        self.prt_res(self.models_creator.prep_LASSO, 'Preparing LASSO model... ', self.dbapi.db)
        self.prt_res(self.models_creator.eval_LASSO, 'Evaluating LASSO model... ')
        self.prt_res(self.models_creator.prep_SVM, 'Preparing SVM model... ', self.dbapi.db)
        self.prt_res(self.models_creator.eval_SVM, 'Evaluating SVM model... ')
        self.prt_res(self.models_creator.prep_RFR, 'Preparing RFR model... ', self.dbapi.db)
        self.prt_res(self.models_creator.eval_RFR, 'Evaluating RFR model... ')
        self.prt_res(self.models_creator.prep_CST, 'Preparing CST model... ', self.dbapi.db)
        self.prt_res(self.models_creator.eval_CST, 'Evaluating CST model... ')


    def show_training_summary(self):
        self.send_output('MODEL |  EVA  |  MAE  |  MTD  ')
        for model, metrics in self.models_creator.evaluation.items():
            ev, mae, mtd, *_ = metrics
            self.send_output(f'{model:^5} | {ev:^5.0%} | {mae:^5.0f} | {mtd:^5.0f}')


    def model_selection(self, parsed_cmd:list):
        sel_model = parsed_cmd[0].upper()

        if not sel_model:
            self.STEP_MODEL_SELECTION = False
            self.send_output('Model Selection cancelled')
            return

        if sel_model not in self.available_models:
            self.send_output('Selected model is not available. Try again')
        else:
            self.selected_model = sel_model
            self.send_output('Preparing examples...')
            self.cls()
            self.show_examples()
            self.STEP_MODEL_SELECTION = False
            self.STEP_APPROVE_CHANGES = True
            self.set_output_prompt('Approve [Y/n]: ')


    def show_examples(self):
        self.send_output(f'______ {self.selected_model} ______')
        *_, values, preds = self.models_creator.evaluation[self.selected_model]

        diffs = (preds - values) / values
        self.send_output('PRED | TRUE | DIF%')
        for i in range(min(len(values), 10)):
            self.send_output(f'{preds[i][0]:^4.0f} | {values[i][0]:^4.0f} | {diffs[i][0]:>4.0%}')

         
    def approve_changes(self, parsed_cmd:list):
        if parsed_cmd[0] in {'y','Y','yes','Yes'}:
            self.update_config_with_new_model()                
            self.STEP_APPROVE_CHANGES = False
        else:
            self.send_output('Changes declined')
            self.cls()
            self.show_training_summary()
            self.set_output_prompt('Pick a model: ')
            self.STEP_APPROVE_CHANGES = False
            self.STEP_MODEL_SELECTION = True


    def update_config_with_new_model(self):
        self.STEP_SAVE_SUCCESS = self.models_creator.save_model(self.selected_model)
        self.config.update({'efc_model': self.selected_model})
        self.send_output('CONFIG UPDATED WITH A NEW MODEL')


