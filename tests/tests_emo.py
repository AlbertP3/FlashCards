from unittest import TestCase, mock
import pandas as pd
import numpy as np
import os
import sys

import joblib
import logging
from utils import Config
from DBAC.api import db_interface
import EMO.models as models
import EMO.augmentation as augmentation
import EMO.cli as emo_cli

log = logging.getLogger(__name__)
config = Config()
T_PATH = './scripts/tests/res'
config.update({
    'lngs_path': os.path.join(T_PATH, 'languages'),
    'revs_path': os.path.join(T_PATH,'revisions'),
    'db_path': os.path.join(T_PATH, 'resources/rev_db.csv'),
    'sod_filepath':os.path.join(T_PATH,'languages/example.csv'),
    'resources_path': os.path.join(T_PATH, 'resources'),
})


EXAMPLE_RECORDS = [
    [75, 13.043478260869565, 7890.390833333333, 1599.8863888888889, 14, 92],
    [65, 12.956810631229235, 3762.4519444444445, 579.1197222222222, 9, 67],
    [104, 17.577464788732396, 5612.822222222222, 504.8491666666667, 12, 88],
    [49, 18.846153846153847, 7441.532222222222, 518.0544444444445, 14, 77],
    [100, 19.292604501607716, 6550.613333333334, 409.0411111111111, 13, 87],
    [120, 17.77777777777778, 4561.831666666667, 403.8283333333333, 10, 77],
    [80, 18.045112781954888, 3433.7361111111113, 13.553055555555556, 10, 82],
    [65, 19.79695431472081, 8295.898888888889, 405.99611111111113, 16, 84],
    [62, 17.464788732394368, 8085.379722222222, 404.29777777777775, 15, 82],
    [69, 17.394957983193276, 7221.8533333333335, 517.7583333333333, 14, 97],
]


class Test_data_prep(TestCase):
    
    def setUp(self):
        self.dbapi = db_interface()
        self.dbapi.refresh()


    def test_filter(self):
        pre_len = len(self.dbapi.db)
        self.dbapi.filter_for_efc_model()
        filtered = self.dbapi.db
        self.assertLess(len(filtered), pre_len)

        de_count = len([r for r in filtered['SIGNATURE'].values.tolist() if '_mistakes' in r])
        self.assertEqual(de_count, 0)

        en_count = len([r for r in filtered['SIGNATURE'].values.tolist() if 'EN' in r])
        self.assertEqual(en_count, filtered.shape[0])

        non_pos_count = len([r for r in filtered['POSITIVES'].values.tolist() if r == 0])
        self.assertEqual(non_pos_count, 0)

    def test_drop_cols(self):
        self.dbapi.remove_cols_for_efc_model()
        self.assertNotIn('SIGNATURE', self.dbapi.db.columns)
        self.assertIn('TOTAL', self.dbapi.db.columns)
    
    def test_create_metrics(self):
        self.dbapi.filter_for_efc_model()
        self.dbapi.add_efc_metrics()

        modb_part = self.dbapi.db.loc[self.dbapi.db['SIGNATURE'] == 'REV_EN10092021164327']
        self.assertEqual(str(modb_part['TIMESTAMP'].values[0]), '2021-10-18T10:00:06.000000000')
        self.assertEqual(modb_part['TIMEDELTA_SINCE_CREATION'].to_list()[:9], [216,240,1235,1885,2525,3413,4616,5863,7705])
        self.assertEqual(modb_part['TIMEDELTA_LAST_REV'].to_list()[:9], [86, 24, 995, 650, 640, 888, 1203, 1246, 1842])
        self.assertEqual(modb_part['CUM_CNT_REVS'].to_list()[:9], [int(config['init_revs_cnt'])+i for i in range(1, 10)])



class Test_models_creator(TestCase):
    
    def setUp(self):
        self.dbapi = db_interface()
        self.dbapi.refresh()
        self.dbapi.filter_for_efc_model()
        self.dbapi.add_efc_metrics()
        self.dbapi.remove_cols_for_efc_model()
        self.models_creator = models.Models()

    def test_model_svm(self):
        self.models_creator.prep_SVM(self.dbapi.db)
        self.models_creator.eval_SVM()
        # log.info(self.models_creator.models['SVM'])

    def test_model_las(self):
        self.models_creator.prep_LASSO(self.dbapi.db)
        self.models_creator.eval_LASSO()
        log.info(self.models_creator.evaluation['LAS'])

    def test_model_cst(self):
        self.models_creator.prep_CST(self.dbapi.db)
        self.models_creator.eval_CST()
        log.info(self.models_creator.evaluation['CST'][:3])

    def test_model_rfr(self):
        self.models_creator.prep_RFR(self.dbapi.db)
        self.models_creator.eval_RFR()
        log.info(self.models_creator.evaluation['RFR'])

    def test_aug_cap(self):
        augmentation.cap_quantiles(self.dbapi.db)

    def test_aug_discretization_dtd(self):
        augmentation.decision_tree_discretizer(self.dbapi.db)



class Test_CLI(TestCase):
    
    def setUp(self):
        self.registry = list()
        output = mock.Mock()
        output.cls = lambda: self.registry.clear()
        self.cli = emo_cli.CLI(output)
        self.cli.send_output = self._send_output

    def _send_output(self, text:str, include_newline=True):
        if include_newline: self.registry.append(text)
        else: self.registry[-1]+=text

    def _prepare_data(self):
        self.dbapi = db_interface()
        self.dbapi.refresh()
        self.dbapi.filter_for_efc_model()
        self.dbapi.add_efc_metrics()
        self.dbapi.remove_cols_for_efc_model()

    def test_quality_of_data(self):
        self._prepare_data()
        # self.dbapi.db.to_csv('scripts/tests/res/watch.csv')

    def test_prepare_data(self):
        self.cli.prepare_data()
        log.info(self.registry)

    def test_augment_data(self):
        self._prepare_data()
        self.cli.prepare_augmentation()
        log.info(self.registry)
    
    def test_prep_models(self):
        self._prepare_data()
        self.cli.prepare_models()
        self.cli.prepare_models()
        log.info(self.registry)

    def test_show_training_summary(self):
        self._prepare_data()
        self.cli.models_creator.prep_SVM(self.dbapi.db)
        self.cli.models_creator.prep_LASSO(self.dbapi.db)
        self.cli.models_creator.prep_CST(self.dbapi.db)
        self.cli.models_creator.prep_RFR(self.dbapi.db)
        self.cli.models_creator.eval_SVM()
        self.cli.models_creator.eval_RFR()
        self.cli.models_creator.eval_CST()
        self.cli.models_creator.eval_LASSO()
        self.cli.show_training_summary()
        log.info('\n' + '\n'.join(self.registry))

    def test_show_examples(self):
        self._prepare_data()
        self.cli.models_creator.prep_SVM(self.dbapi.db)
        self.cli.models_creator.eval_SVM()
        self.cli.selected_model = 'SVM'
        self.cli.show_examples()
        log.info('\n' + '\n'.join(self.registry))

    def test_save_model_CST(self):
        self._prepare_data()
        self.cli.models_creator.prep_CST(self.dbapi.db)
        self.cli.models_creator.save_model('CST')
        model = joblib.load(os.path.join(config['resources_path'],'efc_models', 'CST.pkl'))
        results = model.predict([[100, 15, 24*30, 24*7, 3, 65],
                                [98, 15, 24*30, 24, 5, 80]])
        log.info(model.name)
        log.info(results)

    def test_save_model_SVM(self):
        self._prepare_data()
        self.cli.models_creator.prep_SVM(self.dbapi.db)
        self.cli.models_creator.save_model('SVM')
        model = joblib.load(os.path.join(config['resources_path'],'efc_models', 'SVM.pkl'))
        results = model.predict([[100, 15, 24*30, 24*7, 3, 65],
                                [98, 15, 24*30, 24, 5, 80]])
        log.info(model.name)
        log.info(results)

    def test_save_model_LAS(self):
        self._prepare_data()
        self.cli.models_creator.prep_LASSO(self.dbapi.db)
        self.cli.models_creator.save_model('LAS')
        model = joblib.load(os.path.join(config['resources_path'],'efc_models', 'LAS.pkl'))
        results = model.predict(EXAMPLE_RECORDS)
        log.info(model.name)
        log.info(results)
        self.assertEqual(len(EXAMPLE_RECORDS), len(results))

    def test_save_model_RFR(self):
        self._prepare_data()
        self.cli.models_creator.prep_RFR(self.dbapi.db)
        self.cli.models_creator.save_model('RFR')
        model = joblib.load(os.path.join(config['resources_path'],'efc_models', 'RFR.pkl'))
        results = model.predict(EXAMPLE_RECORDS)
        log.info(model.name)
        log.info(results)
        self.assertEqual(len(EXAMPLE_RECORDS), len(results))

    def test_run_emo(self):
        self._prepare_data()
        self.cli.run_emo([])
        log.info(self.registry)
