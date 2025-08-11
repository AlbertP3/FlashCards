import re
import logging
from datetime import datetime
from random import randint
from typing import Optional
import pandas as pd
from DBAC import db_conn, FileDescriptor
from utils import fcc_queue, LogLvl, format_seconds_to
from logtools import audit_log
from cfg import config
from data_types import HIDE_TIPS_POLICIES
from rev_summary import SummaryGenerator

log = logging.getLogger("BKD")


class MainWindowLogic:

    def __init__(self):
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
        self.summary_gen = SummaryGenerator()
        self.is_synopsis = False
        self.should_hide_tips = lambda: False
        self.tips_hide_re = re.compile(config["hide_tips"]["pattern"])
        self.allow_hide_tips = True
        self.mistakes_saved = False
        self.is_blurred = False

    @property
    def is_revision(self):
        return db_conn.active_file.kind == db_conn.KINDS.rev

    @property
    def active_file(self):
        return db_conn.active_file

    def check_is_initial_rev(self) -> bool:
        return (
            self.active_file.kind == db_conn.KINDS.rev
            and db_conn.get_sum_repeated(self.active_file.signature)
            < config["init_revs_cnt"]
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
        if self.active_file.kind == db_conn.KINDS.mst:
            config["mst"]["unreviewed"] = max(
                config["mst"]["unreviewed"] - self.active_file.data.shape[0], 0
            )
        db_conn.create_record(
            self.total_words, self.positives, seconds_spent, is_first=0
        )
        self.is_recorded = True
        self.skip_efc_reload_regular()
        if self.active_file.filepath in config["CRE"]["items"]:
            self._update_cre()
            fcc_queue.put_log(self._get_cre_stat())
            if not config["CRE"]["items"]:
                self._cre_finalize()

    def skip_efc_reload_regular(self):
        self.efc._db_load_time_efc = db_conn.last_update
        for i, v in enumerate(self.efc._recoms):
            if v["fp"] == self.active_file.filepath:
                del self.efc._recoms[i]
                self.efc.recoms_qlist.takeItem(i)
                self.efc.files_count -= 1
                break

    def _update_cre(self):
        config["CRE"]["items"].remove(self.active_file.filepath)
        config["CRE"]["cards_seen"] += self.cards_seen
        config["CRE"]["time_spent"] += self.seconds_spent
        config["CRE"]["positives"] += self.positives

    def _cre_finalize(self):
        fcc_queue.put_notification(
            "CRE finished - Congratulations!!!", lvl=LogLvl.important
        )
        config["CRE"]["prev"]["date"] = datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")
        config["CRE"]["prev"]["count"] = config["CRE"]["count"]
        config["CRE"]["prev"]["positives"] = config["CRE"]["positives"]
        config["CRE"]["prev"]["cards_seen"] = config["CRE"]["cards_seen"]
        config["CRE"]["prev"]["time_spent"] = config["CRE"]["time_spent"]
        self._flush_cre()

    def _get_cre_stat(self) -> str:
        try:
            accuracy = config["CRE"]["positives"] / config["CRE"]["cards_seen"]
            rev_done = config["CRE"]["count"] - len(config["CRE"]["items"])
            return "\n".join(
                [
                    "",
                    "    CRE Report",
                    f"Progress : {100*(config['CRE']['cards_seen'] / config['CRE']['cards_total']):.0f}%",
                    f"Revisions: {rev_done}/{config['CRE']['count']}",
                    f"Cards    : {config['CRE']['cards_seen']}/{config['CRE']['cards_total']}",
                    f"Timer    : {format_seconds_to(config['CRE']['time_spent'], 'hour', sep=':')}",
                    f"Accuracy : {100*accuracy:.0f}%",
                ]
            )
        except ZeroDivisionError as e:
            log.error(e, exc_info=True)
            return "CRE statistics are unavailable at the moment"

    def _flush_cre(self):
        config["CRE"]["items"].clear()
        config["CRE"]["count"] = 0
        config["CRE"]["cards_seen"] = 0
        config["CRE"]["cards_total"] = 0
        config["CRE"]["time_spent"] = 0
        config["CRE"]["positives"] = 0

    def _reverse_side(self):
        self.side = 1 - self.side

    def _delete_current_card(self):
        oid = db_conn.get_oid_by_index(self.current_index)
        db_conn.delete_card(self.current_index)
        self.total_words = self.active_file.data.shape[0]
        if self.current_index > 0:
            self.current_index -= 1
        self.side = self.get_default_side()
        # If applicable, sync SFE with active tmp file
        if (
            self.active_file.tmp
            and self.sfe.model.fh.fd.tmp
            and self.active_file.signature == self.sfe.model.fh.fd.signature
        ):
            self.sfe.model.del_rows([oid])

    def load_flashcards(self, fd: FileDescriptor, seed: Optional[int] = None):
        try:
            db_conn.afops(fd, shuffle=True, seed=seed)
        except FileNotFoundError:
            fcc_queue.put_notification(f"File not found: {fd.filepath}", lvl=LogLvl.exc)

    def should_create_db_record(self):
        return (
            not self.is_recorded
            and self.active_file.valid
            and self.total_words - self.current_index - 1 == 0
            and self.active_file.kind in db_conn.GRADED
        )

    def handle_creating_revision(self, seconds_spent=0):
        if isinstance(self.active_file.parent, dict):
            config["ILN"][self.active_file.parent["filepath"]] = (
                self.active_file.parent["len_"]
            )
            self.sfe.check_update_iln()
        self.active_file.signature = db_conn.gen_signature(self.active_file)
        self.active_file.kind = db_conn.KINDS.rev
        newfp = db_conn.create_revision_file(
            self.active_file.data.iloc[: self.cards_seen + 1, :]
        )
        self.update_files_lists()
        db_conn.create_record(
            self.cards_seen + 1, self.positives, seconds_spent, is_first=1
        )
        self.load_flashcards(db_conn.files[newfp])
        self.update_backend_parameters()
        self.update_interface_parameters()
        self.skip_efc_reload_initial()

    def skip_efc_reload_initial(self):
        self.efc._db_load_time_efc = db_conn.last_update
        self.efc._recoms.append(
            {
                "fp": self.active_file.filepath,
                "disp": f"{config['icons']['initial']} {self.active_file.signature}",
                "score": 0,
                "is_init": True,
            }
        )
        self.efc._recoms.sort(
            key=lambda x: (
                x[config["efc"]["sort"]["key_1"]],
                x[config["efc"]["sort"]["key_2"]],
            )
        )
        self.efc.is_view_outdated = True

    def update_backend_parameters(self):
        config["onload_filepath"] = self.active_file.filepath
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
            config["hide_tips"]["policy"].get(
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
                    if config["hide_tips"]["connector"] == "and":
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
        db_conn.create_mistakes_file(mistakes_list=[i[:2] for i in self.mistakes_list])
        self.update_files_lists()
        self.mistakes_saved = True
        self.notify_on_mistakes()

    def notify_on_mistakes(self):
        if (
            config["popups"]["allowed"]["unreviewed_mistakes"]
            and config["mst"]["unreviewed"]
            / (config["mst"]["part_size"] * config["mst"]["part_cnt"])
            >= config["popups"]["triggers"]["unreviewed_mistakes_percent"]
        ):
            try:
                mistakes_fd = [
                    fd
                    for fd in db_conn.files.values()
                    if fd.lng == self.active_file.lng and fd.kind == db_conn.KINDS.mst
                ][0]
                unr_cnt = min(
                    config["mst"]["unreviewed"],
                    config["mst"]["part_size"] * config["mst"]["part_cnt"],
                )
                fcc_queue.put_notification(
                    f"There are {unr_cnt} unreviewed Mistakes!",
                    lvl=LogLvl.info,
                    func=lambda: self.initiate_flashcards(mistakes_fd),
                )
            except IndexError:
                log.debug("No matching Mistakes file found")

    def notify_on_outstanding_initial_revisions(self):
        if config["popups"]["allowed"]["initial_revs"]:
            outstanding_cnt = 0
            for rec in self.efc._recoms:
                if rec["is_init"]:
                    outstanding_cnt += 1
            if outstanding_cnt > 0:
                fcc_queue.put_notification(
                    f"There are {outstanding_cnt} outstanding Initial Revisions",
                    lvl=LogLvl.info,
                    func=None if self.is_initial_rev else self.efc.load_next_efc,
                )

    def init_eph_from_mistakes(self):
        mistakes_df = pd.DataFrame(
            data=[i[:2] for i in self.mistakes_list],
            columns=self.active_file.headers,
        )
        if not self.active_file.tmp:
            self.file_monitor_del_path(self.active_file.filepath)
        db_conn.activate_tmp_file(
            data=mistakes_df,
            kind=db_conn.KINDS.eph,
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

    def _update_default_side(self):
        """substitute add_default_side() via a first-class function"""
        default_side = config["card_default_side"]
        if default_side.isnumeric():
            default_side = int(default_side)
            self.add_default_side = lambda: self.cards_seen_sides.append(default_side)
        else:
            self.add_default_side = lambda: self.cards_seen_sides.append(randint(0, 1))

    def get_default_side(self) -> int:
        return self.cards_seen_sides[self.current_index]

    def get_current_card(self) -> pd.Series:
        return self.active_file.data.iloc[self.current_index, :]

    def notify_on_error(self, traceback, exc_value=None):
        log.error(traceback, exc_info=True, stacklevel=2)
        self.log.open(scroll_end=True)

    def should_save_mistakes(self) -> bool:
        res = False
        if (
            self.mistakes_list
            and not self.mistakes_saved
            and (
                self.is_recorded
                or config["mst"]["opt"]["allow_save_mst_from_unfinished"]
            )
        ):
            if self.active_file.kind == db_conn.KINDS.rev:
                if self.is_initial_rev:
                    if config["mst"]["opt"]["allow_save_mst_from_initial_rev"]:
                        res = True
                else:
                    if config["mst"]["opt"]["allow_save_mst_from_rev"]:
                        res = True
            elif self.active_file.kind == db_conn.KINDS.mst:
                if config["mst"]["opt"]["allow_save_mst_from_mst"]:
                    res = True
            elif self.active_file.kind == db_conn.KINDS.eph:
                if config["mst"]["opt"]["allow_save_mst_from_eph"]:
                    res = True
        return res

    def update_files_lists(self):
        db_conn.update_fds()
        self.ldt.is_view_outdated = True
        self.efc.is_view_outdated = True

    def sfe_apply_add(self, row: list[str]):
        new_idx = len(self.active_file.data)
        self.active_file.data.loc[new_idx] = [*row, new_idx]
        self.total_words += 1
        self.update_words_button()
        self.display_text(self.get_current_card().iloc[self.side])
        audit_log(
            op="ADD",
            data=row,
            filepath=self.active_file.filepath,
            author="FCS",
            row=new_idx,
            status="ACTIVE_ONLY",
        )

    def sfe_apply_edit(self, oid: int, val: list[str]):
        idx = db_conn.get_index_by_oid(oid)
        if idx <= self.current_index:
            try:
                mst_idx = self.find_in_mistakes_list(oid)
                self.mistakes_list[mst_idx] = [*val, oid]
            except IndexError:
                pass
        self.active_file.data.iloc[idx] = [*val, oid]
        self.display_text(self.get_current_card().iloc[self.side])
        audit_log(
            op="UPDATE",
            data=val,
            filepath=self.active_file.filepath,
            author="FCS",
            row=idx,
            status="ACTIVE_ONLY",
        )

    def sfe_apply_delete(self, oids: list[int]):
        for oid in oids:
            idx = db_conn.get_index_by_oid(oid)
            if 0 < idx <= self.current_index:
                self.current_index -= 1
                try:
                    mst_idx = self.find_in_mistakes_list(oid)
                    self.mistakes_list.pop(mst_idx)
                except IndexError:
                    pass
            db_conn.delete_card(idx)
            self.total_words -= 1
        self.update_words_button()
        self.display_text(self.get_current_card().iloc[self.side])

    def find_in_mistakes_list(self, idx: int) -> int:
        for i, v in enumerate(self.mistakes_list):
            if v[2] == idx:
                return i
        else:
            raise IndexError

    def create_session_snapshot(self):
        _fcc_log = self.fcc.console_log
        if len(_fcc_log) > 0 and _fcc_log[-1] == self.fcc.console_prompt:
            _fcc_log.pop()
        for m in fcc_queue.get_logs():
            _fcc_log.append(f"[{m.timestamp.strftime('%H:%M:%S')}] {m.message}")
        snapshot = {
            "timestamp": datetime.now().strftime(db_conn.TSFORMAT),
            "current_index": self.current_index,
            "seconds_spent": self.seconds_spent,
            "pd_random_seed": config["pd_random_seed"],
            "cards_seen": self.cards_seen,
            "words_back": self.words_back,
            "positives": self.positives,
            "negatives": self.negatives,
            "mistakes_list": self.mistakes_list,
            "mistakes_saved": self.mistakes_saved,
            "cards_seen_sides": self.cards_seen_sides,
            "side": self.side,
            "is_recorded": self.is_recorded,
            "revmode": self.revmode,
            "is_synopsis": self.is_synopsis,
            "allow_hide_tips": self.allow_hide_tips,
            "synopsis": self.synopsis,
            "fcc_cmd_cursor": self.fcc.cmd_cursor,
            "fcc_console_log": _fcc_log,
            "fcc_cmd_log": self.fcc.cmd_log,
            "is_initial_rev": self.is_initial_rev,
            "is_blurred": self.is_blurred,
        }
        config.cache["snapshot"]["session"] = snapshot
        log.debug(f"Created a session snapshot")

    def _apply_session_snapshot_backend(self):
        metadata = config.cache["snapshot"]["session"]
        self.current_index = metadata["current_index"]
        self.seconds_spent = metadata["seconds_spent"]
        config["pd_random_seed"] = metadata["pd_random_seed"]
        self.is_recorded = metadata["is_recorded"]
        self.revmode = metadata["revmode"]
        self.is_synopsis = metadata["is_synopsis"]
        self.allow_hide_tips = metadata["allow_hide_tips"]
        self.synopsis = metadata["synopsis"]
        self.cards_seen = metadata["cards_seen"]
        self.words_back = metadata["words_back"]
        self.positives = metadata["positives"]
        self.negatives = metadata["negatives"]
        self.is_initial_rev = metadata["is_initial_rev"]
        self.is_blurred = metadata["is_blurred"]
        self.mistakes_list = metadata["mistakes_list"]
        self.mistakes_saved = metadata["mistakes_saved"]
        self.cards_seen_sides = metadata["cards_seen_sides"]
        self.side = metadata["side"]
        self.fcc.cmd_log = metadata["fcc_cmd_log"][-config["cache_history_size"] :]
        self.fcc.console_log = metadata["fcc_console_log"][
            -config["cache_history_size"] :
        ]
        self.fcc.cmds_cursor = metadata["fcc_cmd_cursor"]
        self.total_words = self.active_file.data.shape[0]
        self.set_should_hide_tips()

    def modify_card_result(self):
        if self.words_back == 0:
            fcc_queue.put_notification("Card not yet checked", lvl=LogLvl.important)
        else:
            try:
                mst_idx = self.find_in_mistakes_list(
                    db_conn.get_oid_by_index(self.current_index)
                )
                self.mistakes_list.pop(mst_idx)
                self.negatives -= 1
                self.positives += 1
                fcc_queue.put_notification(
                    "Score modified to positive", lvl=LogLvl.important
                )
            except IndexError:
                self.append_current_card_to_mistakes_list()
                self.positives -= 1
                self.negatives += 1
                fcc_queue.put_notification(
                    "Score modified to negative", lvl=LogLvl.important
                )
            self.update_score_button()
