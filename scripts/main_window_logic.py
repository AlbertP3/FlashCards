from random import randint
import db_api
from utils import *
from rev_summary import summary_generator


class main_window_logic():

    def __init__(self):
        self.config = Config()
        self.default_side = self.get_default_side()
        self.side = self.default_side
        self.file_path = self.config['onload_file_path']
        self.revmode = False
        self.cards_seen = 0
        self.signature = ''
        self.revision_summary = None
        self.TIMER_KILLED_FLAG = False
        self.TEMP_FILE_FLAG = False
        self.is_revision = False
        self.last_modification_time = None
        self.is_saved = False
        self.dbapi = db_api.db_interface()
        

    def build_backend_only(self):
        data = self.load_flashcards(self.file_path)
        if dataset_is_valid(data):
            self.update_backend_parameters(self.file_path, data)
            self.post_logic(UTILS_STATUS_DICT['dataset_is_valid'])


    def post_logic(self, text):
        self.post_fcc(text)


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
        wordback_mode = False
        if self.words_back > 0:
            self.words_back-=1
            if self.words_back == 0 and self.revmode:
                wordback_mode = True
        return wordback_mode


    def record_revision_to_db(self, seconds_spent=0):
        self.dbapi.create_record(self.signature, self.total_words, self.positives, seconds_spent)
        self.post_logic(db_api.DBAPI_STATUS_DICT['create_record'])


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
            self.post_logic(UTILS_STATUS_DICT['load_dataset'])
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
        self.post_logic(UTILS_STATUS_DICT['save_revision'])

        # Create initial record
        self.dbapi.create_record(self.signature, self.cards_seen+1, self.positives, seconds_spent)
        
        # immediately load the revision
        new_path = self.config['revs_path'] + self.signature + '.csv'
        data = self.load_flashcards(new_path)
        self.update_backend_parameters(new_path, data)


    def change_revmode(self, force_which=None):
        if not self.is_revision:
            self.revmode = False
        elif force_which is None:
            self.revmode = not self.revmode
        else:
            self.revmode = force_which

    
    def update_backend_parameters(self, file_path, data, override_signature=None):
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

        self.config.update({'onload_file_path': file_path})

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
        self.is_mistakes_list = 'mistakes' in self.filename.lower()
        self.revision_summary = None
        self.TIMER_KILLED_FLAG = False
        self.last_modification_time = os.path.getmtime(self.file_path) if not self.TEMP_FILE_FLAG else 9999999999
        
        self.post_logic(f'{"Revision" if self.is_revision else "Language"} loaded: {self.filename}')


    def get_rating_message(self):
        last_positives = self.dbapi.get_last_positives(self.signature, req_pos=True)
        max_positives = self.dbapi.get_max_positives_count(self.signature)
        last_time_spent = self.dbapi.get_last_time_spent(self.signature, req_pos=True)
        summary_gen = summary_generator(self.positives, last_positives, self.total_words,
                                    max_positives, self.seconds_spent, last_time_spent)
        if 'revision_summary' in self.config['optional']:
            progress = summary_gen.get_summary_text()
        else:
            progress = 'Revision done'
        return progress


    def get_default_side(self):
        default_side = self.config['card_default_side']
        if default_side.isnumeric():
            return int(default_side)
        elif default_side.lower().startswith('rand'):
            return randint(0,1) 


    def get_current_card(self):
        return self.dataset.iloc[self.current_index, :]


    def notify_on_error(self, traceback, exc_value=None):
        register_log(traceback)

        if exc_value:  # is an error
            text_to_post = str(exc_value) + '. See log file for more details.'
        else:
            text_to_post = traceback

        self.get_fcc_sidewindow()
        self.post_fcc(text_to_post)
