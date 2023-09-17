import re 
from utils import *
from random import shuffle
import db_api
from operator import methodcaller

# Optional modules
from SOD.init import sod_spawn
from EMO.init import emo_spawn
from CMG.init import cmg_spawn



class fcc():
    # Flashcards console commands allows access to extra functionality

    def __init__(self,  mw):
        self.mw = mw
        self.config = Config()
        self.console = self.mw.console
        self.DOCS = {
                    'help':'Gets Help',
                    'mct':'Modify Cards Text - edits current side of the card both in current set and in the original file',
                    'rcc':'Reverse Current Card - changes sides of currently displayed card and updates the source file',
                    'mcr':'Modify Card Result - allows changing pos/neg for the current card',
                    'dcc':'Delete Current Card - deletes card both in current set and in the file',
                    'lln':'Load Last N, loads N-number of words from the original file, starting from the end',
                    'cfm':'Create Flashcards from Mistakes List *[~] *[a/w] *[r/l]- initiate new set from current mistakes e.g cfm a r. "~" arg disables saving to file',
                    'efc':'Ebbinghaus Forgetting Curve *N - shows table with revs, days from last rev and efc score; optional N for number of intervals. Additionaly, shows predicted time until the next revision',
                    'mcp':'Modify Config Parameter - allows modifications of config file',
                    'sck':'Set Config Key - edit configs key. If no value provided then shows current one',
                    'cls':'Clear Screen',
                    'cfn':'Change File Name - changes currently loaded file_path, filename and all records in DB for this signature',
                    'sah':'Show Progress Chart for all languages',
                    'tts':'Total Time Spent *[last_n(1,2,3,...)] *[interval(m,d,y)] - shows amount of time (in hours) spent for each lng for each *interval. Default = 1 m',
                    'scs':'Show Current Signature',
                    'lor':'List Obsolete Revisions - returns a list of revisions that are in DB but not in revisions folder.',
                    'sod':'Scrape online dictionary - *<word/s> *-d <dict name>. Default - curr card in google translate.',
                    'gwd':'Get Window Dimensions',
                    'pcc':'Pull Current Card - load the origin file and updates the currently displayed card',
                    'sfs':'Set Font Size - sets font for current card and returns info on width, height and text len',
                    'sod':'Scrape Online Dictionary - fetch data from online sources using a cli',
                    'emo':'EFC Model Optimzer - employs regression and machine learning techniques to adjust efc model for the user needs',
                    'rgd':'Reset Geometry Defaults',
                    'err':'Raises an Exception'
                    }


    def execute_command(self, parsed_input:list, followup_prompt:bool=True):
        if not parsed_input[-1]:
            return
        elif self.is_allowed_command(parsed_input[0]):
            methodcaller(parsed_input[0], parsed_input)(self)
        else:
            self.post_fcc(f'{parsed_input[0]}: command not found...')
        if followup_prompt:
            self.post_fcc(self.mw.CONSOLE_PROMPT)
        else:
            self.mw.move_cursor_to_end()


    def is_allowed_command(self, command):
        return command in self.DOCS.keys()
    

    def refresh_interface(self):
        self.mw.update_interface_parameters()


    def post_fcc(self, text:str): 
        self.console.append(text)
        self.mw.CONSOLE_LOG.append(text)
    

    def update_console_id(self, new_console):
        self.console = new_console


    def help(self, parsed_cmd):
        if len(parsed_cmd) == 1:
           printout = get_pretty_print(self.DOCS, alingment=['<', '<'], separator='-')
        else:
            command = parsed_cmd[1]
            if command in self.DOCS.keys():
                printout =  get_pretty_print([[command, self.DOCS[command]]], alingment=['<', '<'], separator='-')
            else: # regex search command descriptions
                rp = re.compile(parsed_cmd[1])
                matching = {}
                for k, v in self.DOCS.items():
                    if rp.search(v):
                        matching[k] = v
                try:
                    printout = get_pretty_print(matching, alingment=['<', '<'], separator='-')
                except IndexError:
                    printout = 'Nothing matches the given phrase!'

        self.post_fcc(printout)


    def require_nontemporary(func):
        def verify_conditions(self, *args, **kwargs):
            if not self.mw.TEMP_FILE_FLAG:
                func(self, *args, **kwargs)
            else:
                self.post_fcc(f'{func.__name__} requires a real file.')
        return verify_conditions


    def mct(self, parsed_cmd):
        '''Modify Current Card'''
        cmg = cmg_spawn(stream_out=self)
        cmg.modify_current_card(parsed_cmd)
    

    def rcc(self, parsed_cmd):
        '''Reverse Current Card'''
        cmg = cmg_spawn(stream_out=self)
        cmg.reverse_current_card(parsed_cmd)


    def mcr(self, parsed_cmd):
        '''Modify Card Result - allows modification of current score'''

        mistakes_one_side = [x[1-self.mw.side] for x in self.mw.mistakes_list]
        is_mistake = self.mw.get_current_card()[self.mw.side] in mistakes_one_side
        is_wordsback_mode = self.mw.words_back != 0

        if not is_wordsback_mode:
            self.post_fcc('Card not yet checked.')
        else:
            if is_mistake:
                mistake_index = mistakes_one_side.index(self.mw.get_current_card()[self.mw.side])
                del self.mw.mistakes_list[mistake_index]
                self.mw.negatives-=1
                self.mw.positives+=1
                self.post_fcc('Score modified to positive.')
            else:
                self.mw.append_current_card_to_mistakes_list()
                self.mw.positives-=1
                self.mw.negatives+=1
                self.post_fcc('Score modified to negative.')
      
            self.mw.update_score_button() 


    def dcc(self, parsed_cmd):
        '''Delete current card - from set and from the file'''

        # check preconditions
        if len(parsed_cmd) != 2:
            self.post_fcc('Wrong number of args. Expected 2.')
            return
        elif parsed_cmd[1] != '-':
            self.post_fcc('Wrong confirmation sign. Expected "-".')
            return

        # Get parameters before deletion
        current_word = self.mw.get_current_card()[self.mw.side]

        self.mw.delete_current_card()

        dataset_ordered = load_dataset(self.mw.filepath, do_shuffle=False)

        # modify file if exists
        file_mod_msg = ''
        if dataset_ordered.shape[0] > 0:
            dataset_ordered.drop(dataset_ordered.loc[dataset_ordered[dataset_ordered.columns[self.mw.side]]==current_word].index, inplace=True)
            save_revision(dataset_ordered, self.mw.signature)
            file_mod_msg = ' and from the file as well'

        # print output
        self.post_fcc(f'Card removed from the set{file_mod_msg}.')


    @require_nontemporary
    def lln(self, parsed_cmd):
        '''load last N cards from dataset'''

        if not parsed_cmd[1].isnumeric():
            self.post_fcc('number of cards must be a number')
            return
        
        # get last N records from the file -> shuffle only the part
        n_cards = abs(int(parsed_cmd[1]))
        try: 
            l_cards = abs(int(parsed_cmd[2]))
        except IndexError: 
            l_cards = 0

        file_path = self.mw.file_path
        if l_cards == 0:
            data = load_dataset(file_path, do_shuffle=False).iloc[-n_cards:, :]
        else:
            n_cards, l_cards = sorted([n_cards, l_cards], reverse=True)
            data = load_dataset(file_path, do_shuffle=False).iloc[-n_cards:-l_cards, :]

        data = shuffle_dataset(data)

        # point to non-existing file in case user modified cards
        filename = file_path.split('/')[-1].split('.')[0]
        new_path = os.path.join(self.config['lngs_path'], f"{filename}{str(len(data))}.csv")
        
        self.mw.TEMP_FILE_FLAG = True
        self.mw.del_side_window()
        self.mw.update_backend_parameters(new_path, data)
        self.refresh_interface()
        self.mw.reset_timer()
        self.mw.start_file_update_timer()
        self.post_fcc(f'Loaded last {len(data)} cards.')

    
    def cfm(self, parsed_cmd):
        '''Create Flashcards from Mistakes list'''

        if self.mw.cards_seen == 0:
            self.post_fcc('Unable to save an empty file')
            return

        # Parse args - select path[rev/lng] and mode[append/write]
        mode = 'w' if 'w' in parsed_cmd[1:] else 'a'
        path = self.config['revs_path'] if 'r' in parsed_cmd[1:] else self.config['lngs_path']
        do_save = False if '~' in parsed_cmd[1:] else True

        # Create DataFrame - reverse arrays to match default_side
        reversed_mistakes_list = [[x[1], x[0]] for x in self.mw.mistakes_list]
        shuffle(reversed_mistakes_list)
        mistakes_list = pd.DataFrame(reversed_mistakes_list, columns=self.mw.dataset.columns[::-1])
                                            
        # [write/append] to a mistakes_list file
        lng = get_lng_from_signature(self.mw.signature).upper()
        if do_save:
            full_path = os.path.join(path, f"{lng}_mistakes.csv")
            file_exists = f"{lng}_mistakes.csv" in get_files_in_dir(path)
            keep_headers = True if mode == 'w' or not file_exists else False
            mistakes_list.to_csv(full_path, index=False, mode=mode, header=keep_headers)

        # shows only current mistakes
        # fake path secures original mistakes file from 
        # being overwritten by other commands such as mct or dc
        fake_path = os.path.join(self.config['lngs_path'], f'{lng} Mistakes.csv')
        self.mw.TEMP_FILE_FLAG = True

        self.mw.update_backend_parameters(fake_path, mistakes_list, override_signature=f"{lng}_mistakes")
        self.refresh_interface()
        self.mw.reset_timer()

        # allow instant save of a rev created from mistakes_list
        self.mw.cards_seen = mistakes_list.shape[0]-1
        
        msg_mode = 'written' if mode == 'w' else 'appended'
        msg_result = f'Mistakes List {msg_mode} to {full_path}' if do_save else 'Created flashcards from mistakes list'
        self.post_fcc(msg_result)
        self.mw.del_side_window()

        
    
    def efc(self, parsed_cmd):
        '''Show EFC Table'''
        from efc import efc
        efc_obj = efc()
        efc_obj.refresh_source_data()
        reccommendations = efc_obj.get_complete_efc_table(preds=True)
        if len(parsed_cmd) >= 2 and parsed_cmd[1].isnumeric():
            lim = int(parsed_cmd[1])
        else:
            lim = None
        efc_table_printout = efc_obj.get_efc_table_printout(reccommendations, lim)
        self.post_fcc(efc_table_printout)
        

    def mcp(self, parsed_cmd):
        '''Modify Config Parameter'''
         
        # check preconditions
        if len(parsed_cmd) < 3:
            self.post_fcc('mcp function expected following syntax: mcp dict_key dict new value')
            return

        config_key = parsed_cmd[1]  
        config_new_value = ' '.join(parsed_cmd[2:])

        # check if input key exists in dict
        if config_key not in self.config.keys():
            self.post_fcc('mcp function takes only existing dict keys. Use "sck" to show all available keys.')
            return
        self.config.update({config_key: config_new_value})

    
    def sck(self, parsed_cmd):
        '''Set Config Key'''
        if len(parsed_cmd) == 1:
            c = [['Key', 'Value']]
            c.extend(list([k, str(v)[:50]] for k, v in self.config.items()))
            msg = get_pretty_print(c, separator='|', 
                    alingment=['<', '^'], keep_last_border=True)
        elif len(parsed_cmd) == 2:
            p = re.compile(parsed_cmd[1])
            matching = {k:v for k, v in self.config.items() if p.search(k)}
            if matching:
                c = [['Key', 'Value']]
                c.extend(list([k, str(v)[:50]] for k, v in matching.items()))
                msg = get_pretty_print(c, separator='|', 
                    alingment=['<', '^'], keep_last_border=True)
            else:
                msg = self.config.get(parsed_cmd[1], 'N/A')
                if isinstance(msg, list): msg = '|'.join(msg)
        elif len(parsed_cmd) > 2:
            if parsed_cmd[1] in (k for k, v in self.config.items() if isinstance(v, dict)):
                if not self.config[parsed_cmd[1]].get(parsed_cmd[2]): 
                    msg = f"Key {parsed_cmd[2]} does not exist"
                else:
                    new_val = ' '.join(parsed_cmd[3:])
                    self.config[parsed_cmd[1]][parsed_cmd[2]] = new_val
                    self.config.parse_items()
                    msg = f"Key {parsed_cmd[2]} set to {new_val}"
            else:
                if not self.config.get(parsed_cmd[1]): 
                    msg = f"Key {parsed_cmd[1]} does not exist"
                else:
                    new_val = ' '.join(parsed_cmd[2:])
                    self.config[parsed_cmd[1]] = new_val
                    self.config.parse_items()
                    msg = f"Key {parsed_cmd[1]} set to {new_val}"
        else:
            msg = 'Invalid syntax'
        self.post_fcc(msg)
    

    def cls(self, parsed_cmd=None):
        '''Clear Console'''
        last_line = self.console.toPlainText().split('\n')[-1]
        if last_line.startswith(self.mw.CONSOLE_PROMPT):
            new_console_log = [last_line]
            new_text = last_line
        else:
            new_console_log = []
            new_text = ''
        self.console.setText(new_text)
        self.mw.CONSOLE_LOG = new_console_log


    @require_nontemporary
    def cfn(self, parsed_cmd):
        '''Change File Name'''
       
        # preconditions
        if len(parsed_cmd) < 2:
            self.post_fcc('cfn requires a filename - None was provided.')
            return
        
        # change file name
        old_filename = self.mw.file_path.split('/')[-1].split('.')[0]
        new_filename = ' '.join(parsed_cmd[1:])

        old_file_path = self.mw.file_path
        new_file_path = self.mw.file_path.replace(old_filename, new_filename)
        
        # rename file
        os.rename(old_file_path, new_file_path)

        # edit DB records
        dbapi = db_api.db_interface()
        dbapi.rename_signature(old_filename, new_filename)

        self.post_fcc('Filename changed successfully')
        
        # load file again
        self.mw.initiate_flashcards(new_file_path)
    

    def sah(self, parsed_cmd):
        '''Show All (languages) History chart'''
        self.mw.del_side_window()
        self.mw.get_progress_sidewindow(override_lng_gist=True)  
        self.post_fcc('Showing Progress Chart for all languages')


    def tts(self, parsed_cmd):
        '''Total Time Spent'''

        # parse user input
        last_n = 1 if len(parsed_cmd) < 2 else int(parsed_cmd[1])
        interval = 'm' if len(parsed_cmd) < 3 else parsed_cmd[2]

        db_interface = db_api.db_interface()
        db_interface.refresh()
        lngs = [l.upper() for l in self.config['languages']]
        db = db_interface.get_filtered_by_lng(lngs)

        date_format_dict = {
            'm': '%m/%Y',
            'd': '%d/%m/%Y',
            'y': '%Y',
        } 
        date_format = date_format_dict[interval]
        db['TIMESTAMP'] = pd.to_datetime(db['TIMESTAMP']).dt.strftime(date_format)

        # create column with time for each lng in config
        grand_total_time = list()
        for l in lngs:  
            db[l] = db.loc[db.iloc[:, 1].str.contains(l)]['SEC_SPENT']
            grand_total_time.append(db[l].sum())

        # group by selected interval - removes SIGNATURE
        db = db.groupby(db['TIMESTAMP'], as_index=False, sort=False).sum()
        
        # cut db
        db = db.iloc[-last_n:, :]
        try:
            db = db.loc[db.iloc[:, 4] != 0]
        except IndexError:
            self.post_fcc(f'DATE  {"  ".join([l.upper() for l in lngs])}{"  TOTAL" if len(lngs)>1 else ""}')
            return

        # format dates in time-containing columns
        visible_total_time = list()
        for l in lngs:
            visible_total_time.append(db[l].sum())
            db[l] = db[l].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-'))
        db['SEC_SPENT'] = db['SEC_SPENT'].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-'))
        
        # print result
        if len(lngs) > 1:
            res = db.to_string(index=False, columns=['TIMESTAMP']+lngs+['SEC_SPENT'], header=['DATE']+lngs+['TOTAL'])
            visible_total_time.append(sum(visible_total_time))
            grand_total_time.append(sum(grand_total_time))
        else:
            res = db.to_string(index=False, columns=['TIMESTAMP']+lngs, header=['DATE']+['TOTAL'])

        # add row for Grand Total
        visible_total_time = [format_seconds_to(t, "hour", null_format="-", max_len=5) for t in visible_total_time]
        grand_total_time = [format_seconds_to(t, "hour", null_format="-", max_len=5) for t in grand_total_time]
        res += '\n' + '-'*len(res.split('\n')[1])
        res += '\n∑        ' + '  '.join(visible_total_time)
        res += '\nTOTAL    ' + '  '.join(grand_total_time)

        self.post_fcc(res)


    def scs(self, parsed_cmd):
        '''Show Current Signature'''
        self.post_fcc(self.mw.signature)


    def lor(self, parsed_cmd):
        '''Pist Obsolete Revisions'''
        db_interface = db_api.db_interface()

        unique_signatures = db_interface.get_unique_signatures().values.tolist()
        available_files = get_files_in_dir(self.config['revs_path'], include_extension=False)

        for s in available_files:
            if s in unique_signatures:
                unique_signatures.remove(s)
        
        self.post_fcc('\n'.join([f'{i+1}. {v}' for i, v in enumerate(unique_signatures) if '_mistakes' not in v]))


    def gwd(self, parsed_cmd):
        '''Get Window Dimensions'''
        w = self.mw.frameGeometry().width()
        h = self.mw.frameGeometry().height()
        self.post_fcc(f"W:{int(w)} H:{int(h)}")
    

    def pcc(self, parsed_cmd):
        '''Pull Current Card'''
        new_data = load_dataset(self.mw.file_path, seed=self.config['pd_random_seed'])
        self.mw.dataset.iloc[self.mw.current_index, :2] = new_data.iloc[self.mw.current_index, :2]
        self.mw.display_text(self.mw.get_current_card()[self.mw.side])


    def sfs(self, parsed_cmd):
        '''Set Font Size'''
        if len(parsed_cmd)<2 or not parsed_cmd[1].isnumeric():
            self.post_fcc('SFS requires at least one, numeric argument')
            return
        
        self.mw.display_text(forced_size=int(parsed_cmd[1]))
        self.post_fcc(f'FONT_SIZE:{parsed_cmd[1]} | ' \
                    + f'TEXT_LEN={len(self.mw.get_current_card()[self.mw.side])} | ' \
                    + f'WIDTH={self.mw.frameGeometry().width()} | HEIGHT={self.mw.frameGeometry().height()}')
    

    def rgd(self, parsed_cmd):
        '''Reset Geometry Default'''
        if len(parsed_cmd)==1:
            for w in self.config['GEOMETRY']:
                self.config['GEOMETRY'][w] = self.config['GEOMETRY']['default']
            self.post_fcc("All windows were resized to default")
        elif parsed_cmd[1].lower() in self.config['GEOMETRY'].keys():
            self.config['GEOMETRY'][parsed_cmd[1].lower()] = self.config['GEOMETRY']['default']
            self.post_fcc(f"{parsed_cmd[1].lower()} window was resized to default")
        else:
            self.post_fcc('Specified window does not exist. See config to list of available windows')


    def sod(self, parsed_cmd:list):
        '''Scrape Online Dictionaries'''
        self.sod_object = sod_spawn(stream_out=self)


    def emo(self, parsed_cmd:list):
        '''EFC Model Optimizer'''
        self.emo_object = emo_spawn(stream_out=self)


    def err(self, parsed_cmd:list):
        '''Raise an Exception'''
        raise Exception(f"{' '.join(parsed_cmd[1:])}")