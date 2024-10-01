import re
import logging
from datetime import datetime
from random import randint
from DBAC.api import DbOperator, FileDescriptor
from utils import *
from data_types import HIDE_TIPS_POLICIES
from rev_summary import SummaryGenerator

log = logging.getLogger("BKD")


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
        self.is_afterface = False
        self.is_revision_summary = False
        self.should_hide_tips = lambda: False
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
            self.db.get_sum_repeated(self.active_file.signature) - int(self.is_recorded) < self.config["init_revs_cnt"]
        )


    def result_positive(self):
        if self.current_index < self.total_words and self.words_back == 0:
            self.positives += 1
    

    def result_negative(self):
        if self.current_index < self.total_words and self.words_back == 0:
            self.negatives += 1
            self.append_current_card_to_mistakes_list()
            

    def append_current_card_to_mistakes_list(self):
        self.mistakes_list.append(self.get_current_card().to_list())
        

    def goto_next_card(self):
        if self.total_words > self.current_index:
            self.current_index += 1
            if self.current_index > self.cards_seen:
                self.cards_seen = self.current_index
                self.add_default_side()
            if self.words_back > 0:
                self.words_back -= 1
            self.side = self.get_default_side()


    def goto_prev_card(self):
        if self.current_index >= 1:
            self.current_index -= 1
            self.words_back += 1    
            self.side = self.get_default_side()


    def record_revision_to_db(self, seconds_spent=0):
        if self.active_file.kind == self.db.KINDS.mst:
            self.config["cache"]["unreviewed_mistakes"] = 0
        self.db.create_record(self.total_words, self.positives, seconds_spent)
        self.is_recorded = True


    def handle_comprehensive_revision(self, fd: FileDescriptor):
        # It is assumed that the corresponding revision was saved
        self._update_cre(fd)
        fcc_queue.put(self._get_cre_stat())
        if self.config["CRE"]["items"]:
            if self.config["CRE"]["auto_save_mistakes"] and self.mistakes_list:
                self.db.save_mistakes(mistakes_list=self.mistakes_list)
                self.notify_on_mistakes()
                self.init_eph_from_mistakes()
            if self.config["CRE"]["auto_next"]:
                self.activate_tab("fcc")
                self.fcc_inst.execute_command(["cre"])
        else:
            fcc_queue.put("CRE finished - Congratulations!!!\n")
            self._flush_cre()
            self.config["CRE"]["last_completed"] = datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")
                
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


    def reverse_side(self):
        self.side = 1 - self.side
        
     
    def delete_current_card(self):
        self.db.delete_card(self.current_index)
        self.total_words = self.active_file.data.shape[0]
        self.side = self.get_default_side()
        

    def load_flashcards(self, fd:FileDescriptor, seed=None):
        try:
            self.db.load_dataset(fd, do_shuffle=True, seed=seed)
            fcc_queue.put(f'{self.db.KFN[self.active_file.kind]} loaded: {self.active_file.basename}')
        except FileNotFoundError:
            fcc_queue.put('File Not Found.')


    def should_create_db_record(self):
        return (
            not self.is_recorded
            and self.total_words - self.current_index - 1 == 0 
            and self.active_file.kind in self.db.GRADED 
        )


    def handle_creating_revision(self, seconds_spent=0):
        if isinstance(self.active_file.parent, dict):
            self.config["ILN"][self.active_file.parent["filepath"]] = self.active_file.parent["len_"]
        self.active_file.signature = self.db.gen_signature(self.active_file.lng)
        self.active_file.kind = self.db.KINDS.rev
        newfp = self.db.save_revision(self.active_file.data.iloc[:self.cards_seen+1, :])
        self.db.create_record(self.cards_seen+1, self.positives, seconds_spent)
        self.load_flashcards(self.db.files[newfp])
        self.update_backend_parameters()

    
    def update_backend_parameters(self):
        self.config["onload_filepath"] = self.active_file.filepath
        self.reset_flashcards_parameters()


    def reset_flashcards_parameters(self):
        self.is_recorded = False
        self.is_afterface = False
        self.is_revision_summary = False
        self.revision_summary = None
        self.current_index = 0
        self.cards_seen = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.total_words = self.active_file.data.shape[0]
        self.mistakes_list = list()
        self.cards_seen_sides = list()
        self.add_default_side()
        self.side = self.get_default_side()
        self.set_should_hide_tips()


    def set_should_hide_tips(self):
        nd = lambda: not self.is_afterface and not self.is_revision_summary
        policies = set(self.config["hide_tips"]["policy"].get(self.active_file.kind, [HIDE_TIPS_POLICIES.never]))
        # 0 Level override
        if HIDE_TIPS_POLICIES.never in policies:
            self.should_hide_tips = lambda: False
        elif HIDE_TIPS_POLICIES.always in policies:
            self.should_hide_tips = lambda: nd()
        else:
            # 1 Level state
            state_matched = True
            if policies.intersection(HIDE_TIPS_POLICIES.get_states()):
                if HIDE_TIPS_POLICIES.reg_rev in policies:
                    state_matched = not self.is_initial_rev
            # 2 Level flux
            if state_matched:
                if policies.intersection(HIDE_TIPS_POLICIES.get_flux()):
                    conditions = set()
                    if HIDE_TIPS_POLICIES.new_card in policies:
                        conditions.add(lambda: self.revmode)
                    if HIDE_TIPS_POLICIES.foreign_side in policies:
                        conditions.add(lambda: self.side == 0)
                    # Logical connector
                    if self.config["hide_tips"]["connector"] == "and":
                        self.should_hide_tips = lambda: all(f() for f in conditions) and nd()
                    else:  # or
                        self.should_hide_tips = lambda: any(f() for f in conditions) and nd()
                else:
                    self.should_hide_tips = lambda: nd()
            else:
                self.should_hide_tips = lambda: False


    def save_current_mistakes(self):
        self.db.save_mistakes(mistakes_list=self.mistakes_list)
        self.notify_on_mistakes()

    def notify_on_mistakes(self):
        if self.config["cache"]["unreviewed_mistakes"] / self.config["mistakes_buffer"] >= self.config["POPUPS"]["triggers"]["unreviewed_mistakes_percent"]:
            try:
                mistakes_fd = [
                    fd for fd 
                    in self.db.files.values() 
                    if fd.lng == self.active_file.lng
                    and fd.kind == self.db.KINDS.mst
                ][0]
                fcc_queue.put(
                    f"There are {self.config['cache']['unreviewed_mistakes']} unreviewed Mistakes!",
                    importance=20,
                    func=lambda: self.initiate_flashcards(mistakes_fd),
                    persist=True,
                )
            except IndexError:
                log.debug("No matching Mistakes file found")
        
    def init_eph_from_mistakes(self):
        mistakes_df = pd.DataFrame(
            data=self.mistakes_list, 
            columns=self.active_file.data.columns,
        )
        if not self.active_file.tmp:
            self.file_monitor_del_path(self.active_file.filepath)
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
        self.load_again_click()


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
    

    def get_default_side(self) -> int:
        return self.cards_seen_sides[self.current_index]


    def get_current_card(self):
        return self.active_file.data.iloc[self.current_index, :]


    def notify_on_error(self, traceback, exc_value=None):
        log.error(traceback, exc_info=True, stacklevel=2)

        if exc_value:  # is an error
            err_msg = f"{str(exc_value)}. See log file for more details."
        else:
            err_msg = traceback

        err_msg += '\n' + self.CONSOLE_PROMPT
        fcc_queue.put(err_msg, importance=50)

        if self.side_window_id == 'fcc':
            self.del_side_window()
        self.get_fcc_sidewindow()


    # TODO add snapshot params for SOD
    def create_session_snapshot(self):
        prev_tab = self.active_tab_ident
        self._deactivate_tab()
        snapshot = {
            "timestamp": datetime.now().strftime(self.db.TSFORMAT),
            "current_index": self.current_index,
            "seconds_spent": self.seconds_spent,
            "pd_random_seed": self.config["pd_random_seed"],
            "cards_seen": self.cards_seen,
            "words_back": self.words_back,
            "positives": self.positives,
            "negatives": self.negatives,
            "total_words": self.total_words,
            "mistakes_list": self.mistakes_list,
            "cards_seen_sides": self.cards_seen_sides,
            "side": self.side,
            "cur_load_index": self.cur_load_index,
            "cur_efc_index": self.cur_efc_index,
            "is_recorded": self.is_recorded,
            "revmode": self.revmode,
            "is_afterface": self.is_afterface,
            "is_revision_summary": self.is_revision_summary,
            "revision_summary": self.revision_summary,
            "fcc_cmds_cursor": self.tabs["fcc"]["cmds_cursor"],
            "fcc_console_prompt": self.tabs["fcc"]["console_prompt"],
            "fcc_console_log": self.tabs["fcc"]["console_log"],
            "fcc_cmds_log": self.tabs["fcc"]["cmds_log"],
        }
        self.activate_tab(prev_tab)
        self.config["cache"]["snapshot"]["session"] = snapshot
        log.debug(f"Created a session snapshot")


    def _apply_session_snapshot_backend(self):
        metadata = self.config["cache"]["snapshot"]["session"]
        self.current_index = metadata["current_index"]
        self.seconds_spent = metadata["seconds_spent"]
        self.config["pd_random_seed"] = metadata["pd_random_seed"]
        self.is_recorded = metadata["is_recorded"]
        self.revmode = metadata["revmode"]
        self.is_afterface = metadata["is_afterface"]
        self.is_revision_summary = metadata["is_revision_summary"]
        self.revision_summary = metadata["revision_summary"]
        self.cards_seen = metadata["cards_seen"]
        self.words_back = metadata["words_back"]
        self.positives = metadata["positives"]
        self.negatives = metadata["negatives"]
        self.total_words = metadata["total_words"]
        self.mistakes_list = metadata["mistakes_list"]
        self.cards_seen_sides = metadata["cards_seen_sides"]
        self.side = metadata["side"]
        self.cur_load_index = metadata["cur_load_index"]
        self.cur_efc_index = metadata["cur_efc_index"]
        self._deactivate_tab()
        self.tabs["fcc"]["cmds_log"] = metadata["fcc_cmds_log"][-self.config["cache_history_size"]:]
        self.tabs["fcc"]["console_log"] = metadata["fcc_console_log"][-self.config["cache_history_size"]:]
        self.tabs["fcc"]["cmds_cursor"] = metadata["fcc_cmds_cursor"]
        self.tabs["fcc"]["console_prompt"] = metadata["fcc_console_prompt"]
        self.activate_tab("fcc")
        self.set_should_hide_tips()
