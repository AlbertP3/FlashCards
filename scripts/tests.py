import unittest
import pandas as pd
import load
import utils
import db_api
from datetime import datetime, date, timedelta
import fcc
import gui_main

config = utils.load_config()

def path_to_test(filename):
    path_to_test_dir = './scripts/resources/test_files/'
    return path_to_test_dir + filename


class Test_file_handling(unittest.TestCase):
    

    def test_load_correct_csv_1(self):
        filename = 'correct_EN10092021164327.csv'
        dataset = load.load_dataset(path_to_test(filename))
        self.assertions_for_correct_file(dataset, ROWS_COUNT=72)


    def test_load_correct_csv_2(self):
        filename = 'external_correct_file_1.csv'
        dataset = load.load_dataset(path_to_test(filename))
        self.assertions_for_correct_file(dataset, ROWS_COUNT=793)


    def test_load_excel(self):
        filename = 'ru.xlsx'
        dataset = load.load_dataset(path_to_test(filename))
        self.assertions_for_correct_file(dataset, ROWS_COUNT=19)


    def assertions_for_correct_file(self, dataset: pd.DataFrame, ROWS_COUNT):
        assert isinstance(dataset, pd.DataFrame)
        assert dataset.shape[1] == 2
        assert dataset.shape[0] == ROWS_COUNT - 1
        for card in dataset:
            self.assertTrue(len(card[1])>0, "ERROR ON CARD: " + card)
            self.assertNotEqual(str(card[1]).lower(), 'n/a', 'ERROR ON CARD: ' + card)


    def test_load_wrong_csv(self):
        error_filenames = ['wrong_EN24092021164533.csv']
        for filename in error_filenames:
            dataset = load.load_dataset(path_to_test(filename))
            self.assertEqual(dataset, False)


class Test_utils(unittest.TestCase):

    def test_format_timedelta(self):
        example_timedelta_1 = timedelta(days=0, hours=0, minutes=0, seconds=0)
        example_timedelta_2 = timedelta(days=0, hours=0, minutes=0, seconds=1)
        example_timedelta_3 = timedelta(days=0, hours=0, minutes=0, seconds=2)
        example_timedelta_4 = timedelta(days=0, hours=0, minutes=1, seconds=15)
        example_timedelta_5 = timedelta(days=0, hours=0, minutes=2, seconds=54)
        example_timedelta_6 = timedelta(days=0, hours=1, minutes=6, seconds=12)
        example_timedelta_7 = timedelta(days=0, hours=2, minutes=0, seconds=0)
        example_timedelta_8 = timedelta(days=1, hours=0, minutes=0, seconds=0)
        example_timedelta_9 = timedelta(days=2, hours=4, minutes=15, seconds=43)
        
        self.assertEqual(utils.format_timedelta(example_timedelta_1), '0 Seconds')
        self.assertEqual(utils.format_timedelta(example_timedelta_2), '1 Second')
        self.assertEqual(utils.format_timedelta(example_timedelta_3), '2 Seconds')
        self.assertEqual(utils.format_timedelta(example_timedelta_4), '1 Minute')
        self.assertEqual(utils.format_timedelta(example_timedelta_5), '2 Minutes')
        self.assertEqual(utils.format_timedelta(example_timedelta_6), '1 Hour')
        self.assertEqual(utils.format_timedelta(example_timedelta_7), '2 Hours')
        self.assertEqual(utils.format_timedelta(example_timedelta_8), '1 Day')
        self.assertEqual(utils.format_timedelta(example_timedelta_9), '2 Days')
            

    def test_get_signature_from_filename(self):
        revision = 'signatureassignementtest'
        language = 'language'
        
        self.assertEqual(
            utils.get_signature(revision, 'XT', is_revision=True)
            , revision)
        self.assertEqual(utils.get_signature(language, 'XT', is_revision=False)
            , 'REV_' + 'XT' + datetime.now().strftime('%m%d%Y%H%M%S'))
    

class Test_db_api(unittest.TestCase):

    def test_get_date_from_signature(self):
        correct_signature_example_1 = 'REV_RU11252021180131'
        invalid_signature_example_1 = 'wrongfilenametest'
        non_existing_file = 'non-existing_file'
        dbapi = db_api.db_interface()

        self.assertEqual(dbapi.get_first_date(correct_signature_example_1), date(2021, 11, 26))
        self.assertEqual(dbapi.get_first_date(invalid_signature_example_1), date(1959, 5, 3))
        self.assertEqual(dbapi.get_first_date(non_existing_file), None)
    

    def test_get_first_date(self):
        available_rev_files = utils.get_files_in_dir(config['revs_path'])
        dbapi = db_api.db_interface()
        for rev_file in available_rev_files:
            first_date = dbapi.get_first_date(utils.get_signature(rev_file[:-4],'', True))
            self.assertIsNotNone(first_date)


    def test_get_first_date_if_file_not_in_db(self):
        dbapi = db_api.db_interface()
        first_date = dbapi.get_first_date(utils.get_signature('TEST_FILE_NOT_IN_DB', '', True))
        self.assertEqual(first_date, date(1900, 1, 1))


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
        self.assertEqual(str(dbapi.get_last_date(signature)), timestamp_str)


class Test_flashcard_console_commands(unittest.TestCase):

    def test_help(self):
        fcc_interface = fcc.fcc()
        self.assertEqual(fcc_interface.invoke_command('help modify_card'), 'Allows rewriting for current side of the card. Changes will be written to the rev file')


    def test_modify_card(self):
        fcc_interface = fcc.fcc()

    
    def test_modify_score(self):
        pass


mainwindow = gui_main.main_window_logic()
# fcc_test = Test_flashcard_console_commands(mainwindow)
# fcc_test.test_help()

fcc_interface = fcc.fcc(mainwindow)
# fcc_interface.invoke_command('modify_card a new text suggestion')
print(fcc_interface.invoke_command('help modify_card'))