import unittest
import pandas as pd
import os
import load
from utils import *
import utils
import db_api
from datetime import datetime, date, timedelta
import main_window_logic


config = utils.load_config()

def path_to_test(filename):
    path_to_test_dir = './scripts/resources/test_files/'
    return path_to_test_dir + filename


def init_backend_and_load_test_file():
    mw = main_window_logic.main_window_logic()
    data = mw.load_flashcards('./revisions/TEST_CARD.csv')
    mw.update_backend_parameters('./revisions/TEST_CARD.csv', data)
    return mw


def create_testcards():
    data = pd.DataFrame(data={'TEST_FLNG':['grudge','compelling','ecclesiastical','to put stock in','retentive','castor','disingenuous','cantankerous','Our company is ahead of the curve when it comes to fiber optics.','not unlike','to loiter','Rube','vestigial','fraught','Seeing the writing on the wall, David abruptly announced his retirement last year.','fickle','reckoning','arcane','summa cum laude','copious','incipient','feasible','lark','scrub'],
                        'TEST_NLNG':['?al, uraza','wazny, istotny, frapujÄ…cy','kościelny, duchowny','wierzyÄ‡ w powodzenie czegoÅ›','dobry, chÅ‚onny','olejek rycynowy','obÅ‚udny, afektowny','przykry w usposobieniu ','more advanced than the competition','nieco podobny','waÅ‚Ä™saÄ‡','prostak, kmiot','szczÄ…tkowy, Å›ladowy','napi?ty, spi?ty','clues that something (usually negative) will happen','zmienny, lekkomyÅ›lny','szacunki, rozliczenie/obrachunek','tajemny','z wyrÃ³Å¼nieniem','suty, rzÄ™sisty','poczÄ…tkowy, rodzÄ…cy siÄ™','wykonalny, ziszczalny','figiel','szorowanie, roÅ›linnoÅ›Ä‡ pustynna']})
    data.to_csv(config['revs_path']+'TESTCARDS.csv', index=False)


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
    

    def test_validate_dataset(self):
        ds_correct = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny']})
        ds_one_col = pd.DataFrame(data={'EN':['x', 'y', 'z']})
        ds_three_cols = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny'],
                                        '3rd':['x', 'y', 'z']})
        ds_empty = pd.DataFrame(data={})

        self.assertEqual(utils.dataset_is_valid(ds_correct), True)
        self.assertEqual(utils.dataset_is_valid(ds_one_col), False)
        self.assertEqual(utils.dataset_is_valid(ds_three_cols), True)
        self.assertEqual(utils.dataset_is_valid(ds_empty), False)


    def test_load_dataset(self):
        path_csv = './revisions/TEST_CARD.csv'
        path_absent = './revisions/non-existing-file.csv'

        data = utils.load_dataset(path_csv)
        data_3 = utils.load_dataset(path_absent)

        self.assertEqual(utils.dataset_is_valid(data), True)
        self.assertEqual(utils.dataset_is_valid(data_3), False)
      

    def test_load_dataset_randomization(self):
        path = './revisions/TEST_CARD.csv'
        datasample_1 = utils.load_dataset(path, True).values.tolist()[:5]
        datasample_2 = utils.load_dataset(path, True).values.tolist()[:5]
        datasample_3 = utils.load_dataset(path, True).values.tolist()[:5]

        self.assertEqual(datasample_1 != datasample_2 != datasample_3, True)


    def test_get_lng_from_signature(self):
        s1 = utils.get_lng_from_signature('REV_EN0125370523')
        s2 = utils.get_lng_from_signature('aa_EN23525236')
        s3 = utils.get_lng_from_signature('EN2352562')      
        s4 = utils.get_lng_from_signature('random_signature')

        self.assertEqual(s1, 'EN')
        self.assertEqual(s2, 'EN')
        self.assertEqual(s3, 'EN')
        self.assertEqual(s4, '')


    def test_update_signature_timestamp(self):
        s1 = 'REV_EN31122022101010'
        s_expected = f"REV_EN{datetime.now().strftime('%m%d%Y%H%M%S')}"
        self.assertEqual(utils.update_signature_timestamp(s1), s_expected)


    def test_get_signature(self):
        filename_1 = 'en'
        filename_2 = 'avw_3aa'
        filename_3 = 'just_a_rev'
        timestamp = datetime.now().strftime('%m%d%Y%H%M%S')

        self.assertEqual(utils.get_signature(filename_1, 'EN',  False), f'REV_EN{timestamp}')
        self.assertEqual(utils.get_signature(filename_2, 'EDB', False), f'REV_EDB{timestamp}')
        self.assertEqual(utils.get_signature(filename_3, 'EN', True), filename_3)


    def test_get_most_similar_file(self):
        self.assertEqual(utils.get_most_similar_file('./languages/', 'en'), 'en.xlsx')
        self.assertEqual(utils.get_most_similar_file('./languages/', 'non-existing', None), None)
        self.assertEqual(utils.get_most_similar_file('./languages/', 'non-existing', 'load_any'), 'de.csv')


    def test_save_revision(self):
        filename = 'TEST-SAVE-REV'
        data = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny']})

        utils.save_revision(data, filename)
        files_in_rev_folder = utils.get_files_in_dir('./revisions/', include_extension=False)

        self.assertIn(filename, files_in_rev_folder)
        os.remove(f'./revisions/{filename}.csv')



class Test_db_api(unittest.TestCase):


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
        self.assertEqual(dbapi.get_first_datetime('TEST_SIGNATURE'), utils.make_todayte())


    def test_get_first_date_if_file_not_in_db(self):
        dbapi = db_api.db_interface()
        first_date = dbapi.get_first_datetime(utils.get_signature('TEST_FILE_NOT_IN_DB', '', True))
        self.assertEqual(first_date, date(1900, 1, 1))


    def test_get_last_date(self):
        # db_api.create_record('TEST_SIGNATURE', 0, 0)
        dbapi = db_api.db_interface()
        self.assertEqual(dbapi.get_last_datetime('TEST_SIGNATURE'), utils.make_todayte())


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


class Test_flashcard_console_commands(unittest.TestCase):

    def init_backend_and_load_test_file(self):
        self.mw = main_window_logic.main_window_logic()
        data = self.mw.load_flashcards('./revisions/TEST_CARD.csv')
        self.mw.update_backend_parameters('./revisions/TEST_CARD.csv', data)


    def test_modify_card(self):
        self.init_backend_and_load_test_file()

        # modify card in current set
        self.mw.modify_card(['modify_card', 'NEW', 'TEXT'])
        self.assertEqual(self.mw.get_current_card(), 'NEW TEXT')

        # modify the file
        data = self.mw.load_flashcards('./revisions/TEST_CARD.csv')
        one_side_cards = [x[1] for x in data.values.tolist()]
        self.assertIn('NEW TEXT', one_side_cards)


    def test_modify_card_result(self):
        self.init_backend_and_load_test_file()
        self.mw.next_negative()
        self.mw.goto_prev_card()
        command = ['mcr', '+']

        self.mw.mcr(command)
        self.assertEqual(self.mw.get_positives(), 1)


    def test_delete_card(self):
        
        self.init_backend_and_load_test_file()
        self.mw.goto_next_card()

        dataset_ordered_pre = utils.load_dataset(self.mw.get_filepath(), False).values.tolist()
        current_card = self.mw.get_current_card()

        self.mw.dc(parsed_cmd=['dc','-'])

        # Assert order maintained
        dataset_ordered_pre = [x[0] for x in dataset_ordered_pre if x[0] != current_card[0]]
        dataset_ordered_post = utils.load_dataset(self.mw.get_filepath(), False).values.tolist()
        dataset_ordered_post = [x[0] for x in dataset_ordered_post]

        self.assertEqual(len(dataset_ordered_pre), len(dataset_ordered_post))
        self.assertListEqual(dataset_ordered_pre, dataset_ordered_post)


    def test_load_last_n(self):
        data = load_dataset('./revisions/TEST_CARD.csv', do_shuffle=False).values.tolist()[-5:]
        self.init_backend_and_load_test_file()
        self.mw.lln(['lln','5'])

        self.assertEqual(self.mw.get_dataset().shape[0], 5)
        self.assertListEqual(data, self.mw.get_dataset().values.tolist())



class Test_mainwindow(unittest.TestCase):

    
    def test_get_progress(self):
        mw = init_backend_and_load_test_file()
        self.assertEqual(mw.get_progress(10,0,10), 'Impressive for a first try.')
        self.assertEqual(mw.get_progress(0,0,10), 'Not bad for a first try.')
        self.assertEqual(mw.get_progress(0,8,10), 'You guessed right 8 cards less than last time')
        self.assertEqual(mw.get_progress(6,5,20), 'However You guessed right 1 card more than last time')
        self.assertEqual(mw.get_progress(10,12,30), 'You guessed right 2 cards less than last time')
        self.assertEqual(mw.get_progress(5,5,10), 'You guessed the exact same number of cards as last time')


    def test_is_complete_revision(self):
        mw = init_backend_and_load_test_file()
        total_words = mw.get_total_words()
        # go to the last index
        for _ in range(total_words-2):
            mw.goto_next_card()
        
        self.assertEqual(mw.is_complete_revision(), False)
        mw.goto_next_card()
        self.assertEqual(mw.is_complete_revision(), True)
