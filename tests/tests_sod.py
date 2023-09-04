import os
from unittest import TestCase, mock
import requests
import logging

import SOD.init as sod_init
from utils import Config
from tests.tools import dict_mock
from tests.data import EXAMPLE_PHRASES

CWD = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger(__name__)



class Test_CLI(TestCase):
    def setUp(self):
        self.config = Config()
        self.config.update({'sod_source_lng': 'en', 'sod_target_lng': 'pl', 
            'sod_sheetname': 'Sheet1', 'sod_filepath': f'{CWD}/res/languages/example.xlsx'})
        self.mock_cli_output()
        
    def mock_cli_output(self):
        self.cli_output_registry = list()
        output = mock.MagicMock()
        output.console.toPlainText = lambda: '\n'.join(self.cli_output_registry)
        output.console.setText = self.set_text_mock
        self.ss = sod_init.sod_spawn(stream_out=output)
        self.ss.cli.d_api.dicts = {'mock': dict_mock(), 'imitation': dict_mock()}
        self.ss.cli.d_api.dict_service = 'mock'
        self.ss.cli.output.cls = self.cls_mock
        self.ss.cli.send_output = self.send_output_mock
        self.ss.cli.get_char_limit = lambda: 99
        self.ss.cli.get_lines_limit = lambda: 99

    def set_text_mock(self, text): 
        self.cli_output_registry = [i for i in text.split('\n')]

    def send_output_mock(self, msg=None, *args, **kwargs): 
        self.cli_output_registry.append(msg)

    def get_console(self):
        return '\n'.join(self.cli_output_registry+[self.ss.sout.mw.CONSOLE_PROMPT])

    def check_record(self, key, value):
        self.assertEqual(self.ss.cli.fh.data[key][0], value)

    def check_count_added(self, exp):
        self.assertEqual(self.ss.cli.fh.ws.max_row, self.ss.cli.fh.ws.init_len+exp)

    def check_state(self):
        return self.ss.cli.state.__dict__

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

    
    def test_basic_inquiry_1(self):
        self.run_cmd(['hello world']) 
        self.assertIn('1. witaj świEcie                                  | hello world                                   \n2. domyślny serw',
                      self.cli_output_registry[-1], 'output not printed correctly') 
        self.assertTrue(self.ss.cli.state.SELECT_TRANSLATIONS_MODE)

        self.assertEqual(self.ss.cli.phrase, 'hello world')
        self.assertTrue(self.ss.cli.state.SELECT_TRANSLATIONS_MODE)
        self.run_cmd(['1', '2'])
        self.assertIn(f'🖫 hello world: witaj świEcie; domyślny serwis', self.cli_output_registry[-1])

    
    def test_basic_inquiry_2(self):
        self.run_cmd(['hello world']) 
        self.run_cmd(['e1', 'm2', 'r3', 'a'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['edited_record'])
        self.run_cmd([''])
        self.assertEqual(self.ss.cli.phrase, 'default dict service for tests')
        self.run_cmd(['added_new'])
        self.assertEqual(self.ss.cli.fh.data['default dict service for tests'][0], 'witaj świEcieedited_record; red; added_new')


    def test_basic_inquiry_3(self):
        self.run_cmd(['hello world'])
        self.run_cmd(['m'])
        self.run_cmd(['modified'])
        self.assertEqual(self.ss.cli.fh.data.get('modified'), None)

    
    def test_invalid_edit_1(self):
        self.run_cmd(['maudlin'])
        self.run_cmd(['g5'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.run_cmd([''])


    def test_invalid_edit_2(self):
        self.run_cmd(['Q'])
        self.run_cmd(['maudlin'])
        self.run_cmd([''])
        self.run_cmd(['u2'])
        self.run_cmd(['u2'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.run_cmd([''])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, self.ss.cli.prompt.PHRASE)


    def test_basic_inquiry_manual_1(self):
        self.run_cmd(['$'])
        self.assertTrue(self.ss.cli.state.MANUAL_MODE)
        self.run_cmd(['Newphrase'])
        self.assertTrue(self.cli_output_registry[-1], 'Phrase: Newphrase')
        self.run_cmd(['manual entry'])
        self.assertTrue(self.cli_output_registry[-1], 'manual entry')
        self.assertEqual(self.ss.cli.fh.data['Newphrase'][0], 'manual entry')


    def test_basic_inquiry_manual_2(self):
        self.run_cmd(['$', 'Newphrase', '$', 'manual entry'])
        self.assertEqual(self.ss.cli.fh.data['Newphrase'][0], 'manual entry')

    
    def test_basic_inquiry_manual_duplicate(self):
        init_row = self.ss.cli.fh.ws.max_row
        self.run_cmd(['$', 'Newphrase', '$', 'manual entry'])
        self.assertEqual(self.ss.cli.fh.data['Newphrase'][0], 'manual entry')
        self.run_cmd(['$', 'Newphrase', '$', 'manual entry'])
        self.run_cmd([''])  # skip saving
        self.check_count_added(1)
        self.run_cmd(['$'])
        self.run_cmd(['Newphrase'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['Newtranslation'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for Newphrase: ')
        self.run_cmd(['1'])
        self.check_count_added(1)
        self.assertEqual(self.ss.cli.fh.ws.cell(init_row+1, 1).value, 'Newphrase')
        self.assertEqual(self.ss.cli.fh.ws.cell(init_row+1, 2).value, 'Newtranslation')
        
        
    def test_basic_inquiry_manual_abort(self):
        '''Check if both manual entry modes work properly when aborted'''
        self.run_cmd(['$', 'Newphrase', '$', ''])
        self.assertEqual(self.ss.cli.fh.data.get('Newphrase'), None)
        self.assertTrue(self.cli_output_registry[-1].endswith(self.ss.cli.msg.SAVE_ABORTED))
        self.run_cmd(['$'])
        self.run_cmd(['Newphrase'])
        self.run_cmd([''])
        self.assertTrue(self.cli_output_registry[-1].endswith(self.ss.cli.msg.SAVE_ABORTED))
        self.assertEqual(self.ss.cli.fh.data.get('Newphrase'), None)

    
    def test_multiple_single_inquiries(self):
        self.run_cmd(['hello world'])
        self.run_cmd(['e1', 'a'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['_edited'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['added_new'])

        self.run_cmd(['mooning'])
        self.run_cmd(['m', '2'])
        self.run_cmd(['modded'])

        self.assertEqual(self.ss.cli.fh.data['hello world'][0],'witaj świEcie_edited; added_new')
        self.assertEqual(self.ss.cli.fh.data['mooningmodded'][0],'domyślny serwis')


    def test_verify_selection_pattern(self):
        self.ss.cli.translations = ['']*3
        self.ss.cli.state.SELECT_TRANSLATIONS_MODE = True
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['m']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['99']), False, 'Out of Bound')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['m2']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['b1']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a1']), False, 'Index to this Operator not allowed')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['v','s','a','s','e']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['e3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['2e']), False, 'Wrong Order')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['r3']), True)
        self.assertTrue(self.cli_output_registry[-2].endswith(self.ss.cli.msg.WRONG_EDIT))


    def test_queue_handling_on_internet_connection_loss(self):
        # while in queue mode, drop internet connection and assert
        # that: 1. SOD does not fail; 2. notification in top bar is displayed;
        # 3. normal course of work can be continued

        # Begin queue
        self.run_cmd(['Q'])
        self.run_cmd(['neptune'])

        # Drop Connection
        def get_page_content_mock(*args, **kwargs): raise requests.exceptions.ConnectionError
        orig_get = self.ss.cli.d_api.dicts['mock'].get
        self.ss.cli.d_api.dicts['mock'].get = get_page_content_mock       
        self.run_cmd(['moon'])
        self.assertIn('No Internet Connection', self.cli_output_registry[-2]) 
        
        # continue
        self.ss.cli.d_api.dicts['mock'].get = orig_get
        self.run_cmd(['mars'])
        self.assertIn('mars', self.ss.cli.queue_dict.keys())
        self.assertNotIn('moon', self.cli_output_registry, 'SOD did not clean after Connection Error')
        self.assertEqual(self.ss.cli.queue_index-1, len(self.ss.cli.queue_dict.keys()))
    
 
    def test_delete_from_queue(self):
        self.run_cmd(['Q'])
        self.run_cmd(['saturn'])
        self.run_cmd(['moon'])
        self.run_cmd(['venus'])
        self.run_cmd(['del', '2'])

        self.assertNotIn('moon', self.ss.cli.queue_dict)
        self.assertEqual(3, self.ss.cli.queue_index)
        self.assertEqual(2, len(self.ss.cli.queue_dict.keys()))
        self.assertTrue(self.cli_output_registry[-1].startswith(' 2. venus'))
        self.assertTrue(self.cli_output_registry[-2].startswith(' 1. saturn'))


    def test_queue_updates_duplicate(self):
        # Ensure that duplicates are updated 
        self.run_cmd(['Q'])
        self.run_cmd(['saturn'])
        self.run_cmd(['moon'])
        self.run_cmd(['moon'])
        log.debug('\n'.join(self.cli_output_registry)[23:])
        self.assertEqual('\n'.join(self.cli_output_registry)[23:], 
''' 🔃 Updated Queue
 1. saturn
 | witaj świEcie; domyślny serwis
 2. moon
 | witaj świEcie; domyślny serwis''')


    def test_queue_items_shown_limit(self):
        # test if SOD cli displays only last N items, matching the window height
        # 4 lines: status + Queue mark, divided by 2 in the calcs; then 2 lines per each item
        bloats = (y for y in EXAMPLE_PHRASES)
        self.run_cmd(['Q'])

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
        self.run_cmd(['Q'])
        self.run_cmd(['saturn'])
        self.run_cmd(['error'])
        self.assertEqual('\n'.join(self.cli_output_registry)[23:],
''' TEST ERROR INDUCED
 1. saturn
 | witaj świEcie; domyślny serwis''')
        self.run_cmd(['none'])
        self.assertEqual('\n'.join(self.cli_output_registry)[23:],
''' ⚠ No Translations!
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
        self.run_cmd(['duplicate_1']) 
        self.run_cmd([next(bloats)]) 
        self.assertEqual(list(self.ss.cli.queue_dict.keys()), ['Mercury', 'duplicate_1', 'Venus']), 

        # execute the queue
        self.run_cmd(['']) 
        self.run_cmd(['']) # skip saving
        self.assertIn(' ➲ [2/3]', self.get_console())
        self.run_cmd(['1'])
        self.run_cmd([''])
        self.assertIn('Not Saved', self.get_console())
        self.assertEqual(len(self.ss.cli.fh.data), self.ss.cli.fh.ws.init_len+1)
        

    def test_queue_skip_manual_entries(self):
        '''test if selecting from queue auto-saves the manual entries'''
        bloats = (y for y in EXAMPLE_PHRASES)

        self.run_cmd(['Q']) 
        self.run_cmd([next(bloats)]) 
        self.run_cmd(['$ manual-entry $ manual-phrase'])
        self.run_cmd([next(bloats)]) 
        self.run_cmd([next(bloats)]) 
        self.assertIn('manual-entry \n | manual-phrase', self.get_console())

        # execute the queue
        self.run_cmd(['']) 
        self.run_cmd(['']) 
        self.assertIn(' ➲ [3/4]', self.get_console())
        self.assertEqual(self.ss.cli.fh.data['manual-entry'][0], 'manual-phrase')
             

    def test_simple_save(self):
        self.run_cmd(['moon'])
        self.run_cmd(['1', '3'])
        self.assertIn(f'🖫 moon: witaj świEcie; czerwony', self.cli_output_registry[-1])


    def test_save_reverse(self):
        '''Check if entries are saved properly when reversed'''
        self.run_cmd(['moon'])
        self.run_cmd(['r1', '3'])
        self.assertIn(f'🖫 moon: hello world; czerwony', self.cli_output_registry[-1])


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
        self.assertIn('neptune', self.get_console())

        # modify phrase
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Modify: moon')
        self.ss.cli.set_output_prompt('Modify: ', 0)
        self.run_cmd(['earth'])
        self.assertEqual(self.ss.cli.phrase, 'earth')
        

    def test_modify_phrase_with_specific_result(self):
        # Test if replacing the searched phrase with one of the results works
        self.run_cmd(['moon'])
        self.run_cmd(['m3', '2', 'a'])
        self.assertEqual(self.ss.sout.mw.aval_lefts, 3)
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Modify: red')
        self.assertEqual(self.ss.cli.phrase, 'moon')
        
        self.run_cmd([''])
        self.assertEqual(self.ss.cli.phrase, 'red', 'Phrase was not modified')
        self.run_cmd(['added_item'])
        self.assertIn(f'🖫 red: domyślny serwis; added_item', self.cli_output_registry[-1], 'Error during save')


    def test_modify_phrase_cancel(self):
        # Assert that if phrase modification is cancelled, then the save is aborted
        self.run_cmd(['moon'])
        self.run_cmd(['m3', '2'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Modify: red')
        self.ss.sout.mw.CONSOLE_PROMPT = 'Modify: '
        self.run_cmd([''])
        self.assertIsNone(self.ss.cli.phrase)
        self.assertIn('Not Saved', self.cli_output_registry[-1])


    def test_query_simple_run(self):
        '''Test if query is built and executed properly'''
        bloats = (y for y in EXAMPLE_PHRASES)
        self.run_cmd(['Q']) 
        self.assertTrue(self.ss.cli.state.QUEUE_MODE)
        self.run_cmd([next(bloats)])
        self.run_cmd([next(bloats)])
        self.run_cmd([next(bloats)])
        self.assertEqual(set(self.ss.cli.queue_dict.keys()), {'Mercury', 'Venus', 'Earth'})
        self.run_cmd([''])

        self.assertTrue(self.ss.cli.state.QUEUE_SELECTION_MODE)
        self.run_cmd(['e1', 'a'])
        self.run_cmd(['_edited'])
        self.run_cmd(['added_new'])

        self.run_cmd(['m', '1'])
        self.run_cmd(['_modified'])

        self.run_cmd(['r3'])

        self.assertEqual(self.ss.cli.fh.data['Mercury'][0], 'witaj świEcie_edited; added_new')
        self.assertEqual(self.ss.cli.fh.data['Venus_modified'][0], 'witaj świEcie')
        self.assertEqual(self.ss.cli.fh.data['Earth'][0], 'red')

 
    def test_duplicate_reversed_lng(self):
        '''check if duplicate is spotted when lng is reversed'''
        self.run_cmd(['earth'])
        self.run_cmd(['1'])
        self.run_cmd(['PL', 'witaj świEcie'])
        self.assertEqual(self.config['sod_source_lng'], 'pl')
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())


    def test_duplicate_mode_single_entry_1(self):
        '''Manage the duplicate process'''
        self.run_cmd(['maudlin'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['e1', '2'])
        self.run_cmd(['_edited'])
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 2).value, 'definitely a wrong explanation_edited; witaj świEcie')
        self.assertEqual(self.ss.cli.fh.ws.max_row, self.ss.cli.fh.ws.init_len)


    def test_duplicate_mode_single_entry_2(self):
        '''Assert that modyfing existing phrase's translation does alter the original record'''
        self.run_cmd(['maudlin'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['m', '2'])
        self.run_cmd(['_modified'])
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 1).value, 'maudlin_modified')
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 2).value, 'witaj świEcie')
        self.check_count_added(0)
        self.run_cmd(['maudlin'])
        self.assertNotIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd([''])
        self.run_cmd(['maudlin_modified'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.check_count_added(0)


    def test_lng_and_dict_switch_queue(self):
        '''Test switching lng and dicts during query'''
        self.run_cmd(['Q'])
        self.run_cmd(['Earth'])
        self.run_cmd(['dict', 'imitation'])
        self.assertEqual(self.ss.cli.queue_index, 2)
        self.assertEqual(self.ss.cli.d_api.dict_service, 'imitation')
        self.run_cmd(['PL', 'Moon'])
        self.assertEqual(self.ss.cli.queue_index, 3)
        self.assertEqual(self.ss.cli.d_api.source_lng, 'pl')
        self.run_cmd(['dict', 'mock'])
        self.assertEqual(self.ss.cli.d_api.dict_service, 'mock')
        self.assertEqual(self.ss.cli.queue_index, 3)
        self.run_cmd([''])
        self.assertEqual(set(self.ss.cli.queue_dict.keys()), {'Moon'})
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for Earth: ')


    def test_duplicate_mode_manual_oneline(self):
        '''Manage the duplicate process'''
        self.run_cmd(['$', 'maudlin', '$', 'Duis aute'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.run_cmd(['1'])
        self.check_count_added(0)
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 2).value, 'Duis aute')

    
    def test_duplicate_mode_manual_multiline(self):
        '''Manage the duplicate process'''
        self.run_cmd(['$'])
        self.run_cmd(['maudlin'])
        self.run_cmd(['Duis aute'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.assertRegex(self.get_console(), r'1. Duis aute \s+ | maudlin')
        self.assertRegex(self.get_console(), r'2. definitely a wrong explanation \s+ | maudlin')
        self.run_cmd(['1'])
        self.check_count_added(0)
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 2).value, 'Duis aute')


    def test_duplicate_mode_queue(self):
        '''Manage the duplicate process'''
        self.run_cmd(['Q'])
        self.run_cmd(['sun'])
        self.run_cmd(['maudlin'])
        self.run_cmd(['moon'])
        self.run_cmd([''])
        self.run_cmd([''])  # skip saving
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.assertIn('definitely a wrong explanation', self.get_console())
        self.run_cmd(['r4', 'a'])
        self.run_cmd(['ullamco laboris nisi'])
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(2, 2).value, 'red; ullamco laboris nisi')
        self.check_count_added(0)


    def test_compound_inquiries(self):
        '''Check if using consecutive modes works well'''
        # Single
        self.run_cmd(['Mercury'])
        self.run_cmd(['e1', 'a'])
        self.run_cmd(['_edited'])
        self.run_cmd(['added_new'])
        self.check_record('Mercury', 'witaj świEcie_edited; added_new')
        self.check_count_added(1)

        # Query
        self.run_cmd(['Q'])
        self.run_cmd(['Venus'])
        self.run_cmd(['bloat'])
        self.run_cmd([''])
        self.run_cmd(['3', 'm', 'r5'])
        self.run_cmd(['modified'])
        self.run_cmd([''])
        self.check_record('Venusmodified', 'czerwony; dolor sit amet')
        self.check_count_added(2)
        
        # Manual
        self.run_cmd(['$', 'manual-entry', '$', 'manual-input'])
        self.check_record('manual-entry', 'manual-input')
        self.check_count_added(3)

        # Query
        self.test_queue_handling_on_internet_connection_loss()
        self.run_cmd([''])
        self.run_cmd(['3'])
        self.run_cmd(['e'])
        self.run_cmd(['e2'])
        self.run_cmd([''])

        # Single
        self.run_cmd(['Earth'])
        self.run_cmd(['5'])
        self.check_record('Earth', 'lorem ipsum')
        self.check_count_added(6)
