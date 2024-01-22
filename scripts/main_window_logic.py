import logging
from random import randint
from DBAC.api import db_interface, FileDescriptor
from utils import *
from rev_summary import SummaryGenerator

log = logging.getLogger(__name__)


class main_window_logic():

    def __init__(self):
        self.config = Config()
        self.update_default_side()
        self.default_side = self.get_default_side()
        self.side = self.default_side
        self.revmode = False
        self.total_words = 0
        self.words_back = 0
        self.current_index = 0
        self.cards_seen = 0
        self.revision_summary = None
        self.is_saved = False
        self.db = db_interface()
        self.summary_gen = SummaryGenerator()
        self.auto_cfm_offset = 0
        self.is_afterface = False


    @property
    def is_revision(self):
        return self.db.active_file.kind == 'revision'
    
    @property
    def active_file(self):
        return self.db.active_file


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
        self.db.create_record(self.total_words, self.positives, seconds_spent)


    def goto_prev_card(self):
        self.decrease_current_index()
        self.words_back+=1    
        self.side = self.get_default_side()


    def reverse_side(self):
        self.side = 1 - self.side
        
     
    def delete_current_card(self):
        self.db.delete_card(self.current_index)
        self.total_words = self.active_file.data.shape[0]
        self.side = self.get_default_side()
        

    def load_flashcards(self, fd:FileDescriptor):
        try:
            self.db.load_dataset(fd, do_shuffle=True)   
        except FileNotFoundError:
            fcc_queue.put('File Not Found.')


    def is_complete_revision(self):
        diff_words = self.total_words - self.current_index - 1
        return diff_words == 0 and self.is_revision


    def handle_saving(self, seconds_spent=0):
        self.active_file.signature = self.db.gen_signature(self.active_file.lng)
        self.db.create_record(self.cards_seen+1, self.positives, seconds_spent)
        newfp = self.db.save_revision(self.active_file.data.iloc[:self.cards_seen+1, :])
        self.load_flashcards(self.db.files[newfp])
        self.update_backend_parameters()


    def change_revmode(self, force_which=None):
        if not self.is_revision or self.is_saved:
            self.revmode = False
        elif force_which is None:
            self.revmode = not self.revmode
        else:
            self.revmode = force_which

    
    def update_backend_parameters(self):
        self.config.update({'onload_filepath': self.active_file.filepath})
        self.reset_flashcards_parameters()
        fcc_queue.put(f'{"Revision" if self.is_revision else "Language"} loaded: {self.active_file.basename}')


    def reset_flashcards_parameters(self):
        self.current_index = 0
        self.cards_seen = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.mistakes_list = list()
        self.is_saved = False
        self.side = self.get_default_side()
        self.total_words = self.active_file.data.shape[0]
        self.revision_summary = None
        self.auto_cfm_offset = 0
        self.change_revmode(self.is_revision)
        

    def save_to_mistakes_list(self):   
        mistakes_list = self.db.save_mistakes(
            mistakes_list = self.mistakes_list, 
            cols = self.active_file.data.columns, 
            offset = self.auto_cfm_offset
        )
        self.auto_cfm_offset = mistakes_list.shape[0]  
        self.db.load_tempfile(
            data = mistakes_list,
            kind = 'mistakes',
            basename = f'{self.active_file.lng} Mistakes',
            lng = self.active_file.lng,
            signature = f"{self.active_file.lng}_mistakes"
        )
        self.update_backend_parameters()
        self.update_interface_parameters()

        # allow instant save of a rev created from mistakes_list
        self.cards_seen = mistakes_list.shape[0]-1


    def get_rating_message(self):
        if 'revision_summary' in self.config['optional']:
            progress = self.summary_gen.get_summary_text(
                self.positives, self.total_words, self.seconds_spent
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
        return self.active_file.data.iloc[self.current_index, :]


    def notify_on_error(self, traceback, exc_value=None):
        log.error(traceback, exc_info=True)

        if exc_value:  # is an error
            err_msg = f"{str(exc_value)}. See log file for more details."
        else:
            err_msg = traceback

        if self.side_window_id != 'fcc':
            self.get_fcc_sidewindow()
            
        err_msg+='\n'+self.CONSOLE_PROMPT
        self.fcc_inst.post_fcc(err_msg)
