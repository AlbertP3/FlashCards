import os
import re
from unittest import TestCase, mock
import requests
import logging

import SOD.init as sod_init
from SOD.file_handler import XLSXFileHandler
from SOD.dicts import DictLocal
from utils import Config, Caliper
from tests.tools import dict_mock, fmetrics
from tests.data import EXAMPLE_PHRASES

CWD = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger(__name__)



class Test_CLI(TestCase):
    maxDiff = None
    
    def setUp(self):
        self.config = Config()
        self.config['SOD'].update({'last_file': 'example.xlsx', 'initial_language':'native', 'dict_service': 'mock'})
        self.mock_cli_output()
        
    def mock_cli_output(self):
        self.cli_output_registry = list()
        output = mock.MagicMock()
        output.console.toPlainText = lambda: '\n'.join(self.cli_output_registry)
        output.console.setText = self.set_text_mock
        output.mw.caliper = Caliper(fmetrics(char_width=1))
        output.mw.charslim = lambda: 99
        self.ss = sod_init.sod_spawn(stream_out=output)
        self.ss.cli.fh = XLSXFileHandler('./languages/example.xlsx')
        self.ss.cli.fh.wb.save = mock.MagicMock()
        self.ss.cli.dicts.dicts = {'mock': {'service':dict_mock(), 'shortname':'M'}, 
                                    'imitation': {'service':dict_mock(), 'shortname':'i'},
                                    'local': {'service':DictLocal(), 'shortname':'l'}}
        self.ss.cli.dicts.dict_service = 'mock'
        self.ss.cli.dicts.set_languages('np', 'fl')
        self.ss.cli.dicts.available_dicts.update({'mock','imitation'})
        self.ss.cli.dicts.available_dicts_short.update({'i', 'M'})
        self.ss.cli.output.cls = self.cls_mock
        self.ss.cli.send_output = self.send_output_mock
        self.ss.cli.get_lines_limit = lambda: 99
        self.manual_sep = self.config['SOD']['manual_mode_sep']
        self.init_db_len = self.ss.cli.fh.ws.init_len

    def set_text_mock(self, text): 
        self.cli_output_registry = [i for i in text.split('\n')]

    def send_output_mock(self, msg=None, *args, **kwargs): 
        self.cli_output_registry.append(msg)

    def get_console(self) -> str:
        '''Returns what is currently displayed in the console'''
        return '\n'.join(self.cli_output_registry)

    def get_added_record(self, nth) -> tuple:
        '''Returns n-th added record'''
        return self.ss.cli.fh.data[self.ss.cli.fh.ws.init_len+nth]

    def check_record(self, foreign, native, exp_row):
        '''Verify that specific record meets expectations'''
        self.assertEqual(
            (foreign, native),
            (self.ss.cli.fh.ws.cell(exp_row, 1).value, self.ss.cli.fh.ws.cell(exp_row, 2).value)
        )

    def check_count_added(self, exp, msg=None):
        self.assertEqual(self.ss.cli.fh.ws.max_row, self.ss.cli.fh.ws.init_len+exp, msg=msg)

    def check_state(self):
        return self.ss.cli.state.__dict__

    def clear_input_line(self):
        self.cli_output_registry[-1] = self.ss.sout.mw.CONSOLE_PROMPT

    def run_cmd(self, parsed_input:list):
        self.cli_output_registry[-1]+=' '.join(parsed_input)
        self.ss.run(parsed_input)
        self.cli_output_registry.append(self.ss.sout.mw.CONSOLE_PROMPT + self.ss.sout.editable_output)
        self.ss.sout.editable_output=''

    def cls_mock(self, msg=None, keep_content=False, keep_cmd=False): 
        try:
            content = self.cli_output_registry[1:] if keep_content else list() 
        except:
            content = self.cli_output_registry or list()
        self.cli_output_registry.clear() 
        if msg: self.cli_output_registry.append(msg)
        if keep_content: self.cli_output_registry.extend(content)

    
    def test_basic_inquiry_1(self):
        self.run_cmd(['M']) 
        self.run_cmd(['hello world']) 
        self.assertRegex(self.get_console(), r'1\. witaj świEcie\s+\|\s+hello world') 
        self.assertRegex(self.get_console(), r'5\. lorem ipsum\s+\|\s+dolor sit amet') 
        self.assertIn('Select for hello world', self.get_console()) 
        self.assertTrue(self.ss.cli.state.SELECT_TRANSLATIONS_MODE)

        self.assertEqual(self.ss.cli.phrase, 'hello world')
        self.assertTrue(self.ss.cli.state.SELECT_TRANSLATIONS_MODE)
        self.run_cmd(['1', '2'])
        self.assertIn(f'🖫 witaj świEcie; domyślny serwis: hello world', self.get_console())

    
    def test_basic_inquiry_2(self):
        self.run_cmd(['fl'])
        self.run_cmd(['hello world']) 
        self.run_cmd(['e1', 'm2', 'r3', 'a'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['edited_record'])
        self.run_cmd([''])
        self.assertEqual(self.ss.cli.phrase, 'default dict service for tests')
        self.run_cmd(['added_new'])
        self.assertEqual(self.get_added_record(1)[1], 'witaj świEcieedited_record; red; added_new')


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
        self.run_cmd([self.config['SOD']['manual_mode_seq']])
        self.assertTrue(self.ss.cli.state.MANUAL_MODE)
        self.run_cmd(['Newphrase'])
        self.assertTrue(self.cli_output_registry[-1], 'Phrase: Newphrase')
        self.run_cmd(['manual entry'])
        self.assertTrue(self.cli_output_registry[-1], 'manual entry')
        self.assertEqual(self.get_added_record(1)[1], 'Newphrase')


    def test_basic_inquiry_manual_2(self):
        sep = self.config['SOD']['manual_mode_sep']
        self.run_cmd(['fl'])
        self.run_cmd([sep, 'Newphrase', sep, 'manual entry'])
        self.assertEqual(self.get_added_record(1)[1], 'manual entry')

    
    def test_multiple_inquiries_manual_duplicate(self):
        init_row = self.ss.cli.fh.ws.max_row
        sep = self.config['SOD']['manual_mode_sep']
        self.run_cmd([sep, 'Newphrase', sep, 'manual entry'])
        self.assertTrue(self.ss.cli.fh.is_duplicate('Newphrase', self.ss.cli.is_from_native))
        self.assertEqual(self.get_added_record(1)[1], 'Newphrase')
        self.run_cmd([sep, 'Newphrase', sep, 'manual entry'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.assertRegex(self.get_console(), r'1\. manual entry\s+\| Newphrase')
        self.run_cmd([''])
        self.check_count_added(1)
        self.run_cmd([self.config['SOD']['manual_mode_seq']])
        self.run_cmd(['Newphrase'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for Newphrase: ')
        
        self.run_cmd(['a'])
        self.run_cmd(['Okinawa'])
        self.check_count_added(1, 'Existing phrase was not modified')
        self.assertEqual(self.ss.cli.fh.ws.cell(init_row+1, 1).value, 'Okinawa')
        self.assertEqual(self.ss.cli.fh.ws.cell(init_row+1, 2).value, 'Newphrase')
        
        
    def test_basic_inquiry_manual_abort(self):
        '''Check if both manual entry modes work properly when aborted'''
        sep = self.config['SOD']['manual_mode_sep']
        self.run_cmd([sep, 'Newphrase', sep, ''])
        self.assertEqual(self.ss.cli.fh.data.get('Newphrase'), None)
        self.assertIn(self.ss.cli.msg.SAVE_ABORTED, self.get_console())
        self.run_cmd([self.config['SOD']['manual_mode_seq']])
        self.run_cmd(['Newphrase'])
        self.run_cmd([''])
        self.assertIn(self.ss.cli.msg.SAVE_ABORTED, self.get_console())
        self.assertEqual(self.ss.cli.fh.data.get('Newphrase'), None)

    
    def test_multiple_single_inquiries(self):
        self.run_cmd(['fl', 'hello world'])
        self.run_cmd(['e1', 'a'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['_edited'])
        self.assertTrue(self.ss.cli.state.MODIFY_RES_EDIT_MODE)
        self.run_cmd(['added_new'])

        self.run_cmd(['np', 'mooning'])
        self.run_cmd(['m', '2'])
        self.run_cmd(['modded'])

        self.assertEqual(self.get_added_record(1)[1],'witaj świEcie_edited; added_new')
        self.assertEqual(self.get_added_record(2)[1],'mooningmodded')


    def test_verify_selection_pattern(self):
        self.ss.cli.translations = ['']*3
        self.ss.cli.state.SELECT_TRANSLATIONS_MODE = True
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['99']), False, 'Out of Bound')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['m2']), False)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['m2', '1']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['b1']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['a1']), False, 'Index to this Operator not allowed')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['v','s','a','s','e']), False, 'Wrong Operator')
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['e3']), True)
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['2e']), False, 'Wrong Order')
        self.assertTrue(self.cli_output_registry[-1].endswith(self.ss.cli.msg.WRONG_EDIT))
        self.assertIs(self.ss.cli.selection_cmd_is_correct(['r3']), True)


    def test_queue_handling_on_internet_connection_loss(self):
        # while in queue mode, drop internet connection and assert
        # that: 1. SOD does not fail; 2. notification in top bar is displayed;
        # 3. normal course of work can be continued

        # Begin queue
        self.run_cmd(['Q'])
        self.run_cmd(['neptune'])

        # Drop Connection
        def mock_get(*args, **kwargs): raise requests.exceptions.ConnectionError
        with mock.patch('tests.tools.dict_mock.get', mock_get):
            self.run_cmd(['kyoto'])
        self.assertIn('No Internet Connection', self.get_console()) 
        
        # continue
        self.run_cmd(['mars'])
        self.assertIn('mars', self.ss.cli.queue_dict.keys())
        self.assertNotIn('kyoto', self.cli_output_registry, 'SOD did not clean after Connection Error')
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
        self.assertIn(' 2. venus', self.get_console())
        self.assertIn(' 1. saturn', self.get_console())


    def test_queue_updates_duplicate(self):
        # Ensure that duplicates are updated 
        self.run_cmd(['Q'])
        self.run_cmd(['saturn'])
        self.run_cmd(['moon'])
        self.run_cmd(['moon'])
        t = '\n'.join(self.cli_output_registry)
        uindex = t.rfind('Updated Queue')-3
        self.assertEqual(t[uindex:], '\n'.join([' 🔃 Updated Queue',' 1. saturn',' | witaj świEcie; domyślny serwis',' 2. moon',' | witaj świEcie; domyślny serwis', ' 3. ']))


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
        t = '\n'.join(self.cli_output_registry)
        s = t.rfind(' TEST ERROR INDUCED')
        self.assertEqual(t[s:], '\n'.join([' TEST ERROR INDUCED',' 1. saturn',' | witaj świEcie; domyślny serwis', ' 2. ']))
        self.run_cmd(['none'])
        t = '\n'.join(self.cli_output_registry)
        s = t.rfind(' ⚠ No Translations')
        self.assertEqual(t[s:], '\n'.join([' ⚠ No Translations!', ' 1. saturn', ' | witaj świEcie; domyślny serwis', ' 2. ']))
     
            
    def test_lng_switch(self):
        # test various lng changes - user can define: src_lng only, or both src and tgt
        self.ss.cli.dicts.switch_languages(src_lng='pl', tgt_lng='en')
        self.assertEqual(self.ss.cli.dicts.source_lng, 'pl')
        self.assertEqual(self.ss.cli.dicts.target_lng, 'en')

        self.ss.cli.dicts.switch_languages(src_lng='en')
        self.assertEqual(self.ss.cli.dicts.source_lng, 'en')
        self.assertEqual(self.ss.cli.dicts.target_lng, 'pl')

        self.ss.cli.dicts.switch_languages(src_lng='pl', tgt_lng='en')
        self.assertEqual(self.ss.cli.dicts.source_lng, 'pl')
        self.assertEqual(self.ss.cli.dicts.target_lng, 'en')
         
        self.ss.cli.dicts.switch_languages(src_lng='ru', tgt_lng='pl')
        self.assertEqual(self.ss.cli.dicts.source_lng, 'ru')
        self.assertEqual(self.ss.cli.dicts.target_lng, 'pl')
         
        self.ss.cli.dicts.switch_languages(src_lng='en')
        self.assertEqual(self.ss.cli.dicts.source_lng, 'en')
        self.assertEqual(self.ss.cli.dicts.target_lng, 'pl')


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
        sep = self.config['SOD']['manual_mode_sep']

        self.run_cmd(['Q']) 
        self.run_cmd([next(bloats)]) 
        self.run_cmd([f'{sep} manual-entry {sep} manual-phrase'])
        self.run_cmd([next(bloats)]) 
        self.run_cmd([next(bloats)]) 
        self.assertIn('manual-entry \n | manual-phrase', self.get_console())

        # execute the queue
        self.run_cmd(['']) 
        self.run_cmd(['']) 
        self.assertIn(' ➲ [3/4]', self.get_console())
        self.assertEqual(self.get_added_record(1)[1], 'manual-entry')
             

    def test_save_simple(self):
        self.run_cmd(['moon'])
        self.run_cmd(['1', '3'])
        self.assertIn(f'🖫 witaj świEcie; czerwony: moon', self.get_console())

    
    def test_save_simple_2(self):
        self.run_cmd(['fl', 'moon'])
        self.run_cmd(['1', '3'])
        self.assertIn(f'🖫 moon: witaj świEcie; czerwony', self.get_console())


    def test_save_reverse(self):
        '''Check if entries are saved properly when reversed'''
        self.run_cmd(['moon'])
        self.run_cmd(['r1', '3'])
        self.assertIn(f'🖫 hello world; czerwony: moon', self.get_console())
    

    def test_save_duplicate_with_modified_phrase(self):
        '''Check if updating existing row works as expected'''
        self.run_cmd(['fl', 'gimcrack'])
        self.run_cmd(['1', '4', 'm'])
        self.run_cmd(['_modded'])
        self.assertIn(f'🖉 gimcrack_modded: cheap; shoddy; czerwony', self.get_console())
        self.check_count_added(0)
        self.check_record('gimcrack_modded', 'cheap; shoddy; czerwony', self.init_db_len)

    def test_cache_cleared(self):
        '''Verify that cache are cleared properly'''
        # Edit existing
        self.run_cmd(['cheap; shoddy'])
        self.run_cmd(['1', '4'])
        self.check_count_added(0)
        # Search
        self.run_cmd(['tarsier'])
        self.assertFalse(self.ss.cli.fh.validate_dtracker('cheap; shoddy'))
        self.run_cmd([''])
        # Add new
        self.run_cmd(['fl', self.manual_sep, 'new-phrase', self.manual_sep, 'new-translation'])
        self.assertFalse(self.ss.cli.fh.validate_dtracker('tarsier'))
        self.check_count_added(1)
        self.check_record('new-phrase', 'new-translation', self.init_db_len+1)
        self.assertFalse(self.ss.cli.fh.validate_dtracker('new-phrase'))
        # Search
        self.run_cmd(['quebec'])
        self.assertFalse(self.ss.cli.fh.validate_dtracker('new_phrase'))
        self.run_cmd([''])
        # Edit existing
        self.run_cmd(['maudlin'])
        self.run_cmd(['m', '3'])
        self.run_cmd(['_mod'])
        self.check_count_added(1)
        self.check_record('maudlin_mod', 'domyślny serwis', 3)

    def test_res_edit_parse(self):
        self.run_cmd(['fl', 'moon'])
        self.run_cmd(['a', 'e3', 'm', 'a'])

        # append
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Add: ')
        self.run_cmd(['sun'])
        self.assertIn('Add: sun', self.get_console())

        # edit 3rd item
        self.assertIn('Edit: czerwony', self.get_console())
        self.ss.sout.mw.CONSOLE_PROMPT = 'Edit: '
        self.run_cmd(['neptune'])
        self.assertIn('neptune', self.get_console())

        # modify phrase
        self.assertIn('Modify: moon', self.get_console())
        self.clear_input_line()
        self.run_cmd(['earth'])
        self.assertEqual(self.ss.cli.phrase, 'earth')
        

    def test_modify_phrase_with_specific_result(self):
        # Test if replacing the searched phrase with one of the results works
        self.run_cmd(['moon'])
        self.run_cmd(['m3', '2', 'a'])
        self.assertEqual(self.cli_output_registry[-1], 'Modify: red')
        self.assertEqual(self.ss.cli.phrase, 'moon')
        
        self.run_cmd([''])
        self.assertEqual(self.ss.cli.phrase, 'red', 'Phrase was not modified')
        self.run_cmd(['added_item'])
        self.check_count_added(1)
        self.assertIn(f'🖫 domyślny serwis; added_item: red', self.get_console(), 'Error during save')
        self.assertIn(self.ss.cli.prompt.PHRASE, self.cli_output_registry[-1])


    def test_duplicate_modify_phrase(self):
        self.run_cmd(['fl', 'maudlin'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['m1', '6'])
        self.run_cmd(['-edited'])
        self.check_count_added(0)
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin-edited')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'lorem ipsum')

    
    def test_duplicate_modify_phrase_2(self):
        '''Check if newly added cards are evaluated in duplicate check'''
        self.run_cmd(['fl', self.config['SOD']['manual_mode_seq']])
        self.run_cmd(['またあした'])
        self.run_cmd(['See you tomorrow'])
        self.check_count_added(1)
        self.assertTrue(self.ss.cli.fh.is_duplicate('またあした', self.ss.cli.is_from_native))
        self.run_cmd([self.config['SOD']['manual_mode_seq']])
        self.run_cmd(['またあした'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['m', 'e1'])
        self.run_cmd(['-どうぞよろしく'])
        self.run_cmd([' doloris sit Amet'])
        self.check_count_added(1)
        self.assertIn('🖉', self.get_console())
        self.assertEqual(self.ss.cli.fh.ws.cell(5, 1).value, 'またあした-どうぞよろしく')
        self.assertEqual(self.ss.cli.fh.ws.cell(5, 2).value, 'See you tomorrow doloris sit Amet')


    def test_modify_phrase_cancel(self):
        # Assert that if phrase modification is cancelled, then the save is aborted
        self.run_cmd(['moon'])
        self.run_cmd(['m3', '2'])
        self.assertEqual(self.get_console().split('\n')[-1], 'Modify: red')
        self.clear_input_line()
        self.run_cmd([''])
        self.assertIsNone(self.ss.cli.phrase)
        self.assertIn('Not Saved', self.get_console())


    def test_query_simple_run(self):
        '''Test if query is built and executed properly'''
        bloats = (y for y in EXAMPLE_PHRASES)
        self.run_cmd(['fl', 'Q']) 
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

        self.assertEqual(self.get_added_record(1), ('Mercury','witaj świEcie_edited; added_new'))
        self.assertEqual(self.get_added_record(2), ('Venus_modified', 'witaj świEcie'))
        self.assertEqual(self.get_added_record(3), ('Earth', 'red'))

 
    def test_duplicate_reversed_lng(self):
        '''check if duplicate is spotted when lng is reversed'''
        self.run_cmd(['earth'])
        self.run_cmd(['1'])
        self.run_cmd(['fl', 'witaj świEcie'])
        self.assertEqual(self.ss.cli.dicts.source_lng, 'fl')
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())


    def test_duplicate_mode_single_entry_1(self):
        '''Manage the duplicate process'''
        self.run_cmd(['np', 'definitely a wrong explanation'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['e1', '2'])
        self.run_cmd(['_edited'])
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin_edited; witaj świEcie')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'definitely a wrong explanation')
        self.assertEqual(self.ss.cli.fh.ws.max_row, self.ss.cli.fh.ws.init_len)


    def test_duplicate_mode_single_entry_2(self):
        '''Assert that modyfing existing phrase's translation does alter the original record'''
        self.run_cmd(['fl', 'maudlin'])
        self.assertIn(self.ss.cli.msg.PHRASE_EXISTS_IN_DB, self.get_console())
        self.run_cmd(['m', '2'])
        self.run_cmd(['_modified'])
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin_modified')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'witaj świEcie')
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
        self.assertEqual(self.ss.cli.dicts.dict_service, 'imitation', self.ss.cli.dicts.available_dicts)
        self.run_cmd(['fl', 'Moon'])
        self.assertEqual(self.ss.cli.queue_index, 3)
        self.assertEqual(self.ss.cli.dicts.source_lng, 'fl')
        self.run_cmd(['dict', 'mock'])
        self.assertEqual(self.ss.cli.dicts.dict_service, 'mock')
        self.assertEqual(self.ss.cli.queue_index, 3)
        self.run_cmd([''])
        self.assertEqual(set(self.ss.cli.queue_dict.keys()), {'Moon'})
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for Earth: ')


    def test_duplicate_mode_manual_oneline(self):
        '''Manage the duplicate process'''
        sep = self.config['SOD']['manual_mode_sep']
        self.run_cmd(['fl'])
        self.run_cmd([sep, 'maudlin', sep, 'Duis aute'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.run_cmd(['1'])
        self.check_count_added(0)
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'Duis aute')

    
    def test_duplicate_mode_manual_multiline(self):
        '''Manage the duplicate process'''
        self.run_cmd(['fl', self.config['SOD']['manual_mode_seq']])
        self.run_cmd(['maudlin'])
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.assertRegex(self.get_console(), r'1\. definitely a wrong explanation\s+\| maudlin')
        self.run_cmd(['a'])
        self.run_cmd(['tarsier from Quebec'])
        self.check_count_added(0)
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'tarsier from Quebec')


    def test_duplicate_mode_queue(self):
        '''Manage the duplicate process'''
        self.run_cmd(['fl', 'Q'])
        self.run_cmd(['sun'])
        self.run_cmd(['maudlin'])
        self.run_cmd(['moon'])
        self.run_cmd([''])
        self.run_cmd([''])  # skip saving
        self.assertEqual(self.ss.sout.mw.CONSOLE_PROMPT, 'Select for maudlin: ')
        self.assertIn('definitely a wrong explanation', self.get_console())
        self.run_cmd(['r4', 'a'])
        self.run_cmd(['ullamco laboris nisi'])
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 1).value, 'maudlin')
        self.assertEqual(self.ss.cli.fh.ws.cell(3, 2).value, 'red; ullamco laboris nisi')
        self.check_count_added(0)


    def test_compound_inquiries(self):
        '''Check if using consecutive modes works well'''
        # Single
        self.run_cmd(['Mercury'])
        self.run_cmd(['e1', 'a'])
        self.run_cmd(['_edited'])
        self.run_cmd(['added_new'])
        self.check_record('witaj świEcie_edited; added_new', 'Mercury', self.init_db_len+1)
        self.check_count_added(1)

        # Query
        self.run_cmd(['Q'])
        self.run_cmd(['Venus'])
        self.run_cmd(['bloat'])
        self.run_cmd([''])
        self.run_cmd(['3', 'm', 'r5'])
        self.run_cmd(['modified'])
        self.run_cmd([''])
        self.check_record('czerwony; dolor sit amet', 'Venusmodified', self.init_db_len+2)
        self.check_count_added(2)
        
        # Manual
        sep = self.config['SOD']['manual_mode_sep']
        self.run_cmd(['fl'])
        self.assertEqual(self.ss.cli.dicts.source_lng, 'fl')
        self.run_cmd([sep, 'manual-entry', sep, 'manual-input'])
        self.check_record('manual-entry', 'manual-input', self.init_db_len+3)
        self.check_count_added(3)

        # Query
        self.run_cmd(['Q'])
        self.run_cmd(['neptune'])
        self.run_cmd(['kyoto'])
        self.run_cmd([''])
        self.run_cmd(['3'])
        self.run_cmd(['e'])
        self.run_cmd(['e2'])
        self.run_cmd([''])

        # Single
        self.run_cmd(['Earth'])
        self.run_cmd(['5'])
        self.check_record('Earth', 'lorem ipsum', self.init_db_len+6)
        self.check_count_added(6)

    def test_make_cell(self):
        '''Verify that cells have correct width''' 
        scw = 1
        caliper = Caliper(fmetrics(scw))
        self.assertEqual(caliper.make_cell('text '*5, 10*scw, suffix='...'), 'text te...')
        self.assertEqual(caliper.make_cell('text text', 10*scw), 'text text ')
        self.assertEqual(caliper.make_cell('traktować kogoś z honorami', 25*scw, suffix='...'), 'traktować kogoś z ho...')
        self.assertEqual(caliper.make_cell('ええと', 11*scw), 'ええと     ')
        self.assertEqual(caliper.make_cell('ええとこのでんしやはどこに行きますか', 10*scw, suffix='...'), 'ええと... ')
        self.assertEqual(caliper.make_cell('こわいジェットコースター', 36*scw), 'こわいジェットコースター            ')
        self.assertEqual(caliper.make_cell('𨴐付', 36*scw), '𨴐付                                ')
