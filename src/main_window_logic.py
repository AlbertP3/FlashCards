import re
import logging
from datetime import datetime
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
        self.is_recorded = False
        self.db = DbOperator()
        self.summary_gen = SummaryGenerator()
        self.auto_cfm_offset = 0
        self.is_afterface = False
        self.is_revision_summary = False
        self.allow_hiding_tips = False
        self.tips_hide_re = re.compile(self.config["hide_tips"]["pattern"])


    @property
    def is_revision(self):
        return self.db.active_file.kind == self.db.KINDS.rev
    
    @property
    def active_file(self):
        return self.db.active_file
    
    @property
    def is_initial_rev(self) -> bool:
        return (
            self.active_file.kind == self.db.KINDS.rev and 
            self.db.get_sum_repeated(self.active_file.signature) - int(self.is_recorded) <= self.config["init_revs_cnt"]
        )


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
        self.is_recorded = True


    def handle_comprehensive_revision(self, fd: FileDescriptor):
        # It is assumed that the corresponding revision was saved
        self._update_cre(fd)
        fcc_queue.put(self._get_cre_stat())
        if self.config["CRE"]["items"]:
            if self.config["CRE"]["auto_save_mistakes"] and self.mistakes_list:
                self.db.save_mistakes(
                    mistakes_list = self.mistakes_list, 
                    offset = self.auto_cfm_offset
                )
                self.init_eph_from_mistakes()
            if self.config["CRE"]["auto_next"]:
                self.activate_tab("fcc")
                self.fcc_inst.execute_command(["cre"])
        else:
            fcc_queue.put("CRE finished - Congratulations!!!\n")
            self._flush_cre()
            self.config["CRE"]["last_completed"] = datetime.now().strftime(f"%Y-%m-%d %H:%M:%S")
                
    def _update_cre(self, fd: FileDescriptor):
        upd = self.db.get_cre_data(fd.signature)
        self.config["CRE"]["items"].remove(fd.filepath)
        self.config["CRE"]["cards_seen"] += upd["cards_seen"]
        self.config["CRE"]["time_spent"] += upd["time_spent"]
        self.config["CRE"]["positives"] += upd["positives"]


    def _get_cre_stat(self) -> str:
        accuracy = self.config['CRE']['positives'] / self.config['CRE']['cards_seen']
        rev_done = self.config['CRE']['count'] - len(self.config['CRE']['items'])
        return "\n".join([
            "",
            f"Progress : {100*(self.config['CRE']['cards_seen'] / self.config['CRE']['cards_total']):.0f}%",
            f"Revisions: {rev_done}/{self.config['CRE']['count']}",
            f"Cards    : {self.config['CRE']['cards_seen']}/{self.config['CRE']['cards_total']}",
            f"Timer    : {format_seconds_to(self.config['CRE']['time_spent'], 'hour', sep=':')}",
            f"Accuracy : {100*accuracy:.0f}%",
            "",
        ])


    def _flush_cre(self):
        self.config["CRE"]["items"].clear()
        self.config["CRE"]["count"] = 0
        self.config["CRE"]["cards_seen"] = 0
        self.config["CRE"]["cards_total"] = 0
        self.config["CRE"]["time_spent"] = 0
        self.config["CRE"]["positives"] = 0


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
            not self.is_recorded
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
        self.is_recorded = False
        self.total_words = self.active_file.data.shape[0]
        self.revision_summary = None
        self.auto_cfm_offset = 0
        self.set_allow_hiding_tips()


    def set_allow_hiding_tips(self):
        if self.config["hide_tips"]["policy"] == "always":
            self.allow_hiding_tips = True
        elif self.config["hide_tips"]["policy"] == "never":
            self.allow_hiding_tips = False
        elif self.config["hide_tips"]["policy"] == "standard-rev-only":
            self.allow_hiding_tips = self.is_revision and not self.is_initial_rev
        else:
            fcc_queue.put(f"Unknown hide_tips policy: {self.config['hide_tips']['policy']}")


    def save_current_mistakes(self):
        self.db.save_mistakes(
            mistakes_list = self.mistakes_list, 
            offset = self.auto_cfm_offset
        )
        
    def init_eph_from_mistakes(self):
        mistakes_df = pd.DataFrame(
            data=self.mistakes_list, 
            columns=self.active_file.data.columns,
        )
        self.db.load_tempfile(
            data = mistakes_df,
            kind = self.db.KINDS.eph,
            basename = f'{self.active_file.lng} Ephemeral',
            lng = self.active_file.lng,
            signature = f"{self.active_file.lng}_ephemeral",
            parent = {
                "filepath": self.active_file.filepath, 
                "len_": self.active_file.data.shape[0],
            },
        )
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

        err_msg += '\n' + self.CONSOLE_PROMPT
        fcc_queue.put(err_msg)

        if self.side_window_id != 'fcc':
            self.get_fcc_sidewindow()
