from atexit import register
from utils import *
from random import shuffle
import db_api


class fcc():
    # Flashcards console commands allows access to extra functionality
    # through the chosen console - cmd, QTextExit,...
    # Behaviour of certain function might adjust if
    # graphical interface is available.

    def __init__(self,  qtextedit_console=False):
        self.config = load_config()
        self.save_to_log = True
        self.TEMP_FILE_FLAG = False
        self.QTEXTEDIT_CONSOLE = qtextedit_console
        self.DOCS = {'help':'Says what it does - literally',
                    'mct':'Modify Cards Text - edits current side of the card both in current set and in the original file',
                    'mcr':'Modify Card Result - allows changing pos/neg for the current card',
                    'dc':'Delete Card - deletes card both in current set and in the file',
                    'lln':'Load Last N, loads N-number of words from the original file, starting from the end',
                    'cfm':'Create Flashcards from Mistakes List *[~] *[a/w] *[r/l]- initiate new set from current mistakes e.g cfm a r. "~" arg disables saving to file',
                    'efc':'Ebbinghaus Forgetting Curve - shows table with revs, days from last rev and efc score',
                    'mcp':'Modify Config Parameter - allows modifications of config file',
                    'sck':'Show Config Keys - list all available parameters in config file',
                    'cls':'Clear Screen',
                    'cfn':'Change File Name - changes currently loaded file_path, filename and all records in DB for this signature',
                    'sah':'Show Progress Chart for all languages',
                    'tts':'Total Time Spent *[last_n(1,2,3,...)] *[interval(m,d,y)] - shows amount of time (in hours) spent for each lng for each *interval. Default = 1 m',
                    'scs':'Show Current Signature',
                    'lor':'List Obsolete Revisions - returns a list of revisions that are in DB but not in revisions folder.'
                    }


    def execute_command(self, parsed_input, followup_prompt=True, save_to_log=True):
        
        if parsed_input[0] == '' and len(parsed_input) == 1:
            # exit if blank
            return

        if self.is_allowed_command(parsed_input[0]):
            self.save_to_log = save_to_log
            function_to_call = getattr(self, parsed_input[0])
            function_to_call(parsed_input)
        elif ' '.join(parsed_input[:2]).lower() == 'hello world'.lower():
            self.post_fcc('<the world salutes back>')
        else:
            self.post_fcc('Permision Denied or Unknown Command. Type help for... well - help')
        
        if followup_prompt:
            self.post_fcc(self.CONSOLE_PROMPT)


    def is_allowed_command(self, command):
        return command in self.DOCS.keys()
    

    def refresh_interface(self):
        # try refresh interface if available
        try:
            self.update_interface_parameters()
        except:
            pass


    def post_fcc(self, text): 
        if self.QTEXTEDIT_CONSOLE and len(text) > 0:
            self.console.append(text)
            if self.save_to_log:
                self.CONSOLE_LOG = self.console.toPlainText()
        else:
            print(text)


    def help(self, parsed_cmd):
        if len(parsed_cmd) == 1:
           printout = get_pretty_print(self.DOCS, extra_indent=3)
        else:
            command = parsed_cmd[1]
            printout =  get_pretty_print([[command, self.DOCS[command]]], extra_indent=3)

        self.post_fcc(printout)


    def decorator_require_nontemporary(func):
        def verify_conditions(self, *args, **kwargs):
            if not self.TEMP_FILE_FLAG:
                func(self, *args, **kwargs)
            else:
                self.post_fcc(f'{func.__name__} requires a real file.')
        return verify_conditions


    def mct(self, parsed_cmd):
        # Modify current card text - both in app and in the file

        # check preconditions
        if len(parsed_cmd) < 2:
            self.post_fcc('mc function require at least 2 arguments')
            return
            
        # change text on the card
        new_text = ' '.join(parsed_cmd[1:])
        self.dataset.iloc[self.current_index, self.side] = new_text

        # change text in the file
        mod_file_text = ''
        if not self.TEMP_FILE_FLAG:
            save_revision(self.dataset, self.signature)
            mod_file_text = ' Original file updated.'

        self.post_fcc('Card content successfully modified.' + mod_file_text)


    def mcr(self, parsed_cmd):
        # Modify Card Result - allows modification of current score

        mistakes_one_side = [x[1-self.side] for x in self.mistakes_list]
        is_mistake = self.get_current_card()[self.side] in mistakes_one_side
        is_wordsback_mode = self.get_words_back() != 0

        if not is_wordsback_mode:
            self.post_fcc('Card not yet checked. Abandoning.')
        else:
            if is_mistake:
                mistake_index = mistakes_one_side.index(self.get_current_card()[self.side])
                del self.mistakes_list[mistake_index]
                self.negatives-=1
                self.positives+=1
                self.post_fcc('Score successfully modified to positive.')
            else:
                self.append_current_card_to_mistakes_list()
                self.positives-=1
                self.negatives+=1
                self.post_fcc('Score successfully modified to negative.')
      
            self.refresh_interface()


    def dc(self, parsed_cmd):
        # Delete card - from set and from the file

        # check preconditions
        if len(parsed_cmd) != 2:
            self.post_fcc('Wrong number of args. Expected 2.')
            return
        elif parsed_cmd[1] != '-':
            self.post_fcc('Wrong confirmation sign. Expected "-".')
            return

        # Get parameters before deletion
        current_side = self.get_current_side()
        current_word = self.get_current_card()[current_side]

        # Delete from currently loaded set
        self.delete_current_card()

        # load file - if not exists: returns empty DF
        dataset_ordered = load_dataset(self.get_filepath(), do_shuffle=False)

        # modify file if exists
        file_mod_msg = ''
        if dataset_ordered.shape[0] > 0:
            dataset_ordered.drop(dataset_ordered.loc[dataset_ordered[dataset_ordered.columns[current_side]]==current_word].index, inplace=True)
            save_revision(dataset_ordered, self.signature)
            file_mod_msg = ' and from the file as well'

        # print output
        self.post_fcc(f'Card removed from the set{file_mod_msg}.')


    @decorator_require_nontemporary
    def lln(self, parsed_cmd):
        # load last N cards from dataset

        # check preconditions
        if len(parsed_cmd) != 2:
            self.post_fcc('Expected 2 args.')
            return
        elif not parsed_cmd[1].isnumeric():
            self.post_fcc('number of cards must be a number')
            return
        
        # get last N records from the file -> shuffle only the part
        n_cards = abs(int(parsed_cmd[1]))
        file_path = self.get_filepath()
        data = load_dataset(file_path, do_shuffle=False).iloc[-n_cards:, :]
        data = data.sample(frac=1).reset_index(drop=True)

        # point to non-existing file in case user modified cards
        filename = file_path.split('/')[-1].split('.')[0]
        new_path = self.config['lngs_path'] + filename + str(n_cards) + '.csv'
        
        self.update_backend_parameters(new_path, data)
        self.refresh_interface()

        self.post_fcc(f'Loaded last {n_cards} cards.')

    
    def cfm(self, parsed_cmd):
        # Create Flashcards from Mistakes list

        # Parse args - select path[rev/lng] and mode[append/write]
        mode = 'w' if 'w' in parsed_cmd[1:] else 'a'
        path = self.config['revs_path'] if 'r' in parsed_cmd[1:] else self.config['lngs_path']
        do_save = False if '~' in parsed_cmd[1:] else True

        # Create DataFrame - reverse arrays to match default_side
        reversed_mistakes_list = [[x[1], x[0]] for x in self.get_mistakes_list()]
        shuffle(reversed_mistakes_list)
        mistakes_list = pd.DataFrame(reversed_mistakes_list, columns=self.get_headings()[::-1])
                                            
        # Update[write/append] to a mistakes_list file
        lng = get_lng_from_signature(self.get_signature()).upper()
        if do_save:
            full_path = path + lng + '_mistakes.csv'
            file_exists = lng + '_mistakes.csv' in get_files_in_dir(path)
            keep_headers = True if mode == 'w' or not file_exists else False
            mistakes_list.to_csv(full_path, index=False, mode=mode, header=keep_headers)

        # shows only current mistakes
        # fake path secures original mistakes file from 
        # being overwritten by other commands such as mct or dc
        fake_path = self.config['lngs_path'] + 'mistakes_temp.csv'

        self.update_backend_parameters(fake_path, mistakes_list, override_signature=f"{lng}_mistakes")
        self.refresh_interface()
        self.reset_timer()
        self.TEMP_FILE_FLAG = True

        # allow instant save of a rev created from mistakes_list
        self.set_cards_seen(mistakes_list.shape[0]-1)
        
        msg_mode = 'written' if mode == 'w' else 'appended'
        msg_result = f'Mistakes List {msg_mode} to {full_path}' if do_save else 'Created flashcards from mistakes list'
        self.post_fcc(msg_result)
        self.del_side_window()

        
    
    def efc(self, parsed_cmd):
        # show efc table
        from efc import efc
        efc_obj = efc()
        reccommendtations = efc_obj.get_complete_efc_table()
        efc_table_printout = efc_obj.get_efc_table_printout(reccommendtations)

        self.post_fcc(efc_table_printout)
        

    def mcp(self, parsed_cmd):
        # Modify Config Parameter
         
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
            
        update_config(config_key, config_new_value)

        # load config again if available 
        try:
            self.refresh_config()
            self.post_fcc(f'Config Key {config_key} value updated to {config_new_value}')
        except:
            self.post_fcc('Config values set but not updated. Load config again to implement changes')

    
    def sck(self, parsed_cmd):
        # Show Config Keys
        keys_printout = '\n'.join(list(self.config.keys()))
        self.post_fcc(keys_printout)
    

    def cls(self, parsed_cmd):
        # Clear console
        if self.QTEXTEDIT_CONSOLE:
            self.clear_history()
        else:
            print('\n'*100)

    def clear_history(self):
        self.console.setText('')
        self.CONSOLE_LOG = ''


    @decorator_require_nontemporary
    def cfn(self, parsed_cmd):
        # Change File Name
       
        # preconditions
        if len(parsed_cmd) < 2:
            self.post_fcc('cfn requires a filename - None was provided.')
            return
        
        # change file name
        old_filename = self.file_path.split('/')[-1].split('.')[0]
        new_filename = ' '.join(parsed_cmd[1:])

        old_file_path = self.file_path
        new_file_path = self.file_path.replace(old_filename, new_filename)
        
        # rename file
        os.rename(old_file_path, new_file_path)

        # edit DB records
        dbapi = db_api.db_interface()
        dbapi.rename_signature(old_filename, new_filename)

        self.post_fcc('Filename changed successfully')
        
        # load file again
        self.initiate_flashcards(new_file_path)
    

    def sah(self, parsed_cmd):
        # Show All (languages) History chart
        self.get_progress_sidewindow(override_lng_gist=True)  
        self.post_fcc('Showing Progress Chart for all languages')


    def tts(self, parsed_cmd):
        
        # parse user input
        last_n = 1 if len(parsed_cmd) < 2 else int(parsed_cmd[1])
        interval = 'm' if len(parsed_cmd) < 3 else parsed_cmd[2]

        db_interface = db_api.db_interface()
        db = db_interface.get_all()
        lngs = [l.upper() for l in self.config['languages'].split('|')]

        date_format_dict = {
            'm': '%m/%Y',
            'd': '%d/%m/%Y',
            'y': '%Y',
        } 
        date_format = date_format_dict[interval]
        db['TIMESTAMP'] = pd.to_datetime(db['TIMESTAMP']).dt.strftime(date_format)

        # create column with time for each lng in config
        for l in lngs:  
            db[l] = db.loc[db.iloc[:, 1].str.contains(l)]['SEC_SPENT']

        # group by selected interval - removes SIGNATURE
        db = db.groupby(db['TIMESTAMP'], as_index=False, sort=False).sum()

        # cut db
        db = db.iloc[-last_n:, :]
        db = db.loc[db.iloc[:, 4] != 0]

        # format dates in time-containing columns
        for l in lngs:
            db[l] = db[l].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-'))
        db['SEC_SPENT'] = db['SEC_SPENT'].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-'))
        
        # print result
        res = db.to_string(index=False, columns=['TIMESTAMP']+lngs+['SEC_SPENT'], header=['DATE']+lngs+['TOTAL'])
        self.post_fcc(res)


    def scs(self, parsed_cmd):
        self.post_fcc(self.signature)


    def lor(self, parsed_cmd):
        db_interface = db_api.db_interface()

        unique_signatures = db_interface.get_unique_signatures().values.tolist()
        available_files = get_files_in_dir(self.config['revs_path'], include_extension=False)

        for s in available_files:
            if s in unique_signatures:
                unique_signatures.remove(s)
        
        self.post_fcc('\n'.join([f'{i+1}. {v}' for i, v in enumerate(unique_signatures) if '_mistakes' not in v]))

