import re
import logging
from datetime import datetime
from random import randint
import pandas as pd
from DBAC.api import DbOperator, FileDescriptor
from utils import *
from cfg import config
from data_types import HIDE_TIPS_POLICIES
from rev_summary import SummaryGenerator

log = logging.getLogger("BKD")


class MainWindowLogic:

    def __init__(self):
        self.config = config
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
        self.synopsis = None
        self.is_recorded = False
        self.db = DbOperator()
        self.summary_gen = SummaryGenerator()
        self.is_synopsis = False
        self.should_hide_tips = lambda: False
        self.tips_hide_re = re.compile(self.config["hide_tips"]["pattern"])
        self.allow_hide_tips = True
        self.mistakes_saved = False

    @property
    def is_revision(self):
        return self.db.active_file.kind == self.db.KINDS.rev

    @property
    def active_file(self):
        return self.db.active_file

    def check_is_initial_rev(self) -> bool:
        return (
            self.active_file.kind == self.db.KINDS.rev
            and self.db.get_sum_repeated(self.active_file.signature)
            < self.config["init_revs_cnt"]
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
            self.config["mst"]["unreviewed"] = max(
                self.config["mst"]["unreviewed"] - self.active_file.data.shape[0], 0
            )
        self.db.create_record(
            self.total_words, self.positives, seconds_spent, is_first=0
        )
        self.is_recorded = True
        if self.active_file.filepath in self.config["CRE"]["items"]:
            self._update_cre()
            fcc_queue.put_log(self._get_cre_stat())
            if not self.config["CRE"]["items"]:
                self._cre_finalize()

    def _update_cre(self):
        self.config["CRE"]["items"].remove(self.active_file.filepath)
        self.config["CRE"]["cards_seen"] += self.cards_seen
        self.config["CRE"]["time_spent"] += self.seconds_spent
        self.config["CRE"]["positives"] += self.positives

    def _cre_finalize(self):
        fcc_queue.put_notification("CRE finished - Congratulations!!!", lvl=LogLvl.important)
        self.config["CRE"]["prev"]["date"] = datetime.now().strftime(
            r"%Y-%m-%d %H:%M:%S"
        )
        self.config["CRE"]["prev"]["count"] = self.config["CRE"]["count"]
        self.config["CRE"]["prev"]["positives"] = self.config["CRE"]["positives"]
        self.config["CRE"]["prev"]["cards_seen"] = self.config["CRE"]["cards_seen"]
        self.config["CRE"]["prev"]["time_spent"] = self.config["CRE"]["time_spent"]
        self._flush_cre()

    def _get_cre_stat(self) -> str:
        try:
            accuracy = (
                self.config["CRE"]["positives"] / self.config["CRE"]["cards_seen"]
            )
            rev_done = self.config["CRE"]["count"] - len(self.config["CRE"]["items"])
            return "\n".join(
                [
                    "",
                    "    CRE Report",
                    f"Progress : {100*(self.config['CRE']['cards_seen'] / self.config['CRE']['cards_total']):.0f}%",
                    f"Revisions: {rev_done}/{self.config['CRE']['count']}",
                    f"Cards    : {self.config['CRE']['cards_seen']}/{self.config['CRE']['cards_total']}",
                    f"Timer    : {format_seconds_to(self.config['CRE']['time_spent'], 'hour', sep=':')}",
                    f"Accuracy : {100*accuracy:.0f}%",
                ]
            )
        except ZeroDivisionError as e:
            log.error(e, exc_info=True)
            return "CRE statistics are unavailable at the moment"

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

    def load_flashcards(self, fd: FileDescriptor, seed=None):
        try:
            self.db.load_dataset(fd, do_shuffle=True, seed=seed)
        except FileNotFoundError:
            fcc_queue.put_notification(f"File not found: {fd.filepath}", lvl=LogLvl.exc)

    def should_create_db_record(self):
        return (
            not self.is_recorded
            and self.total_words - self.current_index - 1 == 0
            and self.active_file.kind in self.db.GRADED
        )

    def handle_creating_revision(self, seconds_spent=0):
        if isinstance(self.active_file.parent, dict):
            self.config["ILN"][self.active_file.parent["filepath"]] = (
                self.active_file.parent["len_"]
            )
        self.active_file.signature = self.db.gen_signature(self.active_file.lng)
        self.active_file.kind = self.db.KINDS.rev
        newfp = self.db.save_revision(
            self.active_file.data.iloc[: self.cards_seen + 1, :]
        )
        self.db.create_record(
            self.cards_seen + 1, self.positives, seconds_spent, is_first=1
        )
        self.load_flashcards(self.db.files[newfp])
        self.update_backend_parameters()
        self.update_interface_parameters()

    def update_backend_parameters(self):
        self.config["onload_filepath"] = self.active_file.filepath
        self.is_initial_rev = self.check_is_initial_rev()
        self.is_recorded = False
        self.is_synopsis = False
        self.synopsis = None
        self.current_index = 0
        self.cards_seen = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.total_words = self.active_file.data.shape[0]
        self.mistakes_list = list()
        self.mistakes_saved = False
        self.cards_seen_sides = list()
        self.add_default_side()
        self.side = self.get_default_side()
        self.allow_hide_tips = True
        self.set_should_hide_tips()

    def set_should_hide_tips(self):
        nd = lambda: self.allow_hide_tips and not self.is_synopsis
        policies = set(
            self.config["hide_tips"]["policy"].get(
                self.active_file.kind, [HIDE_TIPS_POLICIES.never]
            )
        )
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
                        self.should_hide_tips = (
                            lambda: all(f() for f in conditions) and nd()
                        )
                    else:  # or
                        self.should_hide_tips = (
                            lambda: any(f() for f in conditions) and nd()
                        )
                else:
                    self.should_hide_tips = lambda: nd()
            else:
                self.should_hide_tips = lambda: False

    def save_current_mistakes(self):
        self.db.save_mistakes(mistakes_list=self.mistakes_list)
        self.mistakes_saved = True
        self.notify_on_mistakes()

    def notify_on_mistakes(self):
        if (
            self.config["popups"]["allowed"]["unreviewed_mistakes"]
            and self.config["mst"]["unreviewed"]
            / (self.config["mst"]["part_size"] * self.config["mst"]["part_cnt"])
            >= self.config["popups"]["triggers"]["unreviewed_mistakes_percent"]
        ):
            try:
                mistakes_fd = [
                    fd
                    for fd in self.db.files.values()
                    if fd.lng == self.active_file.lng and fd.kind == self.db.KINDS.mst
                ][0]
                unr_cnt = min(
                    self.config["mst"]["unreviewed"],
                    self.config["mst"]["part_size"] * self.config["mst"]["part_cnt"],
                )
                fcc_queue.put_notification(
                    f"There are {unr_cnt} unreviewed Mistakes!",
                    lvl=LogLvl.info,
                    func=lambda: self.initiate_flashcards(mistakes_fd),
                )
            except IndexError:
                log.debug("No matching Mistakes file found")

    def notify_on_outstanding_initial_revisions(self):
        if self.config["popups"]["allowed"]["initial_revs"]:
            outstanding_cnt = 0
            for rec in self._recoms:
                if rec["is_init"]:
                    outstanding_cnt += 1
            if outstanding_cnt > 0:
                fcc_queue.put_notification(
                    f"There are {outstanding_cnt} outstanding Initial Revisions",
                    lvl=LogLvl.info,
                    func=None if self.is_initial_rev else self.load_next_efc,
                )

    def init_eph_from_mistakes(self):
        mistakes_df = pd.DataFrame(
            data=self.mistakes_list,
            columns=self.active_file.data.columns,
        )
        if not self.active_file.tmp:
            self.file_monitor_del_path(self.active_file.filepath)
        self.db.load_tempfile(
            data=mistakes_df,
            kind=self.db.KINDS.eph,
            basename=f"{self.active_file.lng} Ephemeral",
            lng=self.active_file.lng,
            signature=f"{self.active_file.lng}_ephemeral",
            parent={
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
        """substitute add_default_side() via a first-class function"""
        default_side = self.config["card_default_side"]
        if default_side.isnumeric():
            default_side = int(default_side)
            self.add_default_side = lambda: self.cards_seen_sides.append(default_side)
        else:
            self.add_default_side = lambda: self.cards_seen_sides.append(randint(0, 1))

    def get_default_side(self) -> int:
        return self.cards_seen_sides[self.current_index]

    def get_current_card(self):
        return self.active_file.data.iloc[self.current_index, :]

    def notify_on_error(self, traceback, exc_value=None):
        log.error(traceback, exc_info=True, stacklevel=2)
        self.get_logs_sidewindow()

    def should_save_mistakes(self) -> bool:
        res = False
        if (
            self.mistakes_list
            and not self.mistakes_saved
            and (
                self.is_recorded
                or self.config["mst"]["opt"]["allow_save_mst_from_unfinished"]
            )
        ):
            if self.active_file.kind == self.db.KINDS.rev:
                if self.is_initial_rev:
                    if self.config["mst"]["opt"]["allow_save_mst_from_initial_rev"]:
                        res = True
                else:
                    if self.config["mst"]["opt"]["allow_save_mst_from_rev"]:
                        res = True
            elif self.active_file.kind == self.db.KINDS.mst:
                if self.config["mst"]["opt"]["allow_save_mst_from_mst"]:
                    res = True
            elif self.active_file.kind == self.db.KINDS.eph:
                if self.config["mst"]["opt"]["allow_save_mst_from_eph"]:
                    res = True
        return res

    # TODO add snapshot params for SOD
    def create_session_snapshot(self):
        prev_tab = self.active_tab_ident
        self._deactivate_tab()
        _fcc_log = self.tabs["fcc"]["console_log"]
        if len(_fcc_log) > 0 and _fcc_log[-1] == self.tabs["fcc"]["console_prompt"]:
            _fcc_log.pop()
        for m in fcc_queue.get_logs():
            _fcc_log.append(f"[{m.timestamp.strftime('%H:%M:%S')}] {m.message}")
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
            "mistakes_saved": self.mistakes_saved,
            "cards_seen_sides": self.cards_seen_sides,
            "side": self.side,
            "cur_load_index": self.cur_load_index,
            "cur_efc_index": self.cur_efc_index,
            "is_recorded": self.is_recorded,
            "revmode": self.revmode,
            "is_synopsis": self.is_synopsis,
            "allow_hide_tips": self.allow_hide_tips,
            "synopsis": self.synopsis,
            "efc_last_calc_time": self._efc_last_calc_time,
            "efc_db_is_current": self._db_load_time_efc == self.db.last_load,
            "efc_recommendations": self._recoms,
            "fcc_cmds_cursor": self.tabs["fcc"]["cmds_cursor"],
            "fcc_console_log": _fcc_log,
            "fcc_cmds_log": self.tabs["fcc"]["cmds_log"],
            "is_initial_rev": self.is_initial_rev
        }
        self.activate_tab(prev_tab)
        self.config.cache["snapshot"]["session"] = snapshot
        log.debug(f"Created a session snapshot")

    def _apply_session_snapshot_backend(self):
        metadata = self.config.cache["snapshot"]["session"]
        self.current_index = metadata["current_index"]
        self.seconds_spent = metadata["seconds_spent"]
        self.config["pd_random_seed"] = metadata["pd_random_seed"]
        self.is_recorded = metadata["is_recorded"]
        self.revmode = metadata["revmode"]
        self.is_synopsis = metadata["is_synopsis"]
        self.allow_hide_tips = metadata["allow_hide_tips"]
        self.synopsis = metadata["synopsis"]
        self.cards_seen = metadata["cards_seen"]
        self.words_back = metadata["words_back"]
        self.positives = metadata["positives"]
        self.negatives = metadata["negatives"]
        self.total_words = metadata["total_words"]
        self.is_initial_rev = metadata["is_initial_rev"]
        self.mistakes_list = metadata["mistakes_list"]
        self.mistakes_saved = metadata["mistakes_saved"]
        self.cards_seen_sides = metadata["cards_seen_sides"]
        self.side = metadata["side"]
        self.cur_load_index = metadata["cur_load_index"]
        self.cur_efc_index = metadata["cur_efc_index"]
        self._efc_last_calc_time = metadata["efc_last_calc_time"]
        if metadata["efc_db_is_current"]:
            self._db_load_time_efc = self.db.last_load
        self._recoms = metadata["efc_recommendations"]
        self._deactivate_tab()
        self.tabs["fcc"]["cmds_log"] = metadata["fcc_cmds_log"][
            -self.config["cache_history_size"] :
        ]
        self.tabs["fcc"]["console_log"] = metadata["fcc_console_log"][
            -self.config["cache_history_size"] :
        ]
        self.tabs["fcc"]["cmds_cursor"] = metadata["fcc_cmds_cursor"]
        self.activate_tab("fcc")
        self.set_should_hide_tips()
