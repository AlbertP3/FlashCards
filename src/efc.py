import joblib  # type: ignore
from random import choice
from functools import cache
from datetime import datetime
from logging import log
from math import exp
import DBAC.api as api
from utils import *

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
            total, prev_wpm, ts_creation, ts_last_rev, repeated_times, prev_score = r
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
        self.config = Config()
        self.paths_to_suggested_lngs = dict()
        self.db = api.DbOperator()
        self.efc_model = StandardModel()
        self.load_pickled_model()

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

    def get_recommendations(self):
        recommendations = list()
        self.new_revs = 0
        if self.db.refresh(ignore_filters={"EFC_MODEL"}):
            self.get_complete_efc_table.cache_clear()
        if self.config["days_to_new_rev"] > 0:
            recommendations.extend(self.is_it_time_for_something_new())
        for rev in self.get_complete_efc_table():
            efc_critera_met = rev[2] < self.config["efc_threshold"]
            if efc_critera_met:
                recommendations.append(rev[0])
        return recommendations

    @cache
    def get_complete_efc_table(self, preds: bool = False) -> list[str, str, float]:
        rev_table_data = list()
        self.db.filter_for_efc_model()
        unqs = self.db.gather_efc_record_data()
        init_revs = self.config["init_revs_cnt"]
        init_revs_inth = self.config["init_revs_inth"]

        for fd in self.db.get_sorted_revisions():
            # data: (TIMESTAMP, TOTAL, POSITIVES, SEC_SPENT, LNG)
            data = unqs.get(fd.signature)
            if data:
                since_last_rev = (datetime.now() - data[-1][0]).total_seconds() / 3600
                cnt = len(data) + 1
                if cnt <= init_revs:
                    efc = [[0 if since_last_rev >= init_revs_inth else 100]]
                    pred = (
                        init_revs_inth - since_last_rev
                        if since_last_rev <= init_revs_inth
                        else 0
                    )
                else:
                    total = data[-1][1]
                    since_creation = (
                        datetime.now() - data[0][0]
                    ).total_seconds() / 3600
                    prev_wpm = 60 * data[-1][1] / data[-1][3] if data[-1][3] != 0 else 0
                    prev_score = int(100 * (data[-1][2] / data[-1][1]))
                    rec = [
                        total,
                        prev_wpm,
                        since_creation,
                        since_last_rev,
                        cnt,
                        prev_score,
                    ]
                    efc = self.efc_model.predict([rec], lng=data[-1][4])
                    if preds:
                        pred = self.guess_when_due(
                            rec.copy(), warm_start=efc[0][0], lng=data[-1][4]
                        )
                    else:
                        pred = 0
                s_efc = [fd.signature, since_last_rev / 24, efc[0][0], pred]
            else:
                s_efc = [fd.signature, "inf", 0, 0]
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
        # returns #hours to efc falling below the threshold
        # resh - step resolution in hours
        # warm_start - initial efc value
        # prog_resh - factor for adjusting resh
        # t_tol - target diff tolerance in points
        efc_ = warm_start or 1
        init = record[3]
        cycles = 0
        while cycles < max_cycles:
            if efc_ > self.config["efc_threshold"] + t_tol:
                record[3] += resh
            elif efc_ < self.config["efc_threshold"] - t_tol:
                record[3] -= resh
            else:
                break
            efc_ = self.efc_model.predict([record], lng=lng)[0][0]
            resh /= prog_resh
            cycles += 1
        return record[3] - init

    def get_efc_table_printout(self, efc_table_data, lim=None):
        # sort revs by number of days ago since last revision
        efc_table_data.sort(key=lambda x: x[3])
        if lim:
            efc_table_data = efc_table_data[:lim]
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
        w = self.console.width()*0.8
        printout = self.caliper.make_table(
            data=efc_stats_list,
            pixlim=[0.5*w, 0.18*w, 0.18*w, 0.18*w],
            align=["left", "right", "right", "right"],
        )
        return printout

    def get_fd_from_selected_file(self):
        try:
            i = self.recommendation_list.currentItem().text()
            if self.recommendation_list.currentRow() >= self.new_revs:
                fd = [fd for fd in self.db.files.values() if fd.basename == i][0]
            else:  # Select New Recommendation
                fd = self.db.files[self.paths_to_suggested_lngs[i]]
        except AttributeError:  # if no item is selected
            fd = None
        return fd

    def is_it_time_for_something_new(self):
        # Periodically recommend to create new revision for every lng
        new_recommendations = list()
        for lng in self.config["languages"]:
            for fd in self.db.get_sorted_revisions():
                if fd.lng == lng:
                    time_delta = self.db.get_timedelta_from_creation(fd.signature)
                    if time_delta.days >= self.config["days_to_new_rev"]:
                        new_recommendations.append(self.get_recommendation_text(lng))
                    break
        return new_recommendations

    def get_recommendation_text(self, lng: str):
        # adding key to the dictionary facilitates matching
        # recommendation text with the lng file
        text = self.config["RECOMMENDATIONS"].get(lng, f"It's time for {lng}")
        self.paths_to_suggested_lngs[text] = choice(
            [
                fd.filepath
                for fd in self.db.files.values()
                if fd.lng == lng and fd.kind == self.db.KINDS.lng
            ]
        )
        self.new_revs += 1
        return text
