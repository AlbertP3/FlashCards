from datetime import datetime, timedelta
import pandas as pd
from time import monotonic, perf_counter
import logging
from utils import fcc_queue

log = logging.getLogger("DBAC")


class db_queries:
    def __init__(self):
        self.db = pd.DataFrame()
        self.filters = dict(
            POS_NOT_ZERO=False,
            BY_LNG=False,
            BY_SIGNATURE=False,
            EFC_MODEL=False,
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
                },
            )
            self.__db = self.db.copy(deep=True)
            self.last_load = monotonic()
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

    def write_op(func):
        def inner(self, *args, **kwargs):
            res = func(self, *args, **kwargs)
            self.last_update = monotonic()
            self.refresh()
            return res

        return inner

    @write_op
    def create_record(self, words_total, positives, seconds_spent):
        """Appends a new record to the db for the active file"""
        with open(self.DB_PATH, "a") as fd:
            record = self.make_record(
                timestamp=datetime.now().strftime(self.TSFORMAT),
                signature=self.active_file.signature,
                lng=self.active_file.lng,
                total=str(words_total),
                positives=str(positives),
                sec_spent=str(seconds_spent),
                kind=self.active_file.kind,
            )
            fd.write(record + "\n")
        fcc_queue.put(f"Recorded {self.active_file.signature}")
        log.debug(f"Created Record: {record}")

    def make_record(self, **kwargs) -> str:
        """Enforce proper format as specified by DB_COLS"""
        return ";".join([kwargs[col.lower()] for col in self.DB_COLS])

    @write_op
    def rename_signature(self, old, new):
        self.refresh()
        self.db["SIGNATURE"] = self.db["SIGNATURE"].replace(old, new)
        self.db.to_csv(
            self.DB_PATH,
            encoding="utf-8",
            sep=";",
            index=False,
            date_format=self.TSFORMAT,
        )
        log.debug(f"Renamed signature '{old}' to '{new}'")

    def get_unique_signatures(self):
        return self.db["SIGNATURE"].drop_duplicates()

    def get_unique_signatures_with_existing_files(self) -> set:
        return set(self.db["SIGNATURE"].unique()).intersection(
            fd.signature for fd in self.files.values() if fd.kind == self.KINDS.rev
        )

    def get_sum_repeated(self, signature=None) -> int:
        repeated_times = self.get_filtered_db_if("SIGNATURE", signature)
        repeated_times = repeated_times.count().iloc[0] - 1
        repeated_times = 0 if repeated_times is None else int(repeated_times)
        return repeated_times

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

    def get_last_positives(self, signature=None, req_pos: bool = False):
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            if req_pos:
                for _, row in res.iloc[::-1].iterrows():
                    if row["POSITIVES"] != 0:
                        return row["POSITIVES"]
            return res["POSITIVES"].iloc[-1]
        except:
            return 0

    def get_last_time_spent(self, signature=None, req_pos=False):
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            if req_pos:
                for _, row in res.iloc[::-1].iterrows():
                    if row["POSITIVES"] != 0:
                        return row["SEC_SPENT"]
            return res["SEC_SPENT"].iloc[-1]
        except:
            return 0

    def get_total_words(self, signature=None):
        try:
            res = self.get_filtered_db_if("SIGNATURE", signature)
            return res["TOTAL"].iloc[-1]
        except:
            return 0

    def get_max_positives_count(self, signature=None):
        try:
            positives_list = self.get_filtered_db_if("SIGNATURE", signature)
            positives_list = positives_list["POSITIVES"]
            return positives_list.max()
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
        res = res[self.db["POSITIVES"] != 0]
        res["TIME"] = res["TIMESTAMP"].apply(lambda x: x.dayofyear)
        res = res.drop_duplicates(subset=["TIME"], keep="last")
        return res[return_col_name]

    def get_filtered_by_lng(self, lngs: list):
        return self.__get_filtered_by_lng(lngs)

    def __get_filtered_by_lng(self, lngs: set) -> pd.DataFrame:
        if lngs:
            if not isinstance(lngs, (set, list)):
                lngs = {
                    lngs,
                }
            return self.db[self.db["LNG"].isin(lngs)]
        else:
            return self.db

    def filter_where_positives_not_zero(self):
        # modifies self.db to contain only revision with POSITIVES != 0
        self.db = self.db.loc[self.db["POSITIVES"] != 0]
        self.filters["POS_NOT_ZERO"] = True

    def filter_where_signature_is_equal_to(self, signature):
        self.db = self.db.loc[self.db["SIGNATURE"] == signature]
        self.filters["BY_SIGNATURE"] = signature

    def filter_where_lng(self, lngs: list = []):
        self.db = self.__get_filtered_by_lng(lngs)
        self.filters["BY_LNG"] = lngs

    def get_avg_cpm(self):
        return self.db["TOTAL"].sum() / (self.db["SEC_SPENT"].sum() / 60)

    def get_avg_score(self):
        return self.db["POSITIVES"].sum() / self.db["TOTAL"].sum()

    def get_all(self):
        return self.db
