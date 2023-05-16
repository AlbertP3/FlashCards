from collections import OrderedDict
from itertools import islice, takewhile
import re
from SOD.dicts import Dict_Services
from SOD.file_handler import file_handler
from utils import Config



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

class Prompt:
    def __init__(self) -> None:
        self.PHRASE = 'Search: '
        self.SELECT = 'Select for {}: '
        self.MANUAL_PH = 'Phrase: '
        self.MANUAL_TR = 'Transl: '



class CLI():

    def __init__(self, output, wb_path, ws_sheet_name) -> None:
        self.config = Config()
        self.state = State()
        self.prompt = Prompt()
        self.msg = Message()
        self.transl = str()
        self.phrase = str()
        self.queue_dict = OrderedDict()
        self.output = output
        self.d_api = Dict_Services()
        self.fh = file_handler(wb_path, ws_sheet_name)
        self.selection_queue = list()
        self.status_message = str()


    def reset_state(self):
        self.state = State()


    def set_output_prompt(self, t, aval_lefts=0):
        self.output.mw.CONSOLE_PROMPT = t
        self.output.mw.aval_lefts = aval_lefts


    def send_output(self, text:str):
        self.output.console.append(text)
        self.output.mw.CONSOLE_LOG.append(text)


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
            elif i == 'd': self.set_dict('diki')
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
            self.cls(keep_content=self.state.QUEUE_MODE, keep_cmd=self.state.QUEUE_MODE)
        else:
            self.cls(f'⚠ Wrong Dict!', keep_content=True, keep_cmd = self.state.QUEUE_MODE)


    def insert_manual(self, parsed_cmd):
        if parsed_cmd.count('$') == 2:
            self.insert_manual_oneline(parsed_cmd)
            return

        if not self.state.MANUAL_MODE:
            self.cls()
            self.set_output_prompt(self.prompt.MANUAL_PH)
            self.state.MANUAL_MODE = 'phrase'
            return
        elif self.state.MANUAL_MODE == 'phrase':
            self.phrase = ' '.join(parsed_cmd)
            if self.fh.is_duplicate(self.phrase):
                self.cls(self.msg.PHRASE_EXISTS_IN_DB, keep_content=True)
                self.fh.marked_duplicates.add(self.phrase)
            self.set_output_prompt(self.prompt.MANUAL_TR)
            self.state.MANUAL_MODE = 'transl'
            return
        elif self.state.MANUAL_MODE == 'transl':
            self.transl = ' '.join(parsed_cmd)
            if self.phrase in self.fh.marked_duplicates:
                self.translations = [self.transl, self.fh.get_translations(self.phrase)]
                self.originals = [self.phrase, self.phrase]
                self.state.SELECT_TRANSLATIONS_MODE = True
                self.set_output_prompt(f'Select for {self.phrase}: ')
                self.print_translations_table(self.translations, self.originals)
                return
        # Finalize
        if self.phrase and self.transl:
            if self.fh.is_duplicate(self.phrase):
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
            else:
                self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False
        self.set_output_prompt(self.prompt.PHRASE)


    def insert_manual_oneline(self, parsed_cmd):
        # if 2 delimiter signs are provided, treat the input
        # as a complete card.
        self.state.MANUAL_MODE = True
        delim_index = parsed_cmd.index('$', 2)
        self.phrase = ' '.join(parsed_cmd[1:delim_index])
        self.transl = ' '.join(parsed_cmd[delim_index+1:]) 
        if self.phrase and self.transl:
            if self.fh.is_duplicate(self.phrase):
                self.fh.marked_duplicates.add(self.phrase)
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                self.translations = [self.transl, self.fh.get_translations(self.phrase)]
                self.originals = [self.phrase, self.phrase]
                self.state.SELECT_TRANSLATIONS_MODE = True
                self.set_output_prompt(f'Select for {self.phrase}: ')
                self.print_translations_table(self.translations, self.originals)
            else:
                self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False


    def handle_single_entry(self, phrase):
        self.phrase = phrase
        self.translations, self.originals, self.warnings = self.d_api.get_info_about_phrase(self.phrase)
        self.cls()
        if self.translations:
            if self.fh.is_duplicate(self.phrase):
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                self.originals.insert(0, self.phrase)
                self.translations.insert(0, self.fh.get_translations(self.phrase))
                self.fh.marked_duplicates.add(self.phrase)
            self.state.SELECT_TRANSLATIONS_MODE = True
            self.set_output_prompt(f'Select for {self.phrase}: ')
            self.print_translations_table(self.translations, self.originals)
        else:
            self.cls(self.msg.NO_TRANSLATIONS)
        if self.warnings: self.send_output('\n'.join(self.warnings)+'\n')


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

        if not self.queue_dict:
            self.set_output_prompt(self.prompt.PHRASE)
            self.state.QUEUE_SELECTION_MODE = False


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
        if phrase.startswith('$'):  # Manual Mode for Queue
            l2 = ['']*3; l1 = phrase.split('$')
            l2[:len(l1)] = l1
            phrase, translations = l2[1].strip(), l2[2].strip()
            self.queue_dict[phrase] = [[translations], [phrase], ['MANUAL']]    
            cleaned_text = self.output.console.toPlainText().replace(' $ ', ' ').replace(translations,'')
            self.output.console.setText(cleaned_text)
            self.output.mw.CONSOLE_LOG = cleaned_text
            transl = translations
            warnings = None
        else:  # Online Dictionary
            translations, originals, warnings = self.d_api.get_info_about_phrase(phrase)
            if (translations or originals) and not warnings:
                self.queue_dict[phrase] = [translations, originals, warnings]
                transl = "; ".join(translations[:2]).rstrip()
                transl = transl[:c_lim]+'…' if len(transl)>c_lim else transl
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
            if self.fh.is_duplicate(phrase):
                msg = self.msg.PHRASE_EXISTS_IN_DB
                self.fh.marked_duplicates.add(phrase)
                self.queue_dict[phrase][0].insert(0, phrase)
                self.queue_dict[phrase][1].insert(0, self.fh.get_translations(phrase))
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
            transl = transl[:c_lim]+'…' if len(transl)>c_lim else transl
            s2 = f' | {transl}'
            self.send_output(s1+'\n'+s2)
            self.queue_index+=1
            self.queue_visible_items+=1
        

    def save_to_db(self, phrase:str, translations:list):
        translations:str= '; '.join([t for t in translations if t])
        if len(translations) > 0 and self.phrase:
            # match columns order in the target file
            if self.config['sod_source_lng']==self.config['native_lng']:
                phrase, translations = translations, phrase
            success, errs = self.fh.append_content(phrase, translations)    
            if success: 
                self.notify_on_save(phrase, translations)
            else:
                self.cls(errs)
        else:
            self.cls(self.msg.SAVE_ABORTED)

        self.phrase = None
        self.res_edit = None
    

    def notify_on_save(self, phrase, res_edit):
        lim = self.get_char_limit()
        msg = f'🖫 {phrase}: {res_edit}'
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
        return int(1.184 * self.output.console.width() / self.output.mw.CONSOLE_FONT_SIZE)


    def get_lines_limit(self):
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
        result = True
        pattern = re.compile(r'^(\d+|e\d+|a|m\d*|r\d+)$')
        lim = len(self.translations)
        if (self.state.SELECT_TRANSLATIONS_MODE and str(self.state.MODIFY_RES_EDIT_MODE)[0] not in 'ea') \
            and not self.state.QUEUE_SELECTION_MODE:
            all_args_match = all({pattern.match(c) for c in parsed_cmd})
            index_out_of_range = any(int(re.sub(r'[a-zA-z]', '', c))>lim for c in parsed_cmd if c not in 'amr') if all_args_match else True
            if not all_args_match or index_out_of_range:
                result = False
                self.cls(self.msg.WRONG_EDIT, keep_content=True)
        return result


    def res_edit_parse(self, parsed_cmd):
        if self.state.MODIFY_RES_EDIT_MODE[0] == 'm':
            c = self.output.console.toPlainText()
            e_index = c.rfind(': ') + 2
            self.phrase = c[e_index:]
        elif self.state.MODIFY_RES_EDIT_MODE[0] == 'a':
            self.res_edit.append(' '.join(parsed_cmd))
        elif self.state.MODIFY_RES_EDIT_MODE[0] == 'e':
            c = self.output.console.toPlainText()
            e_index = c.rfind(': ') + 2
            self.res_edit.append(c[e_index:])


    def safe_get(self, iterable, i, default=None):
        try:
            return iterable[i]
        except:
            return default


    def res_edit_set_prompt(self, r):
        if r[0] == 'm':
            phrase = self.originals[int(r[1:])-1] if len(r)>1 else self.phrase
            new_prompt = f'Modify: {phrase}' 
            aval_lefts = len(phrase)
        elif r[0] == 'a':
            new_prompt = f'Add: '
            aval_lefts = 0
        elif r[0] == 'e':
            new_prompt = f'Edit: {self.translations[int(r[1:])-1]}'
            aval_lefts = len(self.translations[int(r[1:])-1])
        else: 
            new_prompt = self.prompt.PHRASE
            aval_lefts = 0
        self.set_output_prompt(new_prompt, aval_lefts)


    def cls(self, msg=None, keep_content=False, keep_cmd=False):
        if keep_content:
            content = self.output.console.toPlainText().split('\n')
            content = content[1:] if keep_cmd else content[1:-1]
            content = '\n'.join(content)
        self.output.console.setText('')
        self.output.mw.CONSOLE_LOG = []
        self.__post_status_bar(msg)
        if keep_content: 
            self.send_output(content)


    def __post_status_bar(self, msg=None):
        active_dict = self.d_api.dict_service
        source_lng = self.d_api.source_lng
        target_lng = self.d_api.target_lng
        len_db = self.fh.ws.max_row - 1
        status = f"🕮 {active_dict} | {source_lng}⇾{target_lng} | 🛢 {len_db} | "

        if msg:
            remaining_len = self.get_char_limit() - len(status)
            status += msg[:remaining_len-1]+'…' if len(msg)>remaining_len else msg
        self.send_output(status)


    def show_help(self):
        available_dicts = '\n    '.join([f'{i+1}. {v}' for i, v in enumerate(self.d_api.get_available_dicts())])
        msg = f'''
Commands:
    1. dict <DICT_NAME>             --> change dictionary 
    2. $ <PHRASE> $ <MEANING>       --> manual input
    3. Q                            --> enter Queue mode
    4. <SRC_LNG_ID> *<TGT_LNG_ID>   --> change source/target language           
    5. <blank>                      --> exit SOD or finish the Queue mode

Search results modification:
    1. e<N>     --> edit the N-th translation
    2. m*<N>    --> modify searched phrase
    3. a        --> add a new translation
    4. r<N>     --> add a reversed translation
    5. <blank>  --> abort

Available dicts:
    {available_dicts}
    '''

        self.send_output(msg)


    def close_wb(self):
        self.fh.close()
