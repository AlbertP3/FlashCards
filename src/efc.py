import joblib  # type: ignore
from random import choice
from datetime import datetime
from time import time
import logging
from math import exp
import DBAC.api as api
import statistics
import numpy as np
from utils import *
from cfg import config

log = logging.getLogger("EFC")


class StandardModel:
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


class EFC:
    """
    Based on Ebbinghaus Forgetting Curve
    Estimates the percentage of words in-memory
    """

    def __init__(self):
        self.config = config
        self.db = api.DbOperator()
        self.efc_model = StandardModel()
        self.load_pickled_model()
        self._efc_last_calc_time = 0
        self._db_load_time_efc = 0
        self._recoms: list[dict] = list()  # {fp, disp, score, is_init}

    def load_pickled_model(self):
        try:
            new_model_path = os.path.join(self.db.RES_PATH, "model.pkl")
            new_model_mtime = os.path.getmtime(new_model_path)
            if self.efc_model.mtime < new_model_mtime:
                self.efc_model = joblib.load(new_model_path)
                self.efc_model.mtime = new_model_mtime
                log.debug(f"Activated custom EFC model: {self.efc_model.name}")
        except FileNotFoundError:
            self.efc_model = StandardModel()
            log.warning("Custom EFC model not found. Recoursing to the Standard Model")

    def get_recommendations(self) -> list[dict]:
        cache_valid = (
            self._efc_last_calc_time + 3600 * self.config["efc"]["cache_expiry_hours"]
            >= time()
        )
        db_current = self._db_load_time_efc == self.db.last_load
        if cache_valid and db_current:
            log.debug("Used cached EFC recommendations")
            return self._recoms
        else:
            log.debug("Calculated new EFC recommendations")
            return self.__get_recommendations()

    def __get_recommendations(self) -> list[dict]:
        self._recoms = list()
        self.db.refresh()
        if self.config["mst"]["interval_days"] > 0:
            cur = datetime.now()
            for lng in self.config["languages"]:
                fmt = self.db.MST_BASENAME.format(lng=lng)
                try:
                    for part in range(1, self.config["mst"]["part_cnt"] + 1):
                        sig = f"{fmt}{part}.csv"
                        fp = self.db.make_filepath(lng, self.db.MST_DIR, sig)
                        self.db.files[fp]
                        lmt = self.db.get_last_datetime(fmt)
                        if (cur - lmt).days >= self.config["mst"]["interval_days"]:
                            self._recoms.append(
                                {
                                    "fp": fp,
                                    "disp": f"{self.config['icons']['mistakes']} {sig}",
                                    "score": 0,
                                    "is_init": False,
                                }
                            )
                except KeyError:
                    pass
        if self.config["days_to_new_rev"] > 0:
            self._recoms.extend(self.get_new_recoms())
        for rev in sorted(self.get_efc_data(), key=lambda x: x[2]):
            if rev[2] < self.config["efc"]["threshold"]:
                prefix = (
                    self.config["icons"]["initial"]
                    if rev[5]
                    else self.config["icons"]["revision"]
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
        self._db_load_time_efc = self.db.last_load
        self.db.refresh()
        self._recoms.sort(
            key=lambda x: (
                x[self.config["efc"]["sort"]["key_1"]],
                x[self.config["efc"]["sort"]["key_2"]],
            )
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
            self.db.filter_where_signature_in(signatures)
            sorted_fds = [
                fd
                for fd in self.db.get_sorted_revisions()
                if fd.signature in signatures
            ]
        else:
            sorted_fds = self.db.get_sorted_revisions()
        self.db.filter_for_efc_model()
        unqs = self.db.gather_efc_record_data()
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
                if cnt < self.config["init_revs_cnt"]:
                    is_initial = True
                    efc = [
                        [0 if since_last_rev >= self.config["init_revs_inth"] else 100]
                    ]
                    pred = (
                        self.config["init_revs_inth"] - since_last_rev
                        if since_last_rev <= self.config["init_revs_inth"]
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
            if efc_ > self.config["efc"]["threshold"] + t_tol:
                record[3] += resh
            elif efc_ < self.config["efc"]["threshold"] - t_tol:
                record[3] -= resh
            else:
                break
            efc_ = self.efc_model.predict([record], lng=lng)[0][0]
            resh /= prog_resh
            cycles += 1
        return record[3] - init

    def get_efc_table_printout(self, efc_table_data):
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
        w = self.console.width() * 0.8
        printout = self.caliper.make_table(
            data=efc_stats_list,
            pixlim=[0.5 * w, 0.18 * w, 0.18 * w, 0.18 * w],
            align=["left", "right", "right", "right"],
        )
        return printout

    def get_fd_from_selected_file(self):
        try:
            fd = self.db.files[self._recoms[self.recoms_qlist.currentRow()]["fp"]]
        except AttributeError:  # if no item is selected
            fd = None
        return fd

    def get_new_recoms(self) -> list[dict]:
        """Periodically recommend to create new revision for every lng"""
        recoms = list()
        for lng in self.config["languages"]:
            for fd in self.db.get_sorted_revisions():
                if fd.lng == lng:
                    time_delta = self.db.get_timedelta_from_creation(fd.signature)
                    if time_delta.days >= self.config["days_to_new_rev"]:
                        recom_text = self.config["recoms"].get(
                            lng, f"It's time for {lng}"
                        )
                        recoms.append(
                            {
                                "fp": choice(
                                    [
                                        fd.filepath
                                        for fd in self.db.files.values()
                                        if fd.lng == lng
                                        and fd.kind == self.db.KINDS.lng
                                    ]
                                ),
                                "disp": recom_text,
                                "score": 0,
                                "is_init": False,
                            }
                        )
                    break
        return recoms
