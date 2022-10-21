import sys
import os
from PyQt5.QtCore import Qt, QTimer
from threading import Thread

from pandas.core.dtypes.missing import partial

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import unittest
from unittest.mock import patch, Mock
import pandas as pd
from utils import *
import db_api
from datetime import datetime, date, timedelta
import main_window_logic
import main_window_gui
import efc
from fcc import fcc
import stats
from random import randint
from rev_summary import summary_generator
import time


config = Config()
T_PATH = './scripts/tests/res'
config.update({
    'lngs_path': os.path.join(T_PATH, 'languages'),
    'revs_path': os.path.join(T_PATH,'revisions'),
    'db_path': os.path.join(T_PATH, 'resources/rev_db.csv'),
    'sod_filepath':os.path.join(T_PATH,'languages/example.csv'),
})

class Test_utils(unittest.TestCase):

    def test_format_timedelta(self):
        example_timedelta_1 = timedelta(days=0, hours=0, minutes=0, seconds=0)
        example_timedelta_2 = timedelta(days=0, hours=0, minutes=0, seconds=1)
        example_timedelta_3 = timedelta(days=0, hours=0, minutes=0, seconds=2)
        example_timedelta_4 = timedelta(days=0, hours=0, minutes=1, seconds=15)
        example_timedelta_6 = timedelta(days=0, hours=1, minutes=23, seconds=12)
        example_timedelta_7 = timedelta(days=0, hours=2, minutes=0, seconds=0)
        example_timedelta_8 = timedelta(days=1, hours=0, minutes=0, seconds=0)
        example_timedelta_9 = timedelta(days=2, hours=4, minutes=15, seconds=43)
        example_timedelta_10 = timedelta(days=64, hours=0, minutes=0, seconds=0)
        example_timedelta_11 = timedelta(days=31, hours=0, minutes=0, seconds=0)
        example_timedelta_12 = timedelta(days=380, hours=0, minutes=0, seconds=0)
        example_timedelta_13 = timedelta(days=480, hours=0, minutes=0, seconds=0)
        
        self.assertEqual(format_timedelta(example_timedelta_1), '0 seconds')
        self.assertEqual(format_timedelta(example_timedelta_2), '1 second')
        self.assertEqual(format_timedelta(example_timedelta_3), '2 seconds')
        self.assertEqual(format_timedelta(example_timedelta_4), '1 minute')
        self.assertEqual(format_timedelta(example_timedelta_6), '1 hour')
        self.assertEqual(format_timedelta(example_timedelta_7), '2 hours')
        self.assertEqual(format_timedelta(example_timedelta_8), '1 day')
        self.assertEqual(format_timedelta(example_timedelta_9), '2 days')
        self.assertEqual(format_timedelta(example_timedelta_10), '2.1 months')
        self.assertEqual(format_timedelta(example_timedelta_11), '1.0 month')
        self.assertEqual(format_timedelta(example_timedelta_12), '1.0 year')
        self.assertEqual(format_timedelta(example_timedelta_13), '1.3 years')
            

    def test_validate_dataset(self):
        ds_correct = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny']})
        ds_one_col = pd.DataFrame(data={'EN':['x', 'y', 'z']})
        ds_three_cols = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny'],
                                        '3rd':['x', 'y', 'z']})
        ds_empty = pd.DataFrame(data={})
        self.assertEqual(dataset_is_valid(ds_correct), True)
        self.assertEqual(dataset_is_valid(ds_one_col), False)
        self.assertEqual(dataset_is_valid(ds_three_cols), True)
        self.assertEqual(dataset_is_valid(ds_empty), False)


    def test_get_lng_from_signature(self):
        with patch('utils.config') as mock_config:
            d = {'languages':{'EN', 'RU'}}
            mock_config.__getitem__.side_effect = d.__getitem__
            s1 = get_lng_from_signature('REV_EN0125370523')
            s2 = get_lng_from_signature('aa_EN23525236')
            s3 = get_lng_from_signature('RU_biesy_part1')     
            s4 = get_lng_from_signature('temp')

        self.assertEqual(s1, 'EN')
        self.assertEqual(s2, 'EN')
        self.assertEqual(s3, 'RU')
        self.assertEqual(s4, 'UNKNOWN')


    def test_update_signature_timestamp(self):
        s1 = 'REV_EN31122022101010'
        s_expected = f"REV_EN{datetime.now().strftime('%m%d%Y%H%M%S')}"
        self.assertEqual(update_signature_timestamp(s1), s_expected)


    def test_get_signature(self):
        filename_1 = 'en'
        filename_2 = 'avw_3aa'
        filename_3 = 'just_a_rev'
        timestamp = datetime.now().strftime('%m%d%Y%H%M%S')

        self.assertEqual(get_signature(filename_1, 'EN',  False), f'REV_EN{timestamp}')
        self.assertEqual(get_signature(filename_2, 'EDB', False), f'REV_EDB{timestamp}')
        self.assertEqual(get_signature(filename_3, 'EN', True), filename_3)


    def test_get_most_similar_file(self):
        self.assertEqual(get_most_similar_file('./languages/', 'en'), 'en.xlsx')
        self.assertEqual(get_most_similar_file('./languages/', 'non-existing', None), None)
        self.assertEqual(get_most_similar_file('./languages/', 'non-existing', 'load_any'), 'de.csv')



class Test_db_api(unittest.TestCase):


    def test_get_db(self):
        dbapi = db_api.db_interface()
        df = dbapi.get_database()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('SIGNATURE', df.columns)

        
    def test_get_date_from_signature(self):
        correct_signature_example_1 = 'REV_RU11252021180131'
        invalid_signature_example_1 = 'wrongfilenametest'
        non_existing_file = 'non-existing_file'
        dbapi = db_api.db_interface()

        self.assertEqual(dbapi.get_first_datetime(correct_signature_example_1), date(2021, 11, 26))
        self.assertEqual(dbapi.get_first_datetime(invalid_signature_example_1), date(1959, 5, 3))
        self.assertEqual(dbapi.get_first_datetime(non_existing_file), None)
    

    def test_get_first_date(self):
        dbapi = db_api.db_interface()
        # db_api.create_record('TEST_SIGNATURE', 0, 0)
        self.assertEqual(dbapi.get_first_datetime('TEST_SIGNATURE'), make_todayte())


    def test_get_first_date_if_file_not_in_db(self):
        dbapi = db_api.db_interface()
        first_date = dbapi.get_first_datetime(get_signature('TEST_FILE_NOT_IN_DB', '', True))
        self.assertEqual(first_date, date(1900, 1, 1))


    def test_get_last_date(self):
        # db_api.create_record('TEST_SIGNATURE', 0, 0)
        dbapi = db_api.db_interface()
        self.assertEqual(dbapi.get_last_datetime('TEST_SIGNATURE'), make_todayte())


    def test_get_newest_record(self):
        lng, expected = 'XT', 'newestXTrevision'
        missing_lng, expected_2 = 'MISSING', ''
        dbapi = db_api.db_interface()

        self.assertEqual(dbapi.get_latest_record_signature(lng), expected)
        self.assertEqual(dbapi.get_latest_record_signature(missing_lng), expected_2)


    def test_create_new_record(self):
        timestamp_str = str(datetime.now().strftime("%Y-%m-%d"))
        signature = 'TEST_CREATE_NEW_RECORD'
        db_api.create_record(signature,0,0)
        dbapi = db_api.db_interface()
        self.assertEqual(str(dbapi.get_last_datetime(signature)), timestamp_str)


    def test_get_timedelta_from_creation(self):
        # db_api.create_record('TEST_SIGNATURE', 0, 0)
        dbapi = db_api.db_interface()
        self.assertEqual(dbapi.get_timedelta_from_creation('TEST_SIGNATURE').days, 5)
        self.assertEqual(dbapi.get_timedelta_from_creation('NONEXISTING_SIGNATURE'), None)


    def test_time_delta_from_last_rev(self):
        # db_api.create_record('TEST_SIGNATURE', 0, 0)
        dbapi = db_api.db_interface()
        self.assertEqual(dbapi.get_timedelta_from_last_rev('TEST_SIGNATURE').days, 5)
        self.assertEqual(dbapi.get_timedelta_from_last_rev('NON-EXISTING_SIGNATURE'), None)


    def test_get_last_positives(self):
        dbapi = db_api.db_interface()
        rev_signature = 'JP_ANIME_60'
        expected = 24
        self.assertEqual(dbapi.get_last_positives(rev_signature), expected)


    def test_get_max_positives_count(self):
        dbapi = db_api.db_interface()
        rev_signature = 'REV_EN01212022204840'
        expected = 62
        self.assertEqual(dbapi.get_max_positives_count(rev_signature), expected)


    def test_filter_lng(self):
        dbapi = db_api.db_interface()
        total = dbapi.get_all()
        db_filtered = dbapi.get_filtered_by_lng('EN')
        self.assertNotEqual(db_filtered.shape[0], 0)
        self.assertLess(db_filtered.shape[0], total.shape[0])



class Test_flashcard_console_commands(unittest.TestCase):

    def setUp(self):
        self.registry = list()
        self.mw = Mock()
        self.mw.console = Mock()
        self.fcc_inst = fcc(self.mw)
        self.fcc_inst.post_fcc = lambda text: self.registry.append(str(text))

    def test_rgd(self):
        config['GEOMETRY'].update({'main':(99,49,49,9)})
        # default specific window
        self.fcc_inst.execute_command(['rgd', 'main'])
        self.assertEqual(config['GEOMETRY']['main'], config['GEOMETRY']['default'])
        # default all windows
        config['GEOMETRY'].update({'main':(100,100,100,100)})
        self.fcc_inst.execute_command(['rgd'])
        for w in config['GEOMETRY'].values():
            self.assertEqual(w, config['GEOMETRY']['default'])
        # try default non-existent window
        self.fcc_inst.execute_command(['rgd', 'nasgas'])
        self.assertIn('does not exist', self.registry[-2])


class Test_FlashCards(unittest.TestCase):
    
    def setUp(self):
        # configuration
        self.registry = list()
        self.mw = main_window_logic.main_window_logic()
        self.gui = main_window_gui.main_window_gui()

        # mock variables
        self.mw.fcc_inst = Mock()
        self.mw.fcc_inst.post_fcc = lambda text: self.registry.append(text)
        self.gui.fcc_inst = Mock()
        self.gui.fcc_inst.post_fcc = lambda text: self.registry.append(text)
       
        # finish loading up
        data = self.mw.load_flashcards(os.path.join(T_PATH,'languages/example.xlsx'))
        self.mw.update_backend_parameters(os.path.join(T_PATH,'languages/example.xlsx'), data)
    

    def test_file_update_timer_dont_run_if_update_interval_0(self):
        # assert will not run if update_interval == 0
        config.update({'file_update_interval':'0'})
        self.gui.initiate_cyclic_file_update()
        self.assertIsNone(self.gui.file_update_timer)
        self.assertFalse(self.gui.condition_to_run_file_update_timer()) 
        self.gui.file_update_timer = Mock(side_effect=True)
        self.gui.start_file_update_timer()
        Mock.assert_not_called(self.gui.file_update_timer.start)
         
    def test_file_update_timer_check_file_no_update(self):
        config.update({'file_update_interval':'1'})
        with patch('os.path.getmtime') as mock_mtime:
            mock_mtime = Mock(side_effect=100)
            self.gui.update_dataset = Mock()
            self.gui.last_modification_time = 100
            self.gui.initiate_cyclic_file_update()
            self.gui.start_file_update_timer()
            self.assertIsInstance(self.gui.file_update_timer, QTimer)
            time.sleep(1)
            self.assertNotIn('stop', self.registry[-1])
            Mock.assert_not_called(mock_mtime)
            Mock.assert_not_called(self.gui.update_dataset)



class Test_EFC(unittest.TestCase):

    def test_is_it_time_for_something_new(self):
        efc_obj = efc.efc()
        reccommendations = efc_obj.is_it_time_for_something_new()

        # adjust to the current state of DB
        self.assertIn('Oi mate, take a gander', reccommendations, reccommendations)
        self.assertNotIn('давай товарищ, двигаемся!', reccommendations, reccommendations)



class Test_stats(unittest.TestCase):

    def test_get_progress_data(self):
        stat = stats.stats()
        stat.get_data_for_progress(signature='RU_biesy_part1')
        self.assertEqual(stat.chart_values.shape[0], stat.second_chart_values.shape[0])
        self.assertEqual(stat.revision_count.shape[0], stat.formatted_dates.shape[0])
        self.assertGreater(stat.chart_values.shape[0], 1)



def run_summary_generator_test(positives=None, last_positives=None, total=None, max_positives=None, 
                                time_spent=None, last_time_spent=None, verbose=True):
        positives = randint(20,100)
        last_positives = randint(20,80)
        total = max(last_positives, positives) + randint(0,25)
        max_positives = randint(randint(min(positives, last_positives),max(positives, last_positives)) , total)
        time_spent = randint(50, 600)
        last_time_spent = randint(50, 600)
        res = str()

        summary_gen = summary_generator(positives, last_positives, total, max_positives, 
                                        time_spent, last_time_spent)

        if verbose:
            res+=('='*80)
            res+='\n'
            res+=(f'positives = {positives}\n')
            res+=(f'last_positives = {last_positives}\n')
            res+=(f'total = {total}\n')
            res+=(f'max_positives = {max_positives}\n')
            res+=(f'time_spent = {time_spent}\n')
            res+=(f'last_time_spent = {last_time_spent}\n')
            res+=(f'RESULT: {summary_gen.get_summary_text()}\n')
        else:
            res = summary_gen.get_summary_text()

        if verbose:
            res+=('='*80)

        return res    


def print_summary_generator_in_loop(positives=None, last_positives=None, total=None, max_positives=None, 
                                time_spent=None, last_time_spent=None, verbose=True, iter=1, filters:list()=[]):
    for _ in range(iter):
        res = run_summary_generator_test(positives=positives, last_positives=last_positives, total=total, 
                                        max_positives=max_positives, time_spent=time_spent, last_time_spent=last_time_spent, 
                                        verbose=verbose)
        if filters:
            if any(f in res for f in filters): print(res)
        else:
            print(res)

