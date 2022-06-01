from random import randint
import db_api
from utils import *
from rev_summary import summary_generator


class main_window_logic():

    def __init__(self):
        self.QTEXTEDIT_CONSOLE = None
        
        # Flashcards parameters
        self.config = load_config()
        self.default_side = self.get_default_side()
        self.side = self.default_side
        self.file_path = self.config['onload_file_path']
        self.revmode = False
        self.cards_seen = 0
        self.signature = ''
        

    def build_backend_only(self):
        data = self.load_flashcards(self.file_path)
        if dataset_is_valid(data):
            self.update_backend_parameters(self.file_path, data)
            self.post_logic(self.get_status_dict('dataset_is_valid'))


    def post_logic(self, text):
        if self.QTEXTEDIT_CONSOLE is not None:    
            self.post_fcc(text)
        else:
            print(text)        


    def result_positive(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
    

    def result_negative(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
            self.append_current_card_to_mistakes_list()
            

    def append_current_card_to_mistakes_list(self):
        self.mistakes_list.append([self.get_current_card()[self.default_side], 
                                    self.get_current_card()[1-self.default_side]])
        

    def goto_next_card(self):
        diff_words = self.total_words - self.current_index - 1
        if diff_words >= 0:
            self.side = self.get_default_side()
            self.append_current_index()


    def append_current_index(self):
        self.current_index += 1
        self.track_cards_seen()


    def track_cards_seen(self):
        if self.current_index > self.cards_seen:
            self.cards_seen = self.current_index


    def decrease_current_index(self, value=1):
        if self.current_index >= value:
            self.current_index -= value

            
    def words_back_mode(self):
        # used for managing visibility of buttons
        # occurs when user goes to previous cards
        wordback_mode = False
        if self.words_back > 0:
            self.words_back-=1
            if self.words_back == 0 and self.revmode:
                wordback_mode = True
        return wordback_mode


    def record_revision_to_db(self, seconds_spent=0):
        db_api.create_record(self.signature, self.total_words, self.positives, seconds_spent)
        self.post_logic(self.get_dbapi_dict('create_record'))


    def goto_prev_card(self):
        self.decrease_current_index()
        self.words_back+=1    
        self.side = self.get_default_side()


    def reverse_side(self):
        self.side = 1 - self.side
        
     
    def delete_current_card(self):
        self.dataset.drop([self.current_index], inplace=True, axis=0)
        self.dataset.reset_index(inplace=True, drop=True)
        self.total_words = self.dataset.shape[0]
        self.side = self.get_default_side()
        

    def load_flashcards(self, file_path):
        try:
            dataset = load_dataset(file_path, do_shuffle=True)   
            self.post_logic(self.get_status_dict('load_dataset'))
            self.TEMP_FILE_FLAG = False
            return dataset
        except FileNotFoundError:
            self.post_logic('File Not Found.')


    def is_complete_revision(self):
        diff_words = self.total_words - self.current_index - 1
        return diff_words == 0 and self.is_revision


    def handle_saving(self, seconds_spent=0):
        
        # update timestamp
        self.signature = update_signature_timestamp(self.signature)

        save_revision(self.dataset.iloc[:self.cards_seen+1, :], self.signature)
        self.post_logic(self.get_status_dict('save_revision'))

        # Create initial record
        db_api.create_record(self.signature, self.cards_seen+1, self.positives, seconds_spent)
        
        # immediately load the revision
        new_path = self.config['revs_path'] + self.signature + '.csv'
        data = self.load_flashcards(new_path)
        self.update_backend_parameters(new_path, data)


    def change_revmode(self, force_mode='auto'):
        if self.is_revision:
            if force_mode == 'auto':
                self.revmode = not self.revmode
            else:
                self.revmode = force_mode
        else:
            self.revmode = False

    
    def update_backend_parameters(self, file_path, data, override_signature=None):

        # set updated values
        file_path_parts = file_path.split('/')
        self.filename = file_path_parts[-1].split('.')[0]
        dir_name = file_path_parts[-2]
        
        self.file_path = file_path
        self.dataset = data
        self.is_revision = True if dir_name == self.config['revs_path'][2:-1] else False
        self.change_revmode(self.is_revision)

        if override_signature is None:
            self.signature = get_signature(self.filename, str(data.columns[0])[:2], self.is_revision)
        else:
            self.signature = override_signature

        update_config('onload_file_path', file_path)

        # reset flashcards parameters
        self.current_index = 0
        self.cards_seen = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.mistakes_list = list()
        self.is_saved = False
        self.side = self.get_default_side()
        self.total_words = self.dataset.shape[0]
        self.is_mistakes_list = 'mistakes' in self.filename

        self.config = load_config()

        self.post_logic(f'{"Revision" if self.is_revision else "Language"} loaded: {self.filename}')


    def get_rating_message(self):
        dbapi = db_api.db_interface()
 
        last_positives = dbapi.get_last_positives(self.signature)
        max_positives = dbapi.get_max_positives_count(self.signature)
        last_time_spent = dbapi.get_last_time_spent(self.signature)
        summary_gen = summary_generator(self.positives, last_positives, self.total_words,
                                    max_positives, self.seconds_spent, last_time_spent)
        if 'revision_summary' in self.config['optional']:
            progress = summary_gen.get_summary_text()
        else:
            progress = 'Revision done'
        return progress


    def refresh_config(self):
        self.config = load_config()


    def get_default_side(self):
        default_side = self.config['card_default_side']
        if default_side.isnumeric():
            return int(default_side)
        elif default_side.lower().startswith('rand'):
            return randint(0,1) 

    def get_signature(self):
        return self.signature
        
    def get_current_card(self):
        return self.dataset.iloc[self.current_index, :]

    def get_positives(self):
        return self.positives

    def get_total_words(self):
        return self.total_words

    def get_words_back(self):
        return self.words_back

    def get_filepath(self):
        return self.file_path  

    def get_dataset(self):
        return self.dataset
    
    def get_current_side(self):
        return self.side
    
    def get_mistakes_list(self):
        return self.mistakes_list
    
    def get_headings(self):
        return self.dataset.columns
    
    def get_status_dict(self, key):
        try:
            return get_status_dict()[key]
        except KeyError:
            return f'Key Error on: {key}'


    def get_dbapi_dict(self, key):
        try:
            return db_api.get_dbapi_dict()[key]
        except KeyError:
            return f'Key Error on: {key}'
    

    def set_cards_seen(self, cards_seen):
        self.cards_seen = cards_seen
    

    def set_qtextedit_console(self, console):
        self.QTEXTEDIT_CONSOLE = console


    def log_add(self, traceback, exc_value=None):
        # write log traceback to the file
        register_log(traceback)

        if exc_value:  # is an error
            text_to_post = str(exc_value) + '. See log file for more details.'
        else:
            text_to_post = traceback

        try:
            self.get_fcc_sidewindow()
            self.post_fcc(text_to_post)
        except Exception:
            print(text_to_post)
