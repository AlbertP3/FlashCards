import logging
from random import randint
from DBAC.api import DbOperator, FileDescriptor
from utils import *
from rev_summary import SummaryGenerator

log = logging.getLogger(__name__)


class main_window_logic():

    def __init__(self):
        self.config = Config()
        self.current_index = 0
        self.words_back = 0
        self.cards_seen_sides = list()
        self.update_default_side()
        self.add_default_side()
        self.default_side = self.get_default_side()
        self.side = self.default_side
        self.revmode = False
        self.total_words = 0
        self.cards_seen = 0
        self.revision_summary = None
        self.is_saved = False
        self.db = DbOperator()
        self.summary_gen = SummaryGenerator()
        self.auto_cfm_offset = 0
        self.is_afterface = False


    @property
    def is_revision(self):
        return self.db.active_file.kind == self.db.KINDS.rev
    
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
            self.append_current_index()
            self.side = self.get_default_side()


    def append_current_index(self):
        self.current_index += 1
        # Track cards seen
        if self.current_index > self.cards_seen:
            self.cards_seen = self.current_index
            self.add_default_side()
        

    def decrease_current_index(self, value=1):
        if self.current_index >= value:
            self.current_index -= value

            
    def words_back_mode(self):
        if self.words_back > 0:
            self.words_back-=1
            if self.words_back == 0 and self.revmode:
                return True
        return False


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


    def should_create_db_record(self):
        return (
            not self.is_saved
            and self.total_words - self.current_index - 1 == 0 
            and self.active_file.kind in self.db.GRADED 
        )


    def handle_creating_revision(self, seconds_spent=0):
        self.active_file.signature = self.db.gen_signature(self.active_file.lng)
        self.active_file.kind = self.db.KINDS.rev
        if isinstance(self.active_file.parent, dict):
            self.config["ILN"][self.active_file.parent["filepath"]] = self.active_file.parent["len_"]
        self.db.create_record(self.cards_seen+1, self.positives, seconds_spent)
        newfp = self.db.save_revision(self.active_file.data.iloc[:self.cards_seen+1, :])
        self.load_flashcards(self.db.files[newfp])
        self.update_backend_parameters()


    def change_revmode(self, force_which=None):
        if self.active_file.kind == self.db.KINDS.lng or self.is_saved:
            self.revmode = False
        elif force_which is None:
            self.revmode = not self.revmode
        else:
            self.revmode = force_which

    
    def update_backend_parameters(self):
        self.config.update({'onload_filepath': self.active_file.filepath})
        self.reset_flashcards_parameters()
        fcc_queue.put(f'{self.db.KFN[self.active_file.kind]} loaded: {self.active_file.basename}')


    def reset_flashcards_parameters(self):
        self.current_index = 0
        self.cards_seen = 0
        self.cards_seen_sides = list()
        self.add_default_side()
        self.side = self.get_default_side()
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.mistakes_list = list()
        self.is_saved = False
        self.total_words = self.active_file.data.shape[0]
        self.revision_summary = None
        self.auto_cfm_offset = 0
        self.change_revmode(self.active_file.kind in self.db.GRADED)
        

    def save_to_mistakes_list(self):   
        mistakes_list = self.db.save_mistakes(
            mistakes_list = self.mistakes_list, 
            offset = self.auto_cfm_offset
        )
        self.auto_cfm_offset = mistakes_list.shape[0]  
        self.load_ephemeral_file(mistakes_list)
        self.cards_seen = mistakes_list.shape[0]-1


    def load_ephemeral_file(self, data:pd.DataFrame):
        self.db.load_tempfile(
            data = data,
            kind = self.db.KINDS.eph,
            basename = f'{self.active_file.lng} Ephemeral',
            lng = self.active_file.lng,
            signature = f"{self.active_file.lng}_ephemeral",
            parent = {
                "filepath": self.active_file.filepath, 
                "len_": self.active_file.data.shape[0],
            },
        )
        fcc_queue.put("Created an Ephemeral set")
        self.update_backend_parameters()
        self.update_interface_parameters()


    def get_rating_message(self):
        return self.summary_gen.get_summary_text(
            self.positives, self.total_words, self.seconds_spent
        )


    def update_default_side(self):
        '''substitute add_default_side() via a first-class function'''
        default_side = self.config['card_default_side']
        if default_side.isnumeric():
            default_side = int(default_side)
            self.add_default_side =  lambda: self.cards_seen_sides.append(default_side)
        else:
            self.add_default_side = lambda: self.cards_seen_sides.append(randint(0,1))
    

    def get_default_side(self):
        return self.cards_seen_sides[self.current_index]


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
