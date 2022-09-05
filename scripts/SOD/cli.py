from SOD.scraper import dict_api
from SOD.file_handler import file_handler
from collections import OrderedDict
import re
from utils import Config

class CLI():

    def __init__(self, output, wb_path, ws_sheet_name) -> None:
        self.config = Config()
        self.PHRASE_EXISTS_IN_DB = '⚐ Duplicate'
        self.PHRASE_PROMPT = 'Enter a phrase: '
        self.SAVE_ABORTED = '󠁿󠁿🗙 Not Saved'
        self.NO_TRANSLATIONS = '⚠ No Translations!'
        self.WRONG_EDIT = '⚠ Wrong Edit!'
        self.PROBLEM_OCCURRED = '❕ Error'
        self.SELECT_TRANSLATIONS_MODE = False
        self.RES_EDIT_SELECTION_MODE = False
        self.MODIFY_RES_EDIT_MODE = False
        self.MANUAL_MODE = False
        self.QUEUE_MODE = False
        self.QUEUE_SELECTION_MODE = False
        self.transl = str()
        self.phrase = str()
        self.queue_dict = OrderedDict()
        self.output = output
        self.d_api = dict_api()
        self.fh = file_handler(wb_path, ws_sheet_name)
        self.selection_queue = list()
        self.status_message = str()


    def reset_flags(self):
        self.SELECT_TRANSLATIONS_MODE = False
        self.RES_EDIT_SELECTION_MODE = False
        self.MODIFY_RES_EDIT_MODE = False
        self.MANUAL_MODE = False
        self.QUEUE_MODE = False
        self.QUEUE_SELECTION_MODE = False


    def set_output_prompt(self, t):
        self.output.CONSOLE_PROMPT = t


    def send_output(self, text:str):
        self.output.post_fcc(text)


    def execute_command(self, parsed_phrase:list):
        # set dict service
        parsed_phrase = self.handle_prefix(parsed_phrase)

        # execute command
        if not parsed_phrase:
            self.cls()
        elif parsed_phrase[0] == 'dict':
            self.set_dict(parsed_phrase[1])
        elif parsed_phrase[0] == '$':
            self.insert_manual(parsed_phrase)
        elif parsed_phrase[0] == 'Q':
            self.setup_queue()
        elif parsed_phrase[0] == 'help':
            self.show_help()
        else:
            self.handle_single_entry(' '.join(parsed_phrase))
        

    def handle_prefix(self, parsed_cmd:list):
        src_lng, tgt_lng = None, None
        for i in parsed_cmd:
            if i == 'p': self.set_dict('pons')
            elif i == 'm': self.set_dict('merriam')
            elif i == 'b': self.set_dict('babla')
            elif i in ['PL', 'EN']:
                if not src_lng: src_lng = i.lower()
                elif not tgt_lng: tgt_lng = i.lower()
            else: break
            parsed_cmd = parsed_cmd[1:]
            if src_lng or tgt_lng: 
                self.d_api.switch_languages(src_lng, tgt_lng)
        return parsed_cmd


    def set_dict(self, new_dict):
        if new_dict in self.d_api.get_available_dicts():
            self.d_api.set_dict_service(new_dict)
            self.cls(keep_content=True, keep_cmd = self.QUEUE_MODE)
        else:
            self.cls(f'⚠ Wrong Dict!', keep_content=True, keep_cmd = self.QUEUE_MODE)


    def insert_manual(self, parsed_cmd):
        if not self.MANUAL_MODE:
            self.cls()
            self.set_output_prompt('Phrase: ')
            self.MANUAL_MODE = 'phrase'
            return
        elif self.MANUAL_MODE == 'phrase':
            self.phrase = ' '.join(parsed_cmd)
            if not self.fh.is_duplicate(self.phrase):
                 self.set_output_prompt('Transl: ')
                 self.MANUAL_MODE = 'transl'
            else:
                self.MANUAL_MODE = False
                self.set_output_prompt(self.PHRASE_PROMPT)
                self.cls(self.PHRASE_EXISTS_IN_DB)
            return
        elif self.MANUAL_MODE == 'transl':
            self.transl = ' '.join(parsed_cmd)

        # Finalize
        if self.phrase and self.transl:
                self.save_to_db(self.phrase, self.transl.split(' '))
        else:
            self.cls(self.SAVE_ABORTED)
        self.MANUAL_MODE = False
        self.set_output_prompt(self.PHRASE_PROMPT)


    def handle_single_entry(self, phrase):
        self.phrase = phrase
        self.translations, self.originals, self.warnings = self.d_api.get_info_about_phrase(self.phrase)
        self.cls()
        if self.translations:
            if self.fh.is_duplicate(self.phrase):
                self.cls(self.PHRASE_EXISTS_IN_DB)
            else:
                self.SELECT_TRANSLATIONS_MODE = True
                self.set_output_prompt(f'Select for {self.phrase}: ')
            self.print_translations_table(self.translations, self.originals)
        else:
            self.cls(self.NO_TRANSLATIONS)
        if self.warnings: self.send_output('\n'.join(self.warnings)+'\n')


    def setup_queue(self):
        self.queue_dict = OrderedDict()
        self.queue_index = 1
        self.queue_page_counter = 0
        self.cls()
        self.send_output('Queue:')
        self.QUEUE_MODE = True
        self.phrase = None
        self.translations = None
        self.set_output_prompt(f'{self.queue_index:>2d}. ')


    def setup_queue_unpacking(self):
        if self.queue_dict:
            self.QUEUE_MODE = False
            self.QUEUE_SELECTION_MODE = True
            self.unpack_translations_from_queue()
        else:
            self.reset_flags()
            self.cls()
            self.set_output_prompt(self.PHRASE_PROMPT)


    def manage_queue(self, parsed_cmd:list):
        self.queue_builder(parsed_cmd) 
        self.set_output_prompt(f'{self.queue_index:>2d}. ')

            
    def unpack_translations_from_queue(self, parsed_cmd=None):
        while self.queue_dict:
            p, rs = self.queue_dict.popitem(last=False)
            self.queue_page_counter+=1
            is_duplicate = self.fh.is_duplicate(p)
            if not is_duplicate:
                self.cls(f'➲ [{self.queue_page_counter}/{self.queue_index-1}]:')
                self.print_translations_table(rs[0], rs[1])
                self.phrase = p
                self.translations = rs[0]
                self.set_output_prompt(f'Select for {p}: ')
                self.SELECT_TRANSLATIONS_MODE = True
                break

        if not self.queue_dict:
            if is_duplicate: 
                self.set_output_prompt(self.PHRASE_PROMPT)
            self.QUEUE_SELECTION_MODE = False


    def queue_builder(self, parsed_cmd:list):
        if parsed_cmd[0] == 'del': 
            self.del_from_queue(parsed_cmd[1:])
            return

        c_lim = self.get_char_limit() - 3
        phrase:str = ' '.join(self.handle_prefix(parsed_cmd))
        if phrase.startswith('$'):  # Manual Mode for Queue
            l2 = ['']*3; l1 = phrase.split('$')
            l2[:len(l1)] = l1
            phrase, translations = l2[1], l2[2]
            self.queue_dict[phrase] = [[translations.strip()], [phrase.strip()], list()]    
            cleaned_text = self.output.console.toPlainText().replace(' $ ', ' ').replace(translations,'')
            self.output.console.setText(cleaned_text)
            transl = translations
            warnings = None
        else:
            translations, originals, warnings = self.d_api.get_info_about_phrase(phrase)
            if translations or originals:
                self.queue_dict[phrase] = [translations, originals, warnings]
                transl = "; ".join(translations[:2]).rstrip()
                transl = transl[:c_lim]+'…' if len(transl)>c_lim else transl
            else:
                transl = 'N/A'

        if self.fh.is_duplicate(phrase): msg = self.PHRASE_EXISTS_IN_DB
        elif warnings: msg = self.PROBLEM_OCCURRED
        else: msg = '✅ OK'
        self.cls(msg, keep_content=True, keep_cmd=True )
        self.send_output(f' | {transl}')
        self.queue_index+=1


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
        c_lim = self.get_char_limit() - 3
        for phrase, info in self.queue_dict.items():
            s1 = f'{self.queue_index:>2d}. {phrase}'
            transl = "; ".join(info[0][:2]).rstrip()
            transl = transl[:c_lim]+'…' if len(transl)>c_lim else transl
            s2 = f' | {transl}'
            self.send_output(s1+'\n'+s2)
            self.queue_index+=1
        self.set_output_prompt(f'{self.queue_index:>2d}. ')
            

    def save_to_db(self, phrase:str, translations:list):
        translations:str= '; '.join(translations)
        if len(translations) > 0:
            # match columns order in the target file
            if self.config['sod_source_lng']==self.config['native_lng']:
                phrase, translations = translations, phrase
            if self.d_api.dict_service != 'mock':
                self.fh.append_content(phrase, translations)    
            self.notify_on_save(phrase, translations)
        else:
            self.cls(self.SAVE_ABORTED)

        self.phrase = None
        self.res_edit = None
    

    def notify_on_save(self, phrase, res_edit):
        lim = self.get_char_limit()
        msg = f"🖫 {phrase}: {res_edit}"
        self.cls(msg[:lim]+'…' if len(msg)>lim else msg)


    def print_translations_table(self, trans, origs):
        output = str()
        lim = self.get_char_limit()
        if ''.join(origs)!='': lim = int(lim/2) - 3; sep=' | '
        else: lim = lim-1; sep=''
        for i in range(len(trans)):
            t = trans[i][:lim-1] + '…' if len(trans[i]) > lim else trans[i].ljust(lim, ' ')
            o = origs[i][:lim-1] + '…' if len(origs[i]) > lim else origs[i].ljust(lim, ' ')
            output+=f'{i+1}. {t}{sep}{o}' + '\n'
        self.send_output(output[:-1])
        

    def get_char_limit(self):
        return int(1.134 * self.output.console.width() / self.output.CONSOLE_FONT_SIZE)


    def select_translations(self, parsed_cmd):
        if not self.selection_cmd_is_correct(parsed_cmd): return
        
        if self.SELECT_TRANSLATIONS_MODE:
            self.selection_queue = parsed_cmd
            self.res_edit = list()
            self.SELECT_TRANSLATIONS_MODE = False
            self.RES_EDIT_SELECTION_MODE = True
        
        if self.RES_EDIT_SELECTION_MODE:
            for _ in range(len(self.selection_queue)):
                v : str = self.selection_queue.pop(0)
                if not v:
                    break
                elif v.isnumeric(): 
                    self.res_edit.append(self.translations[int(v)-1])
                else:
                    self.RES_EDIT_SELECTION_MODE = False
                    self.MODIFY_RES_EDIT_MODE = v
                    self.res_edit_set_prompt(v)
                    return
        elif self.MODIFY_RES_EDIT_MODE:
            self.res_edit_parse(parsed_cmd)
            self.MODIFY_RES_EDIT_MODE = False
            self.RES_EDIT_SELECTION_MODE = True
            if self.selection_queue:
                self.select_translations(None)
                return

        if not self.selection_queue:
            self.save_to_db(self.phrase, self.res_edit)
            self.RES_EDIT_SELECTION_MODE = False
            self.MODIFY_RES_EDIT_MODE = False
                 
        if self.QUEUE_SELECTION_MODE:
            self.unpack_translations_from_queue()
        else:
            self.set_output_prompt(self.PHRASE_PROMPT)


    def selection_cmd_is_correct(self, parsed_cmd):
        result = True
        pattern = re.compile(r'^(\d+|e\d+|[am])$')
        lim = len(self.translations)
        if (self.SELECT_TRANSLATIONS_MODE and str(self.MODIFY_RES_EDIT_MODE)[0] not in 'ea') \
            and not self.QUEUE_SELECTION_MODE:
            all_args_match = all({pattern.match(c) for c in parsed_cmd})
            index_out_of_range = any(int(re.sub(r'[a-zA-z]', '', c))>lim for c in parsed_cmd if c not in 'am') if all_args_match else True
            if not all_args_match or index_out_of_range:
                result = False
                self.cls(self.WRONG_EDIT, keep_content=True)
        return result


    def res_edit_parse(self, parsed_cmd):
        if self.MODIFY_RES_EDIT_MODE[0] == 'm':
            self.phrase = ' '.join(parsed_cmd)
        elif self.MODIFY_RES_EDIT_MODE[0] == 'a':
            self.res_edit.append(' '.join(parsed_cmd))
        elif self.MODIFY_RES_EDIT_MODE[0] == 'e':
            c = self.output.console.toPlainText()
            e_index = c.rfind(' | ') + 3
            self.res_edit.append(c[e_index:])


    def safe_get(self, iterable, i, default=None):
        if i < len(iterable):
            return iterable[i]
        else:
            return default


    def res_edit_set_prompt(self, r):
        if r[0] == 'm': new_prompt = f'Modify: {self.phrase} | '
        elif r[0] == 'a': new_prompt = f'Add: '
        elif r[0] == 'e': new_prompt = f'Edit:{str(r)[1:]} | {self.translations[int(r[1:])-1]}'
        else: new_prompt = self.PHRASE_PROMPT
        self.set_output_prompt(new_prompt)

    
    def create_queue_backup(self):
        with open('queue_dict.txt', 'a') as file:
            for p, t in self.queue_dict.items():
                file.write(f'{p};;;{"; ".join(t)}')
        self.send_output('Created backup of the Queue')


    def cls(self, msg=None, keep_content=False, keep_cmd=False):
        if keep_content:
            content = self.output.console.toPlainText().split('\n')
            content = content[1:] if keep_cmd else content[1:-1]
            content = '\n'.join(content)
        self.output.cls()
        self.post_status_bar(msg)
        if keep_content: 
            self.send_output(content)


    def post_status_bar(self, msg=None):
        active_dict = self.d_api.get_dict_service()
        source_lng = self.d_api.source_lng
        target_lng = self.d_api.target_lng
        len_db = self.fh.ws.max_row - 1
        status = f"🕮 {active_dict} | {source_lng}⇾{target_lng} | 🛢 {len_db} | "

        if msg:
            remaining_len = self.get_char_limit() - len(status)
            status += msg[:remaining_len-1]+'…' if len(msg)>remaining_len else msg
        
        self.send_output(status)


    def show_help(self):
        msg = f'''
                    Welcome to Search Online Dictionaries v1.0
-------------------------------------------------------------------
X - look for phrase | dict X - set dict to X | $ - manual input |
Q - enter queue mode
search results modification: prepend with 'e' to edit; 'm' to modify
phrase; 'a' to add new translation; empty to abort
Available dicts: {self.d_api.get_available_dicts()}'''
        self.send_output(msg)


    def close_wb(self):
        self.fh.close()
