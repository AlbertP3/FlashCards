import joblib  # type: ignore
import os
from time import time, perf_counter
from random import choice
from datetime import datetime
import logging
from PyQt5.QtWidgets import QGridLayout, QListWidget, QWidget
from random import shuffle
import statistics
import numpy as np
from math import exp
from utils import fcc_queue, LogLvl, format_seconds_to
from cfg import config
from widgets import get_scrollbar, get_button
from tabs.base import BaseTab
from DBAC import db_conn

log = logging.getLogger("EFC")


class StandardModel:
    """
    Based on Ebbinghaus Forgetting Curve
    Estimates the percentage of words in-memory
    """

    def __init__(self):
        self.name = "CST"
        self.mtime = 0
        self.lng_cols = tuple()

    def predict(
        self,
        record: list[list],
        lng=None,
    ) -> list[list]:
        preds = list()
        for r in record:
            (
                total,
                prev_wpm,
                ts_creation,
                ts_last_rev,
                repeated_times,
                prev_score,
                *_,
            ) = r
            x1, x2, x3, x4 = 2.039, -4.566, -12.495, -0.001
            s = (repeated_times**x1 + 0.01 * prev_score * x2) - (x3 * exp(total * x4))
            preds.append([100 * exp(-ts_last_rev / (24 * s))])
        return preds


class EFCTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.id = "efc"
        self.mw = mw
        self.efc_model = StandardModel()
        self.load_pickled_model()
        self._efc_last_calc_time = 0
        self._db_load_time_efc = 0
        self.files_count = 0
        self._recoms: list[dict] = list()  # {fp, disp, score, is_init}
        self.mw.tab_names[self.id] = "EFC"
        self.cur_efc_index = 0
        self.build()
        self.show_recommendations()
        self.mw.add_tab(self._tab, self.id)

    def init_cross_shortcuts(self):
        super().init_cross_shortcuts()
        self.mw.add_ks(config["kbsc"]["run_command"], self.load_selected_efc, self)
        self.mw.add_ks(
            config["kbsc"]["negative"], lambda: self.nagivate_efc_list(1), self
        )
        self.mw.add_ks(
            config["kbsc"]["reverse"], lambda: self.nagivate_efc_list(-1), self
        )
        self.mw.add_ks(config["kbsc"]["next_efc"], self.load_next_efc, self.mw)

    def open(self):
        self.mw.switch_tab(self.id)
        if not self.cache_valid:
            self.recoms_qlist.clear()
            self.show_recommendations()

    def show_recommendations(self):
        for r in self.get_recommendations():
            self.recoms_qlist.addItem(r["disp"])
        self.files_count = self.recoms_qlist.count()
        if self.files_count:
            self.cur_efc_index = min(self.files_count - 1, self.cur_efc_index)
            self.recoms_qlist.setCurrentRow(self.cur_efc_index)

    def build(self):
        self._tab = QWidget()
        self.efc_layout = QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(
            get_button(None, "Load", self.load_selected_efc), 1, 0, 1, 1
        )
        self.set_box(self.efc_layout)
        self._tab.setLayout(self.efc_layout)

    def create_recommendations_list(self):
        self.recoms_qlist = QListWidget()
        self.recoms_qlist.setFont(config.qfont_button)
        self.recoms_qlist.setVerticalScrollBar(get_scrollbar())
        self.recoms_qlist.itemClicked.connect(self.__recoms_qlist_onclick)
        self.recoms_qlist.itemDoubleClicked.connect(self.__recoms_qlist_onDoubleClick)
        return self.recoms_qlist

    def __recoms_qlist_onclick(self, item):
        self.cur_efc_index = self.recoms_qlist.currentRow()

    def __recoms_qlist_onDoubleClick(self, item):
        self.cur_efc_index = self.recoms_qlist.currentRow()
        self.load_selected_efc()

    def nagivate_efc_list(self, move: int):
        new_index = self.cur_efc_index + move
        if new_index < 0:
            self.cur_efc_index = self.files_count - 1
        elif new_index >= self.files_count:
            self.cur_efc_index = 0
        else:
            self.cur_efc_index = new_index
        self.recoms_qlist.setCurrentRow(self.cur_efc_index)

    def load_selected_efc(self):
        if fd := self.get_fd_from_selected_file():
            self.mw.initiate_flashcards(fd)
            self.mw.switch_tab("main")

    def load_next_efc(self):
        if (
            config["efc"]["opt"]["require_recorded"]
            and self.positives + self.negatives != 0
        ):
            fcc_queue.put_notification(
                "Finish your current revision before proceeding", lvl=LogLvl.warn
            )
            return
        elif config["efc"]["opt"]["save_mistakes"] and self.mw.should_save_mistakes():
            self.mw.save_current_mistakes()

        if config["CRE"]["items"]:
            self.fcc.fcc.execute_command(["cre"])
        else:
            self.__load_next_efc()

    def __load_next_efc(self):
        fd = None
        recs = [
            rec
            for rec in self.get_recommendations()
            if rec["fp"] != self.mw.active_file.filepath
        ]

        if not recs:
            fcc_queue.put_notification(
                "There are no EFC recommendations", lvl=LogLvl.warn
            )
            return

        if config["efc"]["opt"]["random"]:
            shuffle(recs)
        if config["efc"]["opt"]["reversed"]:
            recs = reversed(recs)
        if config["efc"]["opt"]["new_first"]:
            recs.sort(key=lambda x: x["is_init"], reverse=True)

        for rec in recs:
            _fd = db_conn.files[rec["fp"]]
            if config["efc"]["opt"]["skip_mistakes"] and _fd.kind == db_conn.KINDS.mst:
                continue
            else:
                fd = _fd
                break

        if fd:
            self.mw.switch_tab("main")
            self.mw.initiate_flashcards(fd)
        else:
            fcc_queue.put_notification(
                "There are no EFC recommendations", lvl=LogLvl.warn
            )

    def load_pickled_model(self):
        try:
            new_model_path = os.path.join(db_conn.RES_PATH, "model.pkl")
            new_model_mtime = os.path.getmtime(new_model_path)
            if self.efc_model.mtime < new_model_mtime:
                self.efc_model = joblib.load(new_model_path)
                self.efc_model.mtime = new_model_mtime
                log.debug(f"Activated custom EFC model: {self.efc_model.name}")
        except FileNotFoundError:
            self.efc_model = StandardModel()
            log.warning("Custom EFC model not found. Recoursing to the Standard Model")

    @property
    def cache_valid(self):
        db_is_upd = (
            self._efc_last_calc_time + 3600 * config["efc"]["cache_expiry_hours"]
            >= time()
        )
        db_current = self._db_load_time_efc == db_conn.last_load
        return db_is_upd and db_current

    def get_recommendations(self) -> list[dict]:
        if self.cache_valid:
            log.debug("Used cached EFC recommendations")
            return self._recoms
        else:
            return self.__get_recommendations()

    def __get_recommendations(self) -> list[dict]:
        t0 = perf_counter()
        self._recoms = list()
        db_conn.refresh()
        if config["mst"]["interval_days"] > 0:
            cur = datetime.now()
            for lng in config["languages"]:
                fmt = db_conn.MST_BASENAME.format(lng=lng)
                for part in range(1, config["mst"]["part_cnt"] + 1):
                    try:
                        sig = f"{fmt}{part}"
                        fp = db_conn.make_filepath(lng, db_conn.MST_DIR, f"{sig}.csv")
                        db_conn.files[fp]
                        lmt = db_conn.get_last_datetime(sig)
                        if (cur - lmt).days >= config["mst"]["interval_days"]:
                            self._recoms.append(
                                {
                                    "fp": fp,
                                    "disp": f"{config['icons']['mistakes']} {sig}",
                                    "score": 0,
                                    "is_init": False,
                                }
                            )
                    except KeyError:
                        log.warning(f"Mistakes file {fp} is missing")
        if config["days_to_new_rev"] > 0:
            self._recoms.extend(self.get_new_recoms())
        for rev in sorted(self.get_efc_data(), key=lambda x: x[2]):
            if rev[2] < config["efc"]["threshold"]:
                prefix = (
                    config["icons"]["initial"]
                    if rev[5]
                    else config["icons"]["revision"]
                )
                self._recoms.append(
                    {
                        "fp": rev[4],
                        "disp": f"{prefix} {rev[0]}",
                        "score": rev[2],
                        "is_init": rev[5],
                    }
                )
        self._efc_last_calc_time = time()
        self._db_load_time_efc = db_conn.last_load
        db_conn.refresh()
        self._recoms.sort(
            key=lambda x: (
                x[config["efc"]["sort"]["key_1"]],
                x[config["efc"]["sort"]["key_2"]],
            )
        )
        log.debug(
            f"Calculated new EFC recommendations in {1000*(perf_counter()-t0):.0f}ms"
        )
        return self._recoms

    def get_efc_data(
        self, preds: bool = False, signatures: set = None
    ) -> list[str, float, str, float, str, bool]:
        """
        Calculates EFC scores for Revisions.
        Returns: list[signature, days_since_last_rev, efc_score, pred_due_hours, filepath, is_initial].
        Optionally: predicts hours to EFC score falling below the threshold.
        """
        rev_table_data = list()
        if signatures:
            db_conn.filter_where_signature_in(signatures)
            sorted_fds = [
                fd
                for fd in db_conn.get_sorted_revisions()
                if fd.signature in signatures
            ]
        else:
            sorted_fds = db_conn.get_sorted_revisions()
        db_conn.filter_for_efc_model()
        unqs = db_conn.gather_efc_record_data()
        now = datetime.now()
        dow = now.weekday()
        hour = now.hour
        month = now.month
        for fd in sorted_fds:
            # data: (TIMESTAMP, TOTAL, POSITIVES, SEC_SPENT, LNG)
            data = unqs.get(fd.signature)
            if data:
                since_last_rev = (now - data[-1][0]).total_seconds() / 3600
                cnt = len(data)
                if cnt < config["init_revs_cnt"]:
                    is_initial = True
                    efc = [[0 if since_last_rev >= config["init_revs_inth"] else 100]]
                    pred = (
                        config["init_revs_inth"] - since_last_rev
                        if since_last_rev <= config["init_revs_inth"]
                        else 0
                    )
                else:
                    is_initial = False
                    total = data[-1][1]
                    since_creation = (now - data[0][0]).total_seconds() / 3600
                    prev_wpm = 60 * data[-1][1] / data[-1][3] if data[-1][3] != 0 else 0
                    prev_score = int(100 * (data[-1][2] / data[-1][1]))
                    first_score = int(100 * (data[0][2] / data[0][1]))
                    std_score = statistics.pstdev([int(d[2] / d[1]) for d in data])
                    total_time = sum(d[3] for d in data)
                    trend_score = np.mean(
                        np.convolve(
                            [int(100 * x[2] / x[1]) for x in data],
                            np.ones(3) / 3,
                            mode="valid",
                        )
                    )
                    rec = [
                        total,
                        prev_wpm,
                        since_creation,
                        since_last_rev,
                        cnt,
                        prev_score,
                        first_score,
                        dow,
                        hour,
                        month,
                        std_score,
                        total_time,
                        trend_score,
                    ]
                    efc = self.efc_model.predict([rec], lng=data[-1][4])
                    if preds:
                        pred = self.guess_when_due(
                            rec.copy(), warm_start=efc[0][0], lng=data[-1][4]
                        )
                    else:
                        pred = 0
                s_efc = [
                    fd.signature,
                    since_last_rev / 24,
                    efc[0][0],
                    pred,
                    fd.filepath,
                    is_initial,
                ]
            else:
                s_efc = [fd.signature, "inf", 0, 0, fd.filepath, True]
            rev_table_data.append(s_efc)

        return rev_table_data

    def guess_when_due(
        self,
        record,
        resh=800,
        warm_start=1,
        max_cycles=100,
        prog_resh=1.1,
        t_tol=0.01,
        lng=None,
    ):
        """
        returns #hours to efc falling below the threshold
        resh - step resolution in hours
        warm_start - initial efc value
        prog_resh - factor for adjusting resh
        t_tol - target diff tolerance in points
        """
        efc_ = warm_start or 1
        init = record[3]
        cycles = 0
        while cycles < max_cycles:
            if efc_ > config["efc"]["threshold"] + t_tol:
                record[3] += resh
            elif efc_ < config["efc"]["threshold"] - t_tol:
                record[3] -= resh
            else:
                break
            efc_ = self.efc_model.predict([record], lng=lng)[0][0]
            resh /= prog_resh
            cycles += 1
        return record[3] - init

    def get_efc_table(self, efc_table_data) -> list[list[str]]:
        # sort revs by number of days ago since last revision
        efc_table_data.sort(key=lambda x: x[3])
        efc_stats_list = [["REV NAME", "AGO", "EFC", "DUE"]]
        for rev in efc_table_data:
            if abs(rev[3]) < 48:
                pred = format_seconds_to(rev[3] * 3600, "hour", rem=2, sep=":")
            elif abs(rev[3]) < 10000:
                pred = format_seconds_to(rev[3] * 3600, "day", rem=0)
            else:
                pred = "Too Long"
            diff_days = "{:.1f}".format(rev[1]) if isinstance(rev[1], float) else rev[1]
            efc_stats_list.append([rev[0], diff_days, "{:.2f}".format(rev[2]), pred])
        return efc_stats_list

    def get_fd_from_selected_file(self):
        try:
            fd = db_conn.files[self._recoms[self.recoms_qlist.currentRow()]["fp"]]
        except AttributeError:  # if no item is selected
            fd = None
        return fd

    def get_new_recoms(self) -> list[dict]:
        """Periodically recommend to create new revision for every lng"""
        recoms = list()
        for lng in config["languages"]:
            for fd in db_conn.get_sorted_revisions():
                if fd.lng == lng:
                    time_delta = db_conn.get_timedelta_from_creation(fd.signature)
                    if time_delta.days >= config["days_to_new_rev"]:
                        recom_text = config["recoms"].get(lng, f"It's time for {lng}")
                        recoms.append(
                            {
                                "fp": choice(
                                    [
                                        fd.filepath
                                        for fd in db_conn.files.values()
                                        if fd.lng == lng
                                        and fd.kind == db_conn.KINDS.lng
                                    ]
                                ),
                                "disp": recom_text,
                                "score": 0,
                                "is_init": False,
                            }
                        )
                    break
        return recoms
