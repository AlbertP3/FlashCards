import pandas as pd
import numpy as np
import logging
import statistics

log = logging.getLogger("DBAC")


class db_efc_queries:
    def filter_for_efc_model(self, lngs: list = None):
        # Remove mistakes, obsolete lngs and revs with POSITIVES=0
        self.db = self.db[self.db["LNG"].isin(lngs or self.config["languages"])]
        self.db = self.db[self.db["KIND"] == self.KINDS.rev]
        self.db = self.db.loc[self.db["POSITIVES"] != 0]
        self.filters["EFC_MODEL"] = True

    def add_efc_metrics(self, fill_timespent=False):
        """expands db with efc metrics"""
        self.db["TIMESTAMP"] = pd.to_datetime(
            self.db["TIMESTAMP"], format="%m/%d/%Y, %H:%M:%S"
        )

        sig = {k: list() for k in self.db["SIGNATURE"].unique()}
        if fill_timespent:
            avg_wpsec = (
                self.db["TOTAL"].sum()
                / self.db.loc[self.db["SEC_SPENT"] > 0]["SEC_SPENT"].sum()
            )
        else:
            avg_wpsec = 0
        rows_to_del = list()
        self.db["PREV_WPM"] = float(0)
        self.db["TIMEDELTA_SINCE_CREATION"] = 0
        self.db["TIMEDELTA_LAST_REV"] = 0
        self.db["CUM_CNT_REVS"] = 0
        self.db["PREV_SCORE"] = 0
        self.db["FIRST_SCORE"] = 0
        self.db["DOW"] = 0
        self.db["HOUR"] = 0
        self.db["MONTH"] = 0
        self.db["STD_SCORE"] = float(0)
        self.db["TOTAL_TIME"] = float(0)
        self.db["TREND_SCORE"] = float(0)
        self.db["SCORE"] = 0

        for i, r in self.db.iterrows():
            s = r["SIGNATURE"]
            # Tackle missing sec_spent
            if r["SEC_SPENT"] == 0:
                if fill_timespent:
                    self.db.loc[i, "SEC_SPENT"] = int(r["TOTAL"] / avg_wpsec)
                    r["SEC_SPENT"] = int(r["TOTAL"] / avg_wpsec)
                else:
                    rows_to_del.append(i)
                    continue
            sig[s].append((r["TIMESTAMP"], r["TOTAL"], r["POSITIVES"], r["SEC_SPENT"]))
            # Skip initial repetitions
            if len(sig[s]) <= 2:
                rows_to_del.append(i)
                continue
            # '-2' denotes previous revision
            self.db.loc[i, "PREV_WPM"] = round(60 * sig[s][-2][1] / sig[s][-2][3], 0)
            self.db.loc[i, "CUM_CNT_REVS"] = len(sig[s])
            self.db.loc[i, "TIMEDELTA_LAST_REV"] = int(
                (sig[s][-1][0] - sig[s][-2][0]).total_seconds() / 3600
            )
            self.db.loc[i, "TIMEDELTA_SINCE_CREATION"] = int(
                (sig[s][-1][0] - sig[s][0][0]).total_seconds() / 3600
            )
            self.db.loc[i, "PREV_SCORE"] = int(100 * (sig[s][-2][2] / sig[s][-2][1]))

            self.db.loc[i, "FIRST_SCORE"] = int(100 * sig[s][0][2] / sig[s][0][1])
            self.db.loc[i, "DOW"] = sig[s][-1][0].weekday()
            self.db.loc[i, "HOUR"] = sig[s][-1][0].hour
            self.db.loc[i, "MONTH"] = sig[s][-1][0].month
            self.db.loc[i, "STD_SCORE"] = statistics.pstdev(
                [int(100 * x[2] / x[1]) for x in sig[s]]
            )
            self.db.loc[i, "TOTAL_TIME"] = sum(x[3] for x in sig[s])
            self.db.loc[i, "TREND_SCORE"] = np.mean(
                np.convolve(
                    [int(100 * x[2] / x[1]) for x in sig[s]],
                    np.ones(3) / 3,
                    mode="valid",
                )
            )
            self.db.loc[i, "SCORE"] = int(100 * sig[s][-1][2] / sig[s][-1][1])

        self.db = self.db.drop(index=rows_to_del, axis=0)
        self.filters["EFC_MODEL"] = True

    def remove_cols_for_efc_model(self, drop_lng=False):
        cols_to_remove = {"POSITIVES", "TIMESTAMP", "SIGNATURE", "SEC_SPENT", "KIND"}
        if drop_lng:
            cols_to_remove.add("LNG")
        self.db = self.db.drop(cols_to_remove, axis=1)
        self.db = self.db.apply(pd.to_numeric, errors="ignore")
        self.filters["EFC_MODEL"] = True

    def gather_efc_record_data(self) -> dict:
        # Create a dictionary, mapping signatures to tuples of all matching revs
        self.db["TIMESTAMP"] = pd.to_datetime(
            self.db["TIMESTAMP"], format="%m/%d/%Y, %H:%M:%S"
        )
        sig = {k: list() for k in self.db["SIGNATURE"].unique()}
        for i, r in self.db.iterrows():
            sig[r["SIGNATURE"]].append(
                (r["TIMESTAMP"], r["TOTAL"], r["POSITIVES"], r["SEC_SPENT"], r["LNG"])
            )
        return sig

    def encode_language_columns(self, lngs: list):
        for v in lngs[:-1]:  # Avoid correlated features
            self.db[v] = self.db["LNG"].apply(lambda r: 1 if r == v else 0)
        self.db = self.db.drop(["LNG"], axis=1)
        self.filters["EFC_MODEL"] = True
