import pandas as pd
import logging
from datetime import datetime, timedelta
from time import time, perf_counter
from csv import DictWriter
from int import fcc_queue, LogLvl
from logtools import audit_log
from data_types import StatChartDataRaw, C, adlt

log = logging.getLogger("DBA")


class DBQueries:
    def __init__(self):
        self.db = pd.DataFrame()
        self.filters = dict(
            NOT_FIRST=False,
            BY_LNG=False,
            BY_SIGNATURE=False,
            EFC_MODEL=False,
            PROGRESS=False,
        )
        self.__last_update = -1.0
        self.DEFAULT_DATE = datetime(1900, 1, 1)

    def __set_last_update(self):
        self.__last_update = time()
        # sbus.efc_calc_job.emit()

    @property
    def last_update(self) -> float:
        return self.__last_update

    def load(self):
        t0 = perf_counter()
        self.__db = pd.read_csv(
            self.DB_PATH,
            encoding="utf-8",
            sep=";",
            parse_dates=["TIMESTAMP"],
            date_format=self.TSFORMAT,
            dtype={
                "TOTAL": "Int64",
                "POSITIVES": "Int64",
                "SEC_SPENT": "Int64",
                "IS_FIRST": "Int64",
            },
        )
        self.db = self.__db.copy(deep=True)
        self.__set_last_update()
        log.debug(f"Loaded database in {1000*(perf_counter()-t0):.3f}ms", stacklevel=3)

    def refresh(self) -> bool:
        if any(self.filters.values()):
            t0 = perf_counter()
            self.__reset_filters_flags()
            self.db = self.__db.copy(deep=True)
            log.debug(
                f"Refreshed database in {1000*(perf_counter()-t0):.3f}ms", stacklevel=3
            )
            return True
        return False

    def __reset_filters_flags(self):
        for key in self.filters.keys():
            self.filters[key] = False

    def create_record(self, words_total, positives, seconds_spent, is_first):
        """Appends a new record to the db for the active file"""
        ts = datetime.now()
        record = {
            "TIMESTAMP": ts.strftime(self.TSFORMAT),
            "SIGNATURE": self.active_file.signature,
            "LNG": self.active_file.lng,
            "TOTAL": words_total,
            "POSITIVES": positives,
            "SEC_SPENT": seconds_spent,
            "KIND": self.active_file.kind,
            "IS_FIRST": is_first,
        }
        with open(self.DB_PATH, "a") as fd:
            dw = DictWriter(fd, fieldnames=self.DB_COLS, delimiter=";")
            dw.writerow(record)
        self.__db.loc[len(self.__db)] = {**record, "TIMESTAMP": ts}
        self.db = self.__db.copy(deep=True)
        self.__set_last_update()
        fcc_queue.put_notification(
            f"Recorded {self.active_file.signature}", lvl=LogLvl.important
        )
        audit_log(
            op=adlt.op.add,
            data=record,
            filepath=self.DB_PATH,
            author=adlt.author.dbq,
            row=len(self.__db) - 1,
        )

    def rename_signature(self, old: str, new: str):
        self.__db["SIGNATURE"] = self.__db["SIGNATURE"].replace(old, new, regex=False)
        self.__db.to_csv(
            self.DB_PATH,
            encoding="utf-8",
            sep=";",
            index=False,
            date_format=self.TSFORMAT,
        )
        self.db = self.__db.copy(deep=True)
        self.__set_last_update()
        audit_log(
            op=adlt.op.rename,
            data=[old, new],
            filepath=self.DB_PATH,
            author=adlt.author.dbq,
            row=":",
        )

    def get_unique_signatures(self):
        return self.db["SIGNATURE"].drop_duplicates(inplace=False)

    def get_unique_signatures_with_existing_files(self) -> set:
        return set(self.db["SIGNATURE"].unique()).intersection(
            fd.signature for fd in self.files.values() if fd.kind == self.KINDS.rev
        )

    def get_sum_repeated(self, signature) -> int:
        cnt = self.db[self.db["SIGNATURE"] == signature].shape[0] - 1
        return int(cnt)

    def get_total_time_spent_for_signature(self, signature=None):
        time_spent = self.get_filtered_db_if("SIGNATURE", signature)
        time_spent = time_spent["SEC_SPENT"].sum()
        time_spent = time_spent if time_spent is not None else 0
        return time_spent

    def get_last_score(self, signature=None):
        try:
            positives = self.get_last_positives(signature)
            total = self.get_total_words(signature)
            return positives / total
        except:
            return 0

    def get_filtered_db_if(self, col: str, condition=None):
        # returns filtered db if condtion is not None
        if condition is None:
            return self.db
        else:
            return self.db[self.db[col] == condition]

    def get_last_positives(self, signature=None, req_not_first=False) -> int:
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            if req_not_first:
                for _, row in res.iloc[::-1].iterrows():
                    if row["IS_FIRST"] == 0:
                        return int(row["POSITIVES"])
            return int(res["POSITIVES"].iloc[-1])
        except:
            return 0

    def get_last_time_spent(self, signature=None, req_not_first=False) -> int:
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            if req_not_first:
                for _, row in res.iloc[::-1].iterrows():
                    if row["IS_FIRST"] == 0:
                        return int(row["SEC_SPENT"])
            return int(res["SEC_SPENT"].iloc[-1])
        except:
            return 0

    def get_total_words(self, signature=None) -> int:
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            return int(res["TOTAL"].iloc[-1])
        except:
            return 0

    def get_max_positives_count(self, signature=None) -> int:
        try:
            positives_list = self.get_filtered_db_if("SIGNATURE", signature)
            positives_list = positives_list["POSITIVES"]
            return int(positives_list.max())
        except:
            return 0

    def get_first_datetime(self, signature) -> datetime:
        try:
            return self.db[self.db["SIGNATURE"] == signature].iloc[0]["TIMESTAMP"]
        except IndexError:
            return self.DEFAULT_DATE

    def get_last_datetime(self, signature) -> datetime:
        try:
            return self.db[self.db["SIGNATURE"] == signature].iloc[-1]["TIMESTAMP"]
        except IndexError:
            return self.DEFAULT_DATE

    def get_last_mistakes_signature_and_datetime(
        self, lng: str
    ) -> tuple[str, datetime]:
        try:
            df = self.db[
                (self.db["LNG"] == lng) & (self.db["KIND"] == self.KINDS.mst)
            ].iloc[-1]
            return df["SIGNATURE"], df["TIMESTAMP"]
        except IndexError:
            return "", datetime(2137, 12, 31)

    def get_timedelta_from_creation(self, signature) -> timedelta:
        first_date = self.get_first_datetime(signature)
        return datetime.now() - first_date

    def get_timedelta_from_last_rev(self, signature) -> timedelta:
        try:
            last_date = self.get_last_datetime(signature)
            return datetime.now() - last_date
        except:
            return timedelta(0)

    def get_count_of_records_missing_time(self, signature=None) -> int:
        res = self.get_filtered_db_if("SIGNATURE", signature)
        return res[self.db["SEC_SPENT"] == 0].shape[0]

    def get_stat_chart_data(self, signature: str) -> StatChartDataRaw:
        db = self.db.loc[self.db["SIGNATURE"] == signature].copy(deep=True)
        sum_repeated = int(db.shape[0])
        sum_sec_spent = db[C.sec_spent].sum()
        missing_records_cnt = db[db[C.sec_spent] == 0].shape[0]
        total_cards = db.iloc[-1][C.total]
        creation_date = db.iloc[0][C.timestamp]
        last_rev_date = db.iloc[-1][C.timestamp]

        if db.iloc[0][C.positives] == 0:
            # Remove first Revision if ungraded
            db.drop(db.index[0], inplace=True)

        sec_spent = db[C.sec_spent].values.tolist()
        positives = db[C.positives].values.tolist()
        dates = db[C.timestamp].dt.date.values.tolist()
        time_spent = db[C.sec_spent].values.tolist()

        return StatChartDataRaw(
            positives=positives,
            dates=dates,
            total_cards=total_cards,
            time_spent_seconds=time_spent,
            sum_repeated=sum_repeated,
            creation_date=creation_date,
            last_rev_date=last_rev_date,
            sec_spent=sec_spent,
            sum_seconds_spent=sum_sec_spent,
            missing_records_cnt=missing_records_cnt,
        )

    def get_filtered_by_lng(self, lngs: list):
        return self.__get_filtered_by_lng(lngs)

    def __get_filtered_by_lng(self, lngs: set) -> pd.DataFrame:
        if lngs:
            if not isinstance(lngs, (set, list, tuple)):
                lngs = {
                    lngs,
                }
            return self.db[self.db["LNG"].isin(lngs)]
        else:
            return self.db

    def filter_where_not_first(self):
        self.db = self.db.loc[self.db["IS_FIRST"] == 0]
        self.filters["NOT_FIRST"] = True

    def filter_where_signature(self, signature: str):
        self.db = self.db.loc[self.db["SIGNATURE"] == signature]
        self.filters["BY_SIGNATURE"] = signature

    def filter_where_signature_in(self, signatures: set):
        self.db = self.db.loc[self.db["SIGNATURE"].isin(signatures)]
        self.filters["BY_SIGNATURE"] = signatures

    def filter_where_lng(self, lngs: list = []):
        self.db = self.__get_filtered_by_lng(lngs)
        self.filters["BY_LNG"] = lngs

    def filter_for_progress(self, lngs: set):
        self.db = self.db[
            (self.db["KIND"] == self.KINDS.rev)
            & (self.db["LNG"].isin(lngs))
            & (~self.db["IS_FIRST"])
        ]
        self.filters["PROGRESS"] = True

    def get_avg_cpm(self, default=0) -> float:
        if div := self.db["SEC_SPENT"].sum():
            return self.db["TOTAL"].sum() / (div / 60)
        else:
            return default

    def get_avg_score(self, default=0) -> float:
        if div := self.db["TOTAL"].sum():
            return self.db["POSITIVES"].sum() / div
        else:
            return default

    def get_all(self):
        return self.db

    def get_unique_languages(self) -> list:
        return self.db["LNG"].drop_duplicates(inplace=False).values.tolist()

    def get_cards_total(self, signatures: list) -> int:
        db = self.db.drop_duplicates(subset="SIGNATURE", keep="last")
        return int(db[db["SIGNATURE"].isin(signatures)]["TOTAL"].sum())

    def get_cre_data(self, signature: str) -> dict:
        """Fetch data for <signature> latest"""
        return {
            "cards_seen": self.get_total_words(signature),
            "time_spent": self.get_last_time_spent(signature),
            "positives": self.get_last_positives(signature),
        }

    def get_seconds_spent_today(self, lng: str) -> int:
        today = datetime.now().date()
        filtered = self.db[
            (self.db["TIMESTAMP"].dt.date == today) & (self.db["LNG"] == lng)
        ]["SEC_SPENT"]
        return int(filtered.sum())
