import sys
import os
from unittest import TestCase, mock
import re
import requests

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import SOD.dicts as sod_dicts
import SOD.cli as sod_cli
import SOD.init as sod_init
from utils import *



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
        }


class Test_dicts(TestCase):
    
    def setUp(self):
        self.d_api = sod_dicts.Dict_Services()
        self.d_api.dicts['mock'] = dict_mock()
        

    def test_pons_regex(self):
        re_patterns = sod_dicts.dict_pons().re_patterns
        for raw, expected in PONS_EXAMPLES.items():
            s = raw
            for p, r in re_patterns.items():
                s = re.sub(p, r, s)
            self.assertEqual(s, expected)


    def test_get_from_pons(self):
        d = self.d_api['pons']
        translations, originals, warnings = d.get_info_about_phrase('machine learning')
        self.assertNotIn('COMPUT ', originals[0])
        self.assertEqual('uczenie maszynowe', translations[0])

        translations, originals, warnings = d.get_info_about_phrase('ravenous')
        self.assertNotIn('person ', originals[0])
        self.assertEqual('wygłodniały', translations[0])
        

    def test_get_from_merriam(self):
        d = self.d_api['merriam']
        translations, originals, warnings = d.get_info_about_phrase('iconoclast')
        self.assertIn('a person who attacks settled beliefs or institutions', translations)

    
    def test_get_from_mock(self):
        d = self.d_api['mock']
        translations, originals, warnings = d.get('whatever')
        self.assertNotEqual(translations, [])
        self.assertIn('hello world', translations)
    


class Test_CLI(TestCase):
    def setUp(self):
        # changes have to be explicitely saved to the file
        self.config = Config()
        self.cli_output_registry = list()
        output = mock.Mock()
        output.console.toPlainText = lambda: '\n'.join(self.cli_output_registry)
        self.ss = sod_init.sod_spawn(output)

        self.ss.cli = sod_cli.CLI(output, './scripts/unittests/example.xlsx', 'Sheet1')
        self.ss.cli.d_api.dicts['mock'] = dict_mock()
        self.ss.cli.d_api.dict_service = 'mock'
        def cls_mock(msg=None, *args, **kwargs): self.cli_output_registry.clear()
        def send_output_mock(msg=None, *args, **kwargs): self.cli_output_registry.append(msg)
        def get_char_lim_mock(*args, **kwargs): return 99
        def mock_saving_to_db(*args, **kwargs): 
            self.cli_output_registry.append([args, kwargs])
            return True, ''
        self.ss.cli.fh.append_content = mock_saving_to_db 
        self.ss.cli.output.cls = cls_mock
        self.ss.cli.send_output = send_output_mock
        self.ss.cli.get_char_limit = get_char_lim_mock


    def test_basic_inquiry_to_mock(self):
        self.ss.run(['hello world']) 
        self.assertIn('1. witaj świEcie                                  | hello world                                   \n2. domyślny serw',
                      self.cli_output_registry[-1], 'output not printed correctly') 
        self.assertTrue(self.ss.cli.SELECT_TRANSLATIONS_MODE)

        self.ss.run(['1', '2'])
        self.assertIn(f'🖫 hello world: witaj świEcie; domyślny serwis', self.cli_output_registry[-1])


    def test_selection_cmd_pattern(self):
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

     


