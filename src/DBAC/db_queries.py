import pandas as pd
import logging
from datetime import datetime, timedelta
from time import time, perf_counter
from csv import DictWriter
from utils import fcc_queue, LogLvl

log = logging.getLogger("DBAC")


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
        self.last_update: float = 0
        self.last_load: float = -1
        self.DEFAULT_DATE = datetime(1900, 1, 1)

    def refresh(self) -> bool:
        if self.last_load < self.last_update:
            t0 = perf_counter()
            self.db = pd.read_csv(
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
            self.__db = self.db.copy(deep=True)
            self.last_load = time()
            self.__reset_filters_flags()
            log.debug(
                f"Reloaded database in {1000*(perf_counter()-t0):.3f}ms", stacklevel=3
            )
            return True
        elif any(self.filters.values()):
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

    def require_refresh(func):
        def inner(self, *args, **kwargs):
            self.refresh()
            res = func(self, *args, **kwargs)
            return res

        return inner

    def write_op(func):
        def inner(self, *args, **kwargs):
            res = func(self, *args, **kwargs)
            self.last_update = time()
            self.refresh()
            return res

        return inner

    @write_op
    def create_record(self, words_total, positives, seconds_spent, is_first):
        """Appends a new record to the db for the active file"""
        record = {
            "TIMESTAMP": datetime.now().strftime(self.TSFORMAT),
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
        fcc_queue.put_notification(f"Recorded {self.active_file.signature}", lvl=LogLvl.important)
        log.debug(f"Created Record: {record}")

    @write_op
    def rename_signature(self, old, new):
        self.refresh()
        self.db["SIGNATURE"] = self.db["SIGNATURE"].replace(old, new, regex=False)
        self.db.to_csv(
            self.DB_PATH,
            encoding="utf-8",
            sep=";",
            index=False,
            date_format=self.TSFORMAT,
        )
        log.debug(f"Renamed signature '{old}' to '{new}'")

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
            return 0

    def get_count_of_records_missing_time(self, signature=None) -> int:
        res = self.get_filtered_db_if("SIGNATURE", signature)
        return res[self.db["SEC_SPENT"] == 0].shape[0]

    def get_chart_positives(self, signature=None) -> list[int]:
        return self.__get_chart_data_deduplicated(
            "POSITIVES", signature
        ).values.tolist()

    def get_chart_dates(self, signature=None) -> list[pd.Timestamp]:
        return self.__get_chart_data_deduplicated("TIMESTAMP", signature)

    def get_chart_time_spent(self, signature=None) -> list[int]:
        return self.__get_chart_data_deduplicated(
            "SEC_SPENT", signature
        ).values.tolist()

    def __get_chart_data_deduplicated(
        self, return_col_name, signature=None
    ) -> pd.DataFrame:
        # get data for each repetition - if more than 1 repetition
        # occured on one day - retrieve result for the last one.
        res = self.get_filtered_db_if("SIGNATURE", signature)
        res = res[self.db["IS_FIRST"] == 0]
        res["TIME"] = res["TIMESTAMP"].dt.date
        res = res.drop_duplicates(subset=["TIME"], keep="last")
        return res[return_col_name]

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

    def filter_where_signature_is_equal_to(self, signature):
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
            & (self.db["POSITIVES"] != 0)
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
