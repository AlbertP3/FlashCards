import logging
from random import randint
import db_api
from utils import *
from rev_summary import SummaryGenerator

log = logging.getLogger(__name__)


class main_window_logic():

    def __init__(self):
        self.config = Config()
        self.dataset = pd.DataFrame()
        self.update_default_side()
        self.default_side = self.get_default_side()
        self.side = self.default_side
        self.file_path = self.config['onload_file_path']
        self.revmode = False
        self.total_words = 0
        self.current_index = 0
        self.cards_seen = 0
        self.signature = ''
        self.revision_summary = None
        self.TEMP_FILE_FLAG = False
        self.is_revision = False
        self.is_mistakes_list = False
        self.last_modification_time = None
        self.is_saved = False
        self.dbapi = db_api.db_interface()
        self.summary_gen = SummaryGenerator()
        self.auto_cfm_offset = 0
        self.is_afterface = False

        
    def post_logic(self, text):
        self.fcc_inst.post_fcc(text)


    def result_positive(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
    

    def result_negative(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
            self.append_current_card_to_mistakes_list()
            

    def append_current_card_to_mistakes_list(self):
        self.mistakes_list.append(self.get_current_card().to_list())
        

    def goto_next_card(self):
        if self.total_words >= self.current_index + 1:
            self.side = self.get_default_side()
            self.append_current_index()


    def append_current_index(self):
        self.current_index += 1
        # Track cards seen
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
            if dataset.empty: self.post_logic(UTILS_STATUS_DICT['load_dataset'])
            self.TEMP_FILE_FLAG = dataset.empty
            return dataset
        except FileNotFoundError:
            self.post_logic('File Not Found.')
            self.TEMP_FILE_FLAG = True


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
        new_path = os.path.join(self.config['revs_path'], f'{self.signature}.csv')
        data = self.load_flashcards(new_path)
        self.update_backend_parameters(new_path, data)


    def change_revmode(self, force_which=None):
        if not self.is_revision or self.is_saved:
            self.revmode = False
        elif force_which is None:
            self.revmode = not self.revmode
        else:
            self.revmode = force_which

    
    def update_backend_parameters(self, file_path, data, override_signature=None):
        self.filename = file_path.split('/')[-1].split('.')[0]
        self.file_path = file_path
        self.dataset = data
        self.is_revision = os.path.normpath(os.path.dirname(file_path)) == os.path.normpath(self.config['revs_path'])

        if override_signature is None:
            self.signature = get_signature(self.filename, str(data.columns[0])[:2], self.is_revision)
        else:
            self.signature = override_signature

        self.config.update({'onload_file_path': file_path})
        self.reset_flashcards_parameters()
        self.post_logic(f'{"Revision" if self.is_revision else "Language"} loaded: {self.filename}')


    def reset_flashcards_parameters(self):
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
        self.last_modification_time = os.path.getmtime(self.file_path) if not self.TEMP_FILE_FLAG else 9999999999
        self.auto_cfm_offset = 0
        self.change_revmode(self.is_revision)
        

    def save_to_mistakes_list(self):
        # auto_cfm_offset - avoid duplicating cards on multiple saves of the same dataset
        mistakes_list = pd.DataFrame(data=self.mistakes_list, columns=self.dataset.columns)
        lng = get_lng_from_signature(self.signature).upper()
        full_path = os.path.join(self.config['lngs_path'], f'{lng}_mistakes.csv')
        try:
            buffer:pd.DataFrame = load_dataset(full_path, do_shuffle=False)
        except FileNotFoundError:
            buffer = pd.DataFrame()
        buffer = pd.concat([buffer, mistakes_list.iloc[self.auto_cfm_offset:]], ignore_index=True)
        overflow = int(self.config['mistakes_buffer'])
        buffer.iloc[-overflow:].to_csv(full_path, index=False, mode='w', header=True)

        m_cnt = mistakes_list.shape[0] - self.auto_cfm_offset
        self.post_logic(f'{m_cnt} card{"s" if m_cnt>1 else ""} saved to Mistakes List')
        self.auto_cfm_offset = mistakes_list.shape[0]

        # show only the current mistakes as flashcards
        fake_path = os.path.join(self.config['lngs_path'], f'{lng} Mistakes.csv')
        self.TEMP_FILE_FLAG = True
        self.update_backend_parameters(fake_path, mistakes_list, override_signature=f"{lng}_mistakes")
        self.update_interface_parameters()

        # allow instant save of a rev created from mistakes_list
        self.cards_seen = mistakes_list.shape[0]-1


    def get_rating_message(self):
        if 'revision_summary' in self.config['optional']:
            progress = self.summary_gen.get_summary_text(
                self.signature, self.positives, self.total_words, self.seconds_spent
            )
        else:
            progress = 'Revision done'
        return progress


    def update_default_side(self):
        # substitute get_default_side() via a first-class function
        default_side = self.config['card_default_side']
        if default_side.isnumeric():
            default_side = int(default_side)
            self.get_default_side =  lambda: default_side
        else:
            self.get_default_side = lambda: randint(0,1) 


    def get_current_card(self):
        return self.dataset.iloc[self.current_index, :]


    def notify_on_error(self, traceback, exc_value=None):
        log.error(traceback)

        if exc_value:  # is an error
            err_msg = f"[{datetime.now():%H:%M:%S}] {str(exc_value)}. See log file for more details."
        else:
            err_msg = traceback

        if self.side_window_id != 'fcc':
            self.get_fcc_sidewindow()
            
        err_msg+='\n'+self.CONSOLE_PROMPT
        self.fcc_inst.post_fcc(err_msg)
