import sys
import os
from unittest import TestCase, mock
import re
import unittest
import requests
from functools import partial
from itertools import zip_longest

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import SOD.dicts as sod_dicts
import SOD.cli as sod_cli
import SOD.init as sod_init
from utils import *
import tests.tools as tools



class dict_mock():
    def get(self, word):
        translations = ['witaj świEcie', 'domyślny serwis', 'czerwony', 'traktować kogoś z honorami', 'lorem ipsum']
        originals = ['hello world', 'default dict service for tests', 'red', 'to roll out the red carpet for sb [or to give sb the red carpet treatment]', 'dolor sit amet']
        warnings = []
        if word == 'none': 
            translations.clear()
            originals.clear()
        elif word == 'mauve':
            translations = ['mauve']
            originals = ['jasno fioletowy']
        elif word == 'error':
            warnings = ['TEST ERROR INDUCED']
        return translations, originals, warnings


PONS_EXAMPLES =  {
        'przekazywać [perf przekazać]' : 'przekazywać',
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
        'red as a beetroot [or AM beet]': 'red as a beetroot',
        'zaciągać [perf zaciągnąć] się papierosem ': 'zaciągać się papierosem',
        'upodobanie nt [lub słabość f ] do czegoś': 'upodobanie do czegoś',
        'skrętka f ELEC':'skrętka',
        }

EXAMPLE_PHRASES = ('Mercury', 'Venus', 'Earth', 'Mars', 'Jupyter', 'Saturn', 'Uranus', 'Neptune', 'Pluto', 'Moon', 'Sun')

class Test_dicts(TestCase):
    
    def setUp(self):
        self.d_api = sod_dicts.Dict_Services()
        self.d_api.dicts['mock'] = dict_mock()
        

    def mock_connection_html(self, file_name):
        requests_session = requests.session()
        requests_session.mount(f'file://', tools.LocalFileAdapter())
        html = requests_session.get(f"file://{os.getcwd()}/scripts/tests/res/dicts/{file_name}")
        return html


    def test_pons_regex(self):
        re_patterns = sod_dicts.dict_pons().re_patterns
        for raw, expected in PONS_EXAMPLES.items():
            s = raw
            for p, r in re_patterns.items():
                s = re.sub(p, r, s)
            self.assertEqual(s, expected)


    @unittest.skip('Replace online connection with a mock')
    def test_get_from_pons(self):
        d = self.d_api['pons']
        translations, originals, warnings = d.get_info_about_phrase('machine learning')
        self.assertNotIn('COMPUT ', originals[0])
        self.assertEqual('uczenie maszynowe', translations[0])

        translations, originals, warnings = d.get_info_about_phrase('ravenous')
        self.assertNotIn('person ', originals[0])
        self.assertEqual('wygłodniały', translations[0])
        


    @unittest.skip('Replace online connection with a mock')
    def test_get_from_merriam(self):
        d = self.d_api['merriam']
        translations, originals, warnings = d.get_info_about_phrase('iconoclast')
        self.assertIn('a person who attacks settled beliefs or institutions', translations)

    
    def test_get_from_mock(self):
        d = self.d_api['mock']
        translations, originals, warnings = d.get('whatever')
        self.assertNotEqual(translations, [])
        self.assertIn('hello world', translations)


    def test_dict_diki_query_success_1(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_decorous.txt')
        t, o, w = d.get('decorous')
        self.assertEqual(w, [])
        self.assertEqual(['odpowiedni (o wyglądzie), stosowny (o zachowaniu), w dobrym guście'], t)
        self.assertEqual('decorous', o[0])

    def test_dict_diki_query_success_2(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_gasket.txt')
        t, o, w = d.get('gasket')
        self.assertEqual(w, [])
        self.assertEqual(['uszczelka', 'krawat'], t)
        self.assertEqual(['gasket', 'gasket'], o)

    def test_dict_diki_query_success_3(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_abbreviation.txt')
        t, o, w = d.get('abbreviation')
        self.assertEqual(w, [])
        self.assertEqual(['skrót (skrócona nazwa)', 'skrócenie'], t[:2])

    def test_dict_diki_query_success_4(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_affliction.txt')
        t, o, w = d.get('affliction')
        self.assertEqual(w, [])
        self.assertEqual(["zmartwienie, przygnębienie, nieszczęście", "dolegliwość, przypadłość, schorzenie"], t)
        self.assertEqual('affliction', o[0])

    def test_dict_diki_query_success_5(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_environment.txt')
        t, o, w = d.get('environment')
        self.assertEqual(w, [])
        self.assertEqual(['otoczenie, środowisko, anturaż (tworzone przez otaczających ludzi oraz rzeczy)', 'otoczenie, środowisko (rodzaj lub charakterystyczne cechy danego obszaru)', 'środowisko, środowisko naturalne'], t)
        self.assertEqual(['environment', 'the environment', 'environment'], o)

    def test_dict_diki_query_success_6(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_transmogrify.txt')
        t, o, w = d.get('transmogrify')
        self.assertEqual(['przemienić (za pomocą czarów)'], t)
        self.assertEqual(['transmogrify'], o)
        self.assertEqual([], w)

    def test_dict_diki_query_success_7(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_przemieniac.txt')
        t, o, w = d.get('przemieniac')
        self.assertEqual(['transform', 'metamorphose', 'przemienić, zmienić', 'przemienić (za pomocą czarów)'], t)
        self.assertEqual(['przekształcać, transformować, przekształcić się', 'przeobrażać się', 'przemienić', 'przekształcać, transformować, przekształcić się'], o)
        self.assertEqual([], w)

    def test_dict_diki_query_success_8(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_discern.txt')
        t, o, w = d.get('discern')
        self.assertEqual(len(t), len(o))
        self.assertEqual(['discern']*3, o)
        self.assertEqual(['rozeznawać się, dostrzegać', 'dostrzegać, spostrzegać', 'rozeznać'], t)

    def test_dict_diki_query_success_9(self):
        d = self.d_api['diki']
        self.d_api.switch_languages('pl', 'en')
        d.get_page_content = partial(self.mock_connection_html, 'diki_torebka.txt')
        t, o, w = d.get('torebka')
        self.assertEqual(len(t), len(o))
        self.assertEqual(['torebka, torba (damska)', 'torebka, torba, worek, torebka (ilość)', 'woreczek, torebka (jako wewnętrzna część rośliny lub zwierzęcia)', 'torebka (np. z wonnymi ziołami)', 'Słownik terminów anatomicznych', 'torba, torebka', 'pochewka, torebka'], o)
        self.assertEqual(['bag , handbag , purse', 'bag', 'sac', 'sachet', 'capsula', 'bagful', 'involucre'], t)

    def test_dict_diki_query_error_1(self):
        d = self.d_api['diki']
        d.get_page_content = partial(self.mock_connection_html, 'diki_affilication.txt')
        t, o, w = d.get('affilication')
        self.assertEqual('Czy chodziło ci o: affiliation, affliction, affrication', w[0])



    @unittest.skip("TODO")
    def test_get_from_cambridge(self):
        d = self.d_api['cambridge']
        d.get_page_content = partial(self.mock_connection_html, '')



class Test_CLI(TestCase):
    def setUp(self):
        self.config = Config()
        self.cli_output_registry = list()
        self.cli_saved_registry = list()

        output = mock.Mock()
        output.console.toPlainText = self.get_console
        def set_text_mock(text): self.cli_output_registry = [i for i in text.split('\n')]
        output.console.setText = set_text_mock
        self.ss = sod_init.sod_spawn(adapter='fcc', stream_out=output)

        self.ss.cli = sod_cli.CLI(output, './scripts/tests/res/languages/example.xlsx', 'Sheet1')
        self.ss.cli.d_api.dicts['mock'] = dict_mock()
        self.ss.cli.d_api.dict_service = 'mock'

        def send_output_mock(msg=None, *args, **kwargs): self.cli_output_registry.append(msg)
        def get_char_lim_mock(*args, **kwargs): return 99
        def get_lines_lim_mock(*args, **kwargs): return 99
        def mock_saving_to_db(phrase:str, trans:list): 
            t = '; '.join(trans) if isinstance(trans, list) else trans
            self.cli_saved_registry.append([phrase, t])
            return True, ''
            
        self.ss.cli.fh.append_content = mock_saving_to_db 
        self.ss.cli.output.cls = self.cls_mock
        self.ss.cli.send_output = send_output_mock
        self.ss.cli.get_char_limit = get_char_lim_mock
        self.ss.cli.get_lines_limit = get_lines_lim_mock


    def get_console(self):
        return '\n'.join(self.cli_output_registry)

    def run_cmd(self, parsed_input:list):
        # registers console prompt and the input to the log
        self.cli_output_registry.append(self.ss.sout.mw.CONSOLE_PROMPT + ' '.join(parsed_input))
        self.ss.run(parsed_input)

    def cls_mock(self, msg=None, keep_content=False, keep_cmd=False): 
        try:
            content = self.cli_output_registry[1:] if keep_content else list() 
        except:
            content = self.cli_output_registry or list()
        self.cli_output_registry.clear() 
        if msg: self.cli_output_registry.append(msg)
        if keep_content: self.cli_output_registry.extend(content)


    def test_basic_inquiry_to_mock(self):
        self.ss.run(['hello world']) 
        self.assertIn('1. witaj świEcie                                  | hello world                                   \n2. domyślny serw',
                      self.cli_output_registry[-1], 'output not printed correctly') 
        self.assertTrue(self.ss.cli.SELECT_TRANSLATIONS_MODE)

        self.ss.run(['1', '2'])
        self.assertIn(f'🖫 hello world: witaj świEcie; domyślny serwis', self.cli_output_registry[-1])


    def test_verify_selection_pattern(self):
        self.ss.cli.translations = ['']*3
        self.ss.cli.SELECT_TRANSLATIONS_MODE = True
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['99']), False, 'Out of Bound')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['m']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['b1']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a1']), False, 'Index to this Operator not allowed')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['v','s','a','s','e']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['e3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['2e']), False, 'Wrong Order')
        self.assertTrue(self.cli_output_registry[-2].endswith(self.ss.cli.WRONG_EDIT))


    def test_queue_handling_on_internet_connection_loss(self):
        # while in queue mode, drop internet connection and assert
        # that: 1. SOD does not fail; 2. notification in top bar is displayed;
        # 3. normal course of work can be continued

        # Begin queue
        self.ss.run(['Q'])
        self.ss.run(['neptune'])

        # Drop Connection
        def get_page_content_mock(*args, **kwargs): raise requests.exceptions.ConnectionError
        orig_get = self.ss.cli.d_api.dicts['mock'].get
        self.ss.cli.d_api.dicts['mock'].get = get_page_content_mock       
        self.ss.run(['moon'])
        self.assertIn('No Internet Connection!', self.cli_output_registry[-2]) 
        
        # continue
        self.ss.cli.d_api.dicts['mock'].get = orig_get
        self.ss.run(['mars'])
        self.assertIn('mars', self.ss.cli.queue_dict.keys())
        self.assertNotIn('moon', self.cli_output_registry, 'SOD did not clean after Connection Error!')
        self.assertEqual(self.ss.cli.queue_index-1, len(self.ss.cli.queue_dict.keys()))
    
 
    def test_delete_from_queue(self):
        self.ss.run(['Q'])
        self.ss.run(['saturn'])
        self.ss.run(['moon'])
        self.ss.run(['venus'])
        self.ss.run(['del', '2'])

        self.assertNotIn('moon', self.ss.cli.queue_dict)
        self.assertEqual(3, self.ss.cli.queue_index)
        self.assertEqual(2, len(self.ss.cli.queue_dict.keys()))
        self.assertTrue(self.cli_output_registry[-1].startswith(' 2. venus'))
        self.assertTrue(self.cli_output_registry[-2].startswith(' 1. saturn'))


    def test_delete_from_queue_duplicate(self):
        # Ensure that duplicates are updated 
        self.ss.run(['Q'])
        self.ss.run(['saturn'])
        self.ss.run(['moon'])
        self.ss.run(['moon'])
        self.assertEqual('\n'.join(self.cli_output_registry), 
'''🕮 mock | en⇾pl | 🛢 1 | 🔃 Updated Queue
 1. saturn
 | witaj świEcie; domyślny serwis
 2. moon
 | witaj świEcie; domyślny serwis''')


    def test_queue_items_shown_limit(self):
        # test if SOD cli displays only last N items, matching the window height
        # 4 lines: status + Queue mark, divided by 2 in the calcs; then 2 lines per each item
        bloats = (y for y in EXAMPLE_PHRASES)
        self.ss.run(['Q'])

        # only last 2 should be visible
        self.ss.cli.get_lines_limit = mock.Mock(return_value=2*2+4)
        self.run_cmd([next(bloats)])
        self.run_cmd([next(bloats)])
        self.run_cmd([next(bloats)])
        self.assertNotIn('1. ', self.get_console())
        self.assertIn('2. ', self.get_console())
        self.assertIn('3. ', self.get_console())

        # After a resize - show last 4 lines
        self.ss.cli.get_lines_limit = mock.Mock(return_value=4*2+4)
        self.run_cmd([next(bloats)])
        self.run_cmd([next(bloats)])
        self.assertNotIn('1. ', self.get_console())
        self.assertIn('2. ', self.get_console())
        self.assertIn('3. ', self.get_console())
        self.assertIn('4. ', self.get_console())
        self.assertIn('5. ', self.get_console())

        # downsize - show last 3
        self.ss.cli.get_lines_limit = mock.Mock(return_value=3*2+4)
        self.run_cmd([next(bloats)])
        self.assertNotIn('3. ', self.get_console())
        self.assertIn('4. ', self.get_console())
        self.assertIn('5. ', self.get_console())
        self.assertIn('6. ', self.get_console())


    def test_delete_from_queue_on_warning(self):
        # Ensure translations with warnings are ommited
        self.ss.run(['Q'])
        self.ss.run(['saturn'])
        self.ss.run(['error'])
        self.assertEqual('\n'.join(self.cli_output_registry),
'''🕮 mock | en⇾pl | 🛢 1 | TEST ERROR INDUCED
 1. saturn
 | witaj świEcie; domyślny serwis''')
        self.ss.run(['none'])
        self.assertEqual('\n'.join(self.cli_output_registry),
'''🕮 mock | en⇾pl | 🛢 1 | ⚠ No Translations!
 1. saturn
 | witaj świEcie; domyślny serwis''')
     
            
    def test_lng_switch(self):
        # test various lng changes - user can define: src_lng only, or both src and tgt
        self.ss.cli.d_api.switch_languages(src_lng='pl', tgt_lng='en')
        self.assertEqual(self.config['sod_source_lng'], 'pl')
        self.assertEqual(self.config['sod_target_lng'], 'en')

        self.ss.cli.d_api.switch_languages(src_lng='en')
        self.assertEqual(self.config['sod_source_lng'], 'en')
        self.assertEqual(self.config['sod_target_lng'], 'pl')

        self.ss.cli.d_api.switch_languages(src_lng='pl', tgt_lng='en')
        self.assertEqual(self.config['sod_source_lng'], 'pl')
        self.assertEqual(self.config['sod_target_lng'], 'en')
         
        self.ss.cli.d_api.switch_languages(src_lng='ru', tgt_lng='pl')
        self.assertEqual(self.config['sod_source_lng'], 'ru')
        self.assertEqual(self.config['sod_target_lng'], 'pl')
         
        self.ss.cli.d_api.switch_languages(src_lng='en')
        self.assertEqual(self.config['sod_source_lng'], 'en')

        self.assertEqual(self.config['sod_target_lng'], 'pl')


    def test_queue_ommit_duplicates(self):
        bloats = (y for y in EXAMPLE_PHRASES)
        self.run_cmd(['Q']) 
        self.run_cmd([next(bloats)]) 
        self.run_cmd(['duplicate_1']) 
        self.run_cmd([next(bloats)]) 
        self.run_cmd(['duplicate_2']) 
        self.run_cmd(['']) 

        # execute the queue
        self.run_cmd(['']) # skip saving
        self.assertIn(' ➲ [3/4]', self.get_console())
        self.run_cmd(['']) # skip saving
        self.assertIn('Not Saved', self.get_console())
        

    def test_queue_skip_manual_entries(self):
        # test if selecting from queue auto-saves the manual entries
        bloats = (y for y in EXAMPLE_PHRASES)

        self.run_cmd(['Q']) 
        self.run_cmd([next(bloats)]) 
        self.run_cmd(['$ manual-entry $ manual-phrase'])
        self.run_cmd([next(bloats)]) 
        self.run_cmd([next(bloats)]) 
        self.assertIn('manual-entry\n |  manual-phrase', self.get_console())

        # execute the queue
        self.run_cmd(['']) 
        self.run_cmd(['']) 
        self.assertIn(' ➲ [3/4]', self.get_console())
        self.assertIn([' manual-entry ', 'manual-phrase'], self.cli_saved_registry)
             

    def test_simple_save(self):
        self.run_cmd(['moon'])
        self.run_cmd(['1', '3'])
        self.assertIn(f'🖫 moon: witaj świEcie; czerwony', self.cli_output_registry[-1])


    def test_res_edit_parse(self):
        self.run_cmd(['moon'])
        self.run_cmd(['a', 'e3', 'm', 'a'])

        # append
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Add: ')
        self.run_cmd(['sun'])
        self.assertEqual(self.ss.cli.res_edit[-1], 'sun')

        # edit 3rd item
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Edit: czerwony')
        self.ss.sout.mw.CONSOLE_PROMPT = 'Edit: '
        self.run_cmd(['neptune'])
        self.assertEqual(self.ss.cli.res_edit[-1], 'neptune')

        # modify phrase
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Modify: moon')
        self.ss.sout.mw.CONSOLE_PROMPT = 'Modify: '
        self.run_cmd(['earth'])
        self.assertEqual(self.ss.cli.phrase, 'earth')
        

