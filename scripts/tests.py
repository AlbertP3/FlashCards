from collections import OrderedDict
import unittest
import pandas as pd
import os
from utils import *
import db_api
from datetime import datetime, date, timedelta
import main_window_logic
import efc
import stats
from random import randint
from rev_summary import summary_generator
import time
import re
from SOD.scraper import dict_api

def init_backend_and_load_test_file():
    mw = main_window_logic.main_window_logic()
    data = mw.load_flashcards('./revisions/TEST_CARD.csv')
    mw.update_backend_parameters('./revisions/TEST_CARD.csv', data)
    return mw


def create_testcards():
    data = pd.DataFrame(data={'TEST_FLNG':['grudge','compelling','ecclesiastical','to put stock in','retentive','castor','disingenuous','cantankerous','Our company is ahead of the curve when it comes to fiber optics.','not unlike','to loiter','Rube','vestigial','fraught','Seeing the writing on the wall, David abruptly announced his retirement last year.','fickle','reckoning','arcane','summa cum laude','copious','incipient','feasible','lark','scrub'],
                        'TEST_NLNG':['zal, uraza','wazny, istotny, frapujÄ…cy','kościelny, duchowny','wierzyÄ‡ w powodzenie czegos','dobry, chłonny','olejek rycynowy','obłudny, afektowny','przykry w usposobieniu ','more advanced than the competition','nieco podobny','wałęsać','prostak, kmiot','szczÄ…tkowy, śladowy','napi?ty, spi?ty','clues that something (usually negative) will happen','zmienny, lekkomyślny','szacunki, rozliczenie/obrachunek','tajemny','z wyrÃ³Å¼nieniem','suty, rzÄ™sisty','poczÄ…tkowy, rodzÄ…cy siÄ™','wykonalny, ziszczalny','figiel','szorowanie, roślinność pustynna']})
    data.to_csv(config['revs_path']+'TEST_CARD.csv', index=False)



class Test_file_handling(unittest.TestCase):
    
    def assertions_for_correct_file(self, dataset: pd.DataFrame, ROWS_COUNT):
        assert isinstance(dataset, pd.DataFrame)
        assert dataset.shape[1] == 2
        assert dataset.shape[0] == ROWS_COUNT - 1
        for card in dataset:
            self.assertTrue(len(card[1])>0, "ERROR ON CARD: " + card)
            self.assertNotEqual(str(card[1]).lower(), 'n/a', 'ERROR ON CARD: ' + card)



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
        
        self.assertEqual(format_timedelta(example_timedelta_1), '0 Seconds')
        self.assertEqual(format_timedelta(example_timedelta_2), '1 Second')
        self.assertEqual(format_timedelta(example_timedelta_3), '2 Seconds')
        self.assertEqual(format_timedelta(example_timedelta_4), '1 Minute')
        self.assertEqual(format_timedelta(example_timedelta_5), '2 Minutes')
        self.assertEqual(format_timedelta(example_timedelta_6), '1 Hour')
        self.assertEqual(format_timedelta(example_timedelta_7), '2 Hours')
        self.assertEqual(format_timedelta(example_timedelta_8), '1 Day')
        self.assertEqual(format_timedelta(example_timedelta_9), '2 Days')
            

    def test_get_signature_from_filename(self):
        revision = 'signatureassignementtest'
        language = 'language'
        
        self.assertEqual(
            get_signature(revision, 'XT', is_revision=True)
            , revision)
        self.assertEqual(get_signature(language, 'XT', is_revision=False)
            , 'REV_' + 'XT' + datetime.now().strftime('%m%d%Y%H%M%S'))
    

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


    def test_load_dataset(self):
        path_csv = './revisions/TEST_CARD.csv'
        path_absent = './revisions/non-existing-file.csv'

        data = load_dataset(path_csv)
        data_3 = load_dataset(path_absent)

        self.assertEqual(dataset_is_valid(data), True)
        self.assertEqual(dataset_is_valid(data_3), False)
      

    def test_load_dataset_randomization(self):
        path = './revisions/TEST_CARD.csv'
        datasample_1 = load_dataset(path, True).values.tolist()[:5]
        datasample_2 = load_dataset(path, True).values.tolist()[:5]
        datasample_3 = load_dataset(path, True).values.tolist()[:5]

        self.assertEqual(datasample_1 != datasample_2 != datasample_3, True)


    def test_get_lng_from_signature(self):
        s1 = get_lng_from_signature('REV_EN0125370523')
        s2 = get_lng_from_signature('aa_EN23525236')
        s3 = get_lng_from_signature('RU_biesy_part1')     
        s4 = get_lng_from_signature('temp')

        self.assertEqual(s1, 'EN')
        self.assertEqual(s2, 'EN')
        self.assertEqual(s3, 'RU')
        self.assertEqual(s4, '')


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


    def test_save_revision(self):
        filename = 'TEST-SAVE-REV'
        data = pd.DataFrame(data={'EN':['loiter', 'agog', 'compelling'], 
                                        'PL':['szwendac sie', 'podniecony', 'wazny']})

        save_revision(data, filename)
        files_in_rev_folder = get_files_in_dir('./revisions/', include_extension=False)

        self.assertIn(filename, files_in_rev_folder)
        os.remove(f'./revisions/{filename}.csv')



class config_class_test(unittest.TestCase):

    def setUp(self):
        self.conf = Config()

    def test_load(self):
        self.assertEqual(self.conf['optional'], 'keyboard_shortcuts|revision_summary')
        self.assertNotEqual(self.conf['textbox_style_sheet'], '')

    def test_update_config(self):
        self.conf.update({'TEST_ATTR': '0'})
        self.assertEqual(self.conf['TEST_ATTR'], '0')
        


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

        dataset_ordered_pre = load_dataset(self.mw.get_filepath(), False).values.tolist()
        current_card = self.mw.get_current_card()

        self.mw.dc(parsed_cmd=['dc','-'])

        # Assert order maintained
        dataset_ordered_pre = [x[0] for x in dataset_ordered_pre if x[0] != current_card[0]]
        dataset_ordered_post = load_dataset(self.mw.get_filepath(), False).values.tolist()
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

        # first try
        self.assertEqual(mw.get_progress(positives=90, last_positives=0, total=100, max_positives=0), "Impressive for a first try.")
        self.assertEqual(mw.get_progress(positives=10, last_positives=0, total=100, max_positives=0), "Terrible, even for a first try.")
        self.assertEqual(mw.get_progress(positives=75, last_positives=0, total=100, max_positives=0), "Not bad for a first try.")

        # new record
        self.assertEqual(mw.get_progress(positives=90, last_positives=10, total=100, max_positives=10), "That's a new record. Congratulations!")
        self.assertEqual(mw.get_progress(positives=60, last_positives=10, total=100, max_positives=10), "That's a new record. But there is still a lot to improve.")
        self.assertEqual(mw.get_progress(positives=20, last_positives=10, total=100, max_positives=10), "That's a new record. However there is nothing to brag about - you scored only 20%.")
        self.assertEqual(mw.get_progress(positives=100, last_positives=10, total=100, max_positives=10), "That's a new record. You guessed everything right!")

        # close to record
        self.assertEqual(mw.get_progress(positives=90, last_positives=10, total=100, max_positives=90), "You matched all-time record for this revision! Way to go!")
        self.assertEqual(mw.get_progress(positives=88, last_positives=10, total=100, max_positives=90), "You missed all-time record by only 2 cards. But that's still an excellent score.")
        self.assertEqual(mw.get_progress(positives=8, last_positives=10, total=100, max_positives=10), "You missed all-time record by only 2 cards. But it's still entirely pathetic.")
        self.assertEqual(mw.get_progress(positives=9, last_positives=10, total=100, max_positives=10), "You missed all-time record by only 1 card. But it's still entirely pathetic.")

        # close to max
        self.assertEqual(mw.get_progress(positives=9, last_positives=1, total=10, max_positives=12), "Hadn't it been for that 1 card and you would have scored the max!")
        
        # standard case
        self.assertEqual(mw.get_progress(positives=90, last_positives=10, total=100, max_positives=100), "You guessed 80 cards more than last time. Keep it up!")
        self.assertEqual(mw.get_progress(positives=20, last_positives=10, total=100, max_positives=100), "You guessed 10 cards more than last time. However, there is still a lot to improve.")
        self.assertEqual(mw.get_progress(positives=20, last_positives=30, total=100, max_positives=100), "You guessed 10 cards less than last time. Get your sh*t together.")
        self.assertEqual(mw.get_progress(positives=80, last_positives=90, total=100, max_positives=100), "You guessed 10 cards less than last time. However, overall it's not that bad - you scored 80%.")
        self.assertEqual(mw.get_progress(positives=20, last_positives=20, total=100, max_positives=100), "You guessed the exact same number of cards as last time.")


    def test_is_complete_revision(self):
        mw = init_backend_and_load_test_file()
        total_words = mw.get_total_words()
        # go to the last index
        for _ in range(total_words-2):
            mw.goto_next_card()
        
        self.assertEqual(mw.is_complete_revision(), False)
        mw.goto_next_card()
        self.assertEqual(mw.is_complete_revision(), True)



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


class test_dict_scraper(unittest.TestCase):

    def test_pons_regex(self):
        examples =  {'przekazywać [perf przekazać]' : 'przekazywać',
        'robotnik(-ica) m (f)' : 'robotnik(-ica)',
         'zakład m zbrojeniowy' : 'zakład zbrojeniowy',
         'cukrzyca f' : 'cukrzyca',
         'czerwienić [perf za-] się' : 'czerwienić się',
         'to go [or turn] red [in the face]' : 'to go [or turn] red [in the face]',
         'zadłużać [perf zadłużyć] się nt' : 'zadłużać się',
         '[automatyczna] sekretarka f': '[automatyczna] sekretarka',
         'korzeń m': 'korzeń',
         'dezodorant m /klej m w sztyfcie': 'dezodorant/klej w sztyfcie',
         'przerzutki fpl' : 'przerzutki',
         'trudności pl z uczeniem się' : 'trudności z uczeniem się',
         'uczyć [perf na-] się': 'uczyć się',
         'to masticate': 'to masticate',
         '[niedźwiedź] grizzly m [lub grizli m ]' : '[niedźwiedź] grizzly',
         'radio nt na baterie': 'radio na baterie',
         'regent(ka) m (f)': 'regent(ka)',
         'przypochlebiać się imperf': 'przypochlebiać się',
         'salon m kosmetyczny [lub piękności]': 'salon kosmetyczny',
         'bojkotować [perf z-]': 'bojkotować',
         'red as a beetroot [or AM beet]': 'red as a beetroot'
        }
        re_patterns = OrderedDict()
        re_patterns[r'\[(((or )?AM)|lub|perf|inf).*\]'] = ' '
        re_patterns[r'( |\()+(f?pl|fig|m|\(?f\)?|nt|mpl|imperf)([^a-zA-Z0-9\(/]+|$)'] = ' '
        re_patterns[r' ( |$)'] = ''
        re_patterns[r' /'] = '/'

        for raw, expected in examples.items():
            s = raw
            for p, r in re_patterns.items():
                s = re.sub(p, r, s)
            self.assertEqual(s, expected)


    def test_get_from_pons(self):
        d = dict_api('pons')
        translations, originals, warnings = d.get_info_about_phrase('machine learning')
        self.assertNotIn('COMPUT ', originals[0])
        self.assertEqual('uczenie maszynowe', translations[0])

        translations, originals, warnings = d.get_info_about_phrase('ravenous')
        self.assertNotIn('person ', originals[0])
        self.assertEqual('wygłodniały', translations[0])
        
    
    def test_merriam_regex(self):
        pass


    def test_get_from_merriam(self):
        d = dict_api('merriam')
        translations, originals, warnings = d.get_info_about_phrase('iconoclast')
        self.assertIn('a person who attacks settled beliefs or institutions', translations)

    
    def test_get_from_mock(self):
        d = dict_api('mock')
        translations, originals, warnings = d.get_info_about_phrase('whatever')
        self.assertNotEqual(translations, [])
        self.assertIn('hello world', translations)
    

    def test_selection_cmd_pattern(self):
        r = re.compile(r'^(\d+|e\d+|[am])$')
        self.assertIs(r.match('a') is not None, True)
        self.assertIs(r.match('10') is not None, True)
        self.assertIs(r.match('e2') is not None, True)
        self.assertIs(r.match('m') is not None, True)

        self.assertIs(r.match('b10') is not None, False)
        self.assertIs(r.match('a1') is not None, False)
        self.assertIs(r.match('vsase') is not None, False)
        self.assertIs(r.match('2e') is not None, False)
        


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


def test_time_file_save_comp():
    t1 = time.perf_counter()
    comp_time = 1657569324.5002236
    path = './revisions/REV_QN07072022225804.csv'
    mtime = os.path.getmtime(path)
    print(f'TIME SPENT: {time.perf_counter()-t1}')
    print(mtime)
    print()

# test_time_file_save_comp()
