from collections import OrderedDict
from itertools import islice
import logging
import re
import os
from SOD.dicts import Dict_Services
from SOD.file_handler import get_filehandler, FileHandler
from DBAC.api import db_interface
from utils import Config, get_pretty_print

log = logging.getLogger(__name__)


class State:
    def __init__(self) -> None:
        self.SELECT_TRANSLATIONS_MODE = False
        self.RES_EDIT_SELECTION_MODE = False
        self.MODIFY_RES_EDIT_MODE = False
        self.MANUAL_MODE = False
        self.QUEUE_MODE = False
        self.QUEUE_SELECTION_MODE = False
        self.DUPLICATE_MODE = False

class Message:
    def __init__(self) -> None:
        self.PHRASE_EXISTS_IN_DB = '⚐ Duplicate'
        self.SAVE_ABORTED = '󠁿󠁿🗙 Not Saved'
        self.NO_TRANSLATIONS = '⚠ No Translations!'
        self.WRONG_EDIT = '⚠ Wrong Edit!'
        self.OK = '✅ OK'
        self.QUERY_UPDATE = "🔃 Updated Queue"
        self.RE_ERROR = '⚠ Regex Error!'
        self.RE_WARN = '⚠ Nothing Matched Regex!'
        self.UNSUP_EXT = '⚠ Unsupported File Extension'
        self.FILE_MISSING = '⚠ File Does Not Exist!'

class Prompt:
    def __init__(self) -> None:
        self.PHRASE = 'Search: '
        self.SELECT = 'Select for {}: '
        self.MANUAL_PH = 'Phrase: '
        self.MANUAL_TR = 'Transl: '



class CLI():

    def __init__(self, output) -> None:
        self.config = Config()
        self.state = State()
        self.prompt = Prompt()
        self.msg = Message()
        self.transl = str()
        self.phrase = str()
        self.queue_dict = OrderedDict()
        self.output = output
        self.init_cli_args()
        self.re_excl_dirs = re.compile(self.config['SOD']['exclude_pattern'], re.IGNORECASE)
        self.dicts = Dict_Services()
        self.dbapi = db_interface()
        self.fh = None
        self.update_file_handler(self.config['SOD']['last_file'])
        self.selection_queue = list()
        self.status_message = str()

    
    def init_cli_args(self):
        self.sep_manual = self.config['SOD']['manual_mode_sep']
        self.dict_arg = self.config['SOD']['dict_change_arg']
        self.queue_arg = self.config['SOD']['queue_start_arg']
        self.chg_db_arg = self.config['SOD']['change_db_arg']


    def __init_set_languages(self):
        if self.config['SOD']['initial_language'] == 'auto':
            ref = self.config['SOD']['last_src_lng']
        else:
            ref = self.config['SOD']['initial_language']
        r = 1 if ref=='native' else -1
        native, foreign = self.fh.get_languages()[::r]
        self.dicts.set_languages(native, foreign)
        self.config['SOD']['last_src_lng'] = ref


    @property
    def is_from_native(self) -> bool:
        return self.dicts.source_lng==self.fh.native_lng

    @property
    def using_local_db(self) -> bool:
        return self.dicts.dict_service == 'local'


    def update_file_handler(self, filepath:str) -> FileHandler:
        try:
            if not os.path.exists(filepath):
                filepath = self.dbapi.match_from_all_languages(
                    repat=re.compile(filepath, re.IGNORECASE),
                    exclude_dirs=self.re_excl_dirs
                )[0]
            fh = get_filehandler(filepath)
            if self.fh:
                self.fh.close()
            self.fh = fh
            self.__init_set_languages()
            self.cls(f"Loaded {os.path.basename(filepath)}")
        except re.error:
            self.cls(self.msg.RE_ERROR, keep_content=True)
        except IndexError:
            self.cls(self.msg.RE_WARN, keep_content=True)
        except AttributeError:
            self.cls(
                self.msg.UNSUP_EXT + f' {filepath.split(".")[-1]}!', keep_content=True
            )
        except TypeError:
            pass
        else:  # success
            return
        if not self.fh:  # last file does not exist
            self.fh = get_filehandler('.void')
            self.__init_set_languages()
            self.cls(self.msg.FILE_MISSING, keep_content=True)


    def reset_state(self):
        self.state = State()


    def set_output_prompt(self, t):
        self.output.mw.CONSOLE_PROMPT = t


    def send_output(self, text:str):
        self.output.console.append(text)
        self.output.mw.CONSOLE_LOG.append(text)


    def execute_command(self, parsed_phrase:list):
        parsed_phrase = self.handle_prefix(parsed_phrase)
        if not parsed_phrase:
            return
        elif parsed_phrase[0] == self.dict_arg and len(parsed_phrase) == 2:
            self.set_dict(parsed_phrase[1])
        elif parsed_phrase.count(self.config['SOD']['manual_mode_sep']) == 2:
            self.insert_manual_oneline(parsed_phrase)
        elif parsed_phrase[0] == self.config['SOD']['manual_mode_seq']:
            self.insert_manual(parsed_phrase)
        elif parsed_phrase[0] == self.queue_arg:
            self.setup_queue()
        elif parsed_phrase[0] == 'help':
            self.show_help()
        else:
            self.handle_single_entry(' '.join(parsed_phrase))
        

    def handle_prefix(self, parsed_cmd:list):
        src_lng, tgt_lng, capture = None, None, None
        for i in parsed_cmd:
            if capture:
                if capture == 'change_db':
                    self.update_file_handler(i)
                    src_lng, tgt_lng = self.fh.get_languages()
                capture = None
            elif i in self.dicts.available_dicts_short:
                target_dict = {k for k, v in self.dicts.dicts.items() if v['shortname'] == i}.pop()
                self.set_dict(target_dict)
            elif i in self.dicts.available_lngs:
                if not src_lng: src_lng = i.lower()
                elif not tgt_lng: tgt_lng = i.lower()
            elif i == self.chg_db_arg:
                capture = 'change_db'
            else: break
            parsed_cmd = parsed_cmd[1:]
            if bool(src_lng) ^ bool(tgt_lng):
                self.dicts.switch_languages(src_lng, tgt_lng)
                self.update_last_source_lng()
            elif src_lng and tgt_lng:
                self.dicts.set_languages(src_lng, tgt_lng)
                self.update_last_source_lng()
        return parsed_cmd


    def set_dict(self, new_dict):
        if new_dict in self.dicts.available_dicts:
            self.dicts.set_dict_service(new_dict)
            self.cls(keep_content=self.state.QUEUE_MODE, keep_cmd=self.state.QUEUE_MODE)
        else:
            self.cls(f'⚠ Wrong Dict!', keep_content=True, keep_cmd = self.state.QUEUE_MODE)


    def update_last_source_lng(self):
        lng = 'native' if self.dicts.source_lng == self.fh.native_lng else 'foreign'
        self.config['SOD']['last_src_lng'] = lng


    def insert_manual(self, parsed_cmd):
        if not self.state.MANUAL_MODE:
            self.cls()
            self.set_output_prompt(self.prompt.MANUAL_TR if self.is_from_native else self.prompt.MANUAL_PH)
            self.state.MANUAL_MODE = 'first'
            return
        elif self.state.MANUAL_MODE == 'first':
            self.phrase = ' '.join(parsed_cmd)
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                self.manual_duplicate_show()
                return
            self.set_output_prompt(self.prompt.MANUAL_PH if self.is_from_native else self.prompt.MANUAL_TR)
            self.state.MANUAL_MODE = 'second'
            return
        elif self.state.MANUAL_MODE == 'second':
            self.transl = ' '.join(parsed_cmd)
        # Finalize
        if self.phrase and self.transl:
            self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False
        self.set_output_prompt(self.prompt.PHRASE)


    def manual_duplicate_show(self):
        '''If manually entered phrase exists in db then print results from source'''
        prev_dict = self.dicts.dict_service
        self.dicts.dict_service = 'local'
        self.translations, self.originals, _ = self.dicts.get_info_about_phrase(self.phrase)
        self.state.MANUAL_MODE = False
        self.state.SELECT_TRANSLATIONS_MODE = True
        self.set_output_prompt(f'Select for {self.phrase}: ')
        self.cls(self.msg.PHRASE_EXISTS_IN_DB)
        self.print_translations_table(self.translations, self.originals)
        self.dicts.dict_service = prev_dict


    def insert_manual_oneline(self, parsed_cmd):
        # if 2 delimiter signs are provided, treat the input as a complete card.
        self.state.MANUAL_MODE = True
        delim_index = parsed_cmd.index(self.sep_manual, 2)
        self.phrase = ' '.join(parsed_cmd[1:delim_index])
        self.transl = ' '.join(parsed_cmd[delim_index+1:]) 
        if self.phrase and self.transl:
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                prev_dict = self.dicts.dict_service
                self.dicts.dict_service = 'local'
                tran, orig, _ = self.dicts.get_info_about_phrase(self.phrase)
                self.translations, self.originals = [self.transl, *tran], [self.phrase, *orig]
                self.state.SELECT_TRANSLATIONS_MODE = True
                self.set_output_prompt(f'Select for {self.phrase}: ')
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                self.print_translations_table(self.translations, self.originals)
                self.dicts.dict_service = prev_dict
            else:
                self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False


    def handle_single_entry(self, phrase):
        self.phrase = phrase
        self.translations, self.originals, self.warnings = self.dicts.get_info_about_phrase(self.phrase)
        self.cls()
        if self.translations:
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                if not self.using_local_db:
                    tran, orig = self.fh.get_translations(self.phrase, self.is_from_native)
                    for i in range(len(tran)):
                        self.originals.insert(0, orig[i])
                        self.translations.insert(0, tran[i])
            self.state.SELECT_TRANSLATIONS_MODE = True
            self.set_output_prompt(f'Select for {self.phrase}: ')
            self.print_translations_table(self.translations, self.originals)
        else:
            if self.warnings: 
                self.cls(self.warnings[0])
            else:
                self.cls(self.msg.NO_TRANSLATIONS)
        

    def setup_queue(self):
        self.queue_dict = OrderedDict()
        self.queue_index = 1
        self.queue_page_counter = 0
        self.queue_visible_items = 0
        self.cls()
        self.state.QUEUE_MODE = True
        self.phrase = None
        self.translations = None
        self.set_output_prompt(f'{self.queue_index:>2d}. ')


    def setup_queue_unpacking(self):
        if self.queue_dict:
            self.state.QUEUE_MODE = False
            self.state.QUEUE_SELECTION_MODE = True
            self.unpack_translations_from_queue()
        else:
            self.reset_state()
            self.cls()
            self.set_output_prompt(self.prompt.PHRASE)


    def manage_queue(self, parsed_cmd:list):
        self.queue_builder(parsed_cmd) 
        self.set_output_prompt(f'{self.queue_index:>2d}. ')

            
    def unpack_translations_from_queue(self, parsed_cmd=None):
        if self.queue_dict or self.state.MODIFY_RES_EDIT_MODE:
            self.__unpack_translations_from_queue()
        else:
            self.set_output_prompt(self.prompt.PHRASE)
            self.state.QUEUE_SELECTION_MODE = False


    def __unpack_translations_from_queue(self):
        while self.queue_dict:
            p, rs = self.queue_dict.popitem(last=False)
            self.queue_page_counter+=1
            self.phrase = p
            if 'MANUAL' in rs[2]: 
                self.save_to_db(p, rs[0])
            else:
                self.cls(f'➲ [{self.queue_page_counter}/{self.queue_index-1}]:')
                self.print_translations_table(rs[0], rs[1])
                self.translations = rs[0]
                self.originals = rs[1]
                self.set_output_prompt(self.prompt.SELECT.format(p))
                self.state.SELECT_TRANSLATIONS_MODE = True
                break


    def queue_builder(self, parsed_cmd:list):
        if parsed_cmd[0] == 'del': 
            self.del_from_queue(parsed_cmd[1:])
            return
        elif parsed_cmd[0] == 'dict':
            self.set_dict(parsed_cmd[1])
            return

        c_lim = self.get_char_limit() - 3
        phrase:str = ' '.join(self.handle_prefix(parsed_cmd))
        exists_in_queue = phrase in self.queue_dict.keys()
        if phrase.startswith(self.sep_manual):  # Manual Mode for Queue
            l2 = ['']*3; l1 = phrase.split(self.sep_manual)
            l2[:len(l1)] = l1
            phrase, translations = l2[1].strip(), l2[2].strip()
            self.queue_dict[phrase] = [[translations], [phrase], ['MANUAL']]    
            cleaned_text = self.output.console.toPlainText().replace(f' {self.sep_manual} ', ' ').replace(translations,'')
            self.output.console.setText(cleaned_text)
            self.output.mw.CONSOLE_LOG = cleaned_text
            transl = translations
            warnings = None
        else:  # Online Dictionary
            translations, originals, warnings = self.dicts.get_info_about_phrase(phrase)
            if (translations or originals) and not warnings:
                self.queue_dict[phrase] = [translations, originals, warnings]
                transl = "; ".join(translations[:2]).rstrip()
                transl = transl[:c_lim]+self.config['THEME']['default_suffix'] if len(transl)>c_lim else transl
            else:
                transl = ''
                warnings = warnings if warnings else [self.msg.NO_TRANSLATIONS]
        
        if exists_in_queue:
            self.cls(msg=self.msg.QUERY_UPDATE)
            self.print_queue()
        elif warnings:
            msg = warnings[0]
            self.cls(msg, keep_content=False, keep_cmd=True)
            self.print_queue()  
        else: 
            if self.fh.is_duplicate(phrase, self.is_from_native):
                msg = self.msg.PHRASE_EXISTS_IN_DB
                if not self.using_local_db:
                    tran, orig = self.fh.get_translations(phrase, self.is_from_native)
                    for i in range(len(tran)):
                        self.queue_dict[phrase][0].insert(0, orig[i])
                        self.queue_dict[phrase][1].insert(0, tran[i])
                self.queue_dict[phrase][2].append('DUPLICATE')
            else:
                msg = self.msg.OK

            lim_items = int(self.get_lines_limit()/2)-2
            if self.queue_visible_items+1 > lim_items:
                self.cls(msg, keep_content=False, keep_cmd=True)
                self.print_queue(slice_=[len(self.queue_dict)-lim_items, 0])
            else:
                self.cls(msg, keep_content=True, keep_cmd=True )
                self.send_output(f' | {transl}')
                self.queue_index+=1
                self.queue_visible_items+=1


    def del_from_queue(self, indices:list):
        if indices:
            if not all([i.isnumeric() for i in indices]): return
        else:
            indices = [len(self.queue_dict.keys())]
        indices = [int(i) for i in indices if int(i) <= len(self.queue_dict.keys())]
        l_k = list(self.queue_dict.keys())
        for i in indices:
            self.queue_dict.pop(l_k[i-1])
        self.queue_index = 1
        self.cls()
        self.print_queue()
        self.set_output_prompt(f'{self.queue_index:>2d}. ')
            
    
    def print_queue(self, slice_:list=[0, 0]):
        c_lim = self.get_char_limit() - 3
        if slice_[0]<0: slice_[0] = len(self.queue_dict) + slice_[0] 
        if slice_[1]==0: slice_[1] = len(self.queue_dict)
        self.queue_index = slice_[0]+1
        self.queue_visible_items = 0
        for phrase, info in islice(self.queue_dict.items(), slice_[0], slice_[1]):
            s1 = f'{self.queue_index:>2d}. {phrase}'
            transl = "; ".join(info[0][:2]).rstrip()
            transl = transl[:c_lim-self.output.mw.caliper.exlen(transl)]+self.config['THEME']['default_suffix'] if self.output.mw.caliper.strlen(transl)>c_lim else transl
            s2 = f' | {transl}'
            self.send_output(s1+'\n'+s2)
            self.queue_index+=1
            self.queue_visible_items+=1
        

    def save_to_db(self, phrase:str, translations:list):
        translations:str= '; '.join([t for t in translations if t])
        if len(translations) > 0 and self.phrase:
            is_duplicate = self.fh.validate_dtracker(phrase)
            
            if self.is_from_native:
                phrase, translations = translations, phrase

            if is_duplicate:
                success, errs = self.fh.edit_content(phrase, translations)
            else:
                success, errs = self.fh.append_content(phrase, translations)

            if success: 
                self.notify_on_save(phrase, translations, is_duplicate)
            else:
                self.cls(errs)
        else:
            self.cls(self.msg.SAVE_ABORTED)

        self.phrase = None
        self.res_edit = None
    

    def notify_on_save(self, phrase, res_edit, is_duplicate):
        icon = '🖉' if is_duplicate else '🖫'
        msg = f'{icon} {phrase}: {res_edit}'
        self.cls(msg)


    def print_translations_table(self, trans, origs):
        if ''.join(origs) != '':
            sep='|'
            clim = int((self.get_char_limit()-1) // 2)
            if self.config['SOD']['table_ext_mode'] == 'fix':
                output = self.__ptt(trans, origs, clim, clim, sep)
            elif self.config['SOD']['table_ext_mode'] == 'flex':
                llim = min(clim, max(self.output.mw.caliper.strlen(i) for i in trans)+5)
                rlim = self.get_char_limit() - llim
                output = self.__ptt(trans, origs, llim, rlim, sep)
        else:
            clim = self.get_char_limit()
            output = self.__ptt(trans, origs, clim, clim, '')
        self.send_output(output[:-1])


    def __ptt(self, trans:list, origs:list, llim:int, rlim:int, sep:str) -> str:
        output = list()
        suffix = self.config['THEME']['default_suffix']
        align = self.config['SOD']['cell_alignment']
        for i, (t, o) in enumerate(zip(trans, origs)):
            i = f"{i+1}."
            t = self.output.mw.caliper.make_cell(t, llim - len(i)-2, suffix, align)
            o = self.output.mw.caliper.make_cell(o, rlim - len(sep)-2, suffix, align)
            output.append(f"{i} {t} {sep} {o}")
        return '\n'.join(output)
    

    def get_char_limit(self) -> int:
        return self.output.mw.charslim()


    def get_lines_limit(self) -> int:
        return int(0.589 * self.output.console.height() / self.output.mw.CONSOLE_FONT_SIZE)


    def select_translations(self, parsed_cmd):
        if not self.selection_cmd_is_correct(parsed_cmd): return
        
        if self.state.SELECT_TRANSLATIONS_MODE:
            self.selection_queue = parsed_cmd
            self.res_edit = list()
            self.state.SELECT_TRANSLATIONS_MODE = False
            self.state.RES_EDIT_SELECTION_MODE = True
        
        if self.state.RES_EDIT_SELECTION_MODE:
            for _ in range(len(self.selection_queue)):
                v : str = self.selection_queue.pop(0)
                if not v:
                    break
                elif v.isnumeric():
                    self.res_edit.append(self.translations[int(v)-1])
                elif v[0] == 'r':
                    i = int(v[1:])-1
                    self.res_edit.append(self.originals[i])
                else:
                    self.state.RES_EDIT_SELECTION_MODE = False
                    self.state.MODIFY_RES_EDIT_MODE = v
                    self.res_edit_set_prompt(v)
                    return
        elif self.state.MODIFY_RES_EDIT_MODE:
            self.res_edit_parse(parsed_cmd)
            self.state.MODIFY_RES_EDIT_MODE = False
            self.state.RES_EDIT_SELECTION_MODE = True
            if self.selection_queue:
                self.select_translations(None)
                return

        if not self.selection_queue:
            self.save_to_db(self.phrase, self.res_edit)
            self.state.RES_EDIT_SELECTION_MODE = False
            self.state.MODIFY_RES_EDIT_MODE = False
                 
        if self.state.QUEUE_SELECTION_MODE:
            self.unpack_translations_from_queue()
        else:
            self.set_output_prompt(self.prompt.PHRASE)


    def selection_cmd_is_correct(self, parsed_cmd):
        result, all_args_match, index_out_of_range = True, False, False
        pattern = re.compile(r'^(\d+|e\d+|a|m\d*|r\d+|)$')
        lim = len(self.translations)
        if (self.state.SELECT_TRANSLATIONS_MODE and str(self.state.MODIFY_RES_EDIT_MODE)[0] not in 'ea'):
            if len(parsed_cmd)==1 and parsed_cmd[0].startswith('m'):
                all_args_match = False
            else:
                all_args_match = all({pattern.match(c) for c in parsed_cmd})
                index_out_of_range = any(int(re.sub(r'[a-zA-z]', '', c))>lim for c in parsed_cmd if c not in 'amr') if all_args_match else True
            if not all_args_match or index_out_of_range:
                result = False
                self.cls(self.msg.WRONG_EDIT, keep_content=True)
        return result


    def res_edit_parse(self, parsed_cmd):
        if self.state.MODIFY_RES_EDIT_MODE[0] == 'm':
            c = self.output.console.toPlainText()
            e_index = c.rfind('Modify: ') + 8
            self.phrase = c[e_index:]
            self.fh.update_dtracker(new_phrase=self.phrase)
        elif self.state.MODIFY_RES_EDIT_MODE[0] == 'a':
            self.res_edit.append(' '.join(parsed_cmd))
        elif self.state.MODIFY_RES_EDIT_MODE[0] == 'e':
            c = self.output.console.toPlainText()
            e_index = c.rfind('Edit: ') + 6
            self.res_edit.append(c[e_index:])


    def res_edit_set_prompt(self, r):
        if r[0] == 'm':
            new_prompt = 'Modify: ' 
            extra = self.originals[int(r[1:])-1] if len(r)>1 else self.phrase
        elif r[0] == 'a':
            new_prompt = f'Add: '
            extra = ''
        elif r[0] == 'e':
            new_prompt = f'Edit: '
            extra = self.translations[int(r[1:])-1]
        else: 
            new_prompt = self.output.mw.CONSOLE_PROMPT
            extra = ''
        self.set_output_prompt(new_prompt)
        self.output.editable_output = extra


    def cls(self, msg='', keep_content=False, keep_cmd=False):
        if keep_content:
            content = self.output.console.toPlainText().split('\n')
            content = content[1:] if keep_cmd else content[1:-1]
            content = '\n'.join(content)
        self.output.console.setText('')
        self.output.mw.CONSOLE_LOG = []
        self.__post_status_bar(msg)
        if keep_content and content: 
            self.send_output(content)


    def __post_status_bar(self, msg=''):
        active_dict = self.dicts.dict_service
        source_lng = self.dicts.source_lng
        target_lng = self.dicts.target_lng
        len_db = self.fh.total_rows
        status = f"🕮 {active_dict} | {source_lng}⇾{target_lng} | 🛢 {self.fh.filename} | 🃟 {len_db} | {msg}"
        self.send_output(self.output.mw.caliper.make_cell(
            status, self.get_char_limit()-2, self.config['THEME']['default_suffix'], align='left').rstrip()
        )


    def show_help(self):
        available_dicts = '\t'+'\n\t'.join([f"{k:<10} {v['shortname']}" for k, v in self.dicts.dicts.items()])
        cmds = get_pretty_print([
            [f'\t{self.chg_db_arg} <DB_NAME>', 'change database file'], 
            [f'\t{self.config["SOD"]["manual_mode_seq"]}', 'Enter the manual input mode'],
            [f"\t{self.sep_manual} <PHRASE> {self.sep_manual} <MEANING>", "manual input"], 
            ['\tQ', 'enter Queue mode'], 
            ["\t(<SRC_LNG_ID>^<TGT_LNG_ID>)", "change source/target language "], 
            ["\t<blank>", "exit SOD or finish the Queue mode"]
            ],
            separator='-->', alingment=['<', '<'])
        mods = get_pretty_print([
            ["\te<N>", 'edit the N-th translation'],
            ["\tm*<N>", 'modify searched phrase'],
            ["\ta", 'add a new translation'],
            ["\tr<N>", 'add a reversed translation'],
            ["\t<blank>", 'abort']
            ],
            separator='-->', alingment=['<', '<'])
        msg = f'''Commands:\n{cmds}\nSearch results modification:\n{mods}\nAvailable dicts:\n{available_dicts}'''

        self.cls()
        self.send_output(msg)


    def close_wb(self):
        self.fh.close()
