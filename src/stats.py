import pandas as pd
from utils import *
from cfg import config
from datetime import datetime
import DBAC.api as api


class Stats:

    def __init__(self):
        self.config = config
        self.db = api.DbOperator()

    def get_data_for_current_revision(self, signature):
        self.db.refresh()
        self.db.filter_where_signature_is_equal_to(signature)

        # get data
        self.chart_values = self.db.get_chart_positives()
        self.chart_dates = self.db.get_chart_dates()
        self.total_cards = self.db.get_total_words()
        self.total_seconds_spent = self.db.get_total_time_spent_for_signature()
        self.time_spent_seconds = self.db.get_chart_time_spent()
        self.missing_records_cnt = self.db.get_count_of_records_missing_time()
        self.time_spent_minutes = [
            datetime.fromtimestamp(x).strftime("%M:%S") for x in self.time_spent_seconds
        ]
        self.formatted_dates = [date.strftime("%d-%m\n%Y") for date in self.chart_dates]
        self.sum_repeated = self.db.get_sum_repeated(self.db.active_file.signature)
        self.days_ago = format_timedelta(
            self.db.get_timedelta_from_creation(self.db.active_file.signature)
        )
        self.last_rev_days_ago = format_timedelta(
            self.db.get_timedelta_from_last_rev(self.db.active_file.signature)
        )

        # Create Dynamic Chain Index
        if self.config["opt"]["show_percent_stats"]:
            self.create_dynamic_chain_percentages(tight_format=True)
        else:
            self.create_dynamic_chain_values(tight_format=True)
        self.db.refresh()

    def create_dynamic_chain_values(self, tight_format: bool = True):
        self.dynamic_chain_index = [
            self.chart_values[0] if len(self.chart_values) >= 1 else ""
        ]
        tight_format = "\n" if tight_format else " "
        [
            self.dynamic_chain_index.append(
                "{main_val}{tf}({sign_}{dynamic})".format(
                    main_val=self.chart_values[x],
                    tf=tight_format,
                    sign_=get_sign(
                        self.chart_values[x] - self.chart_values[x - 1], neg_sign=""
                    ),
                    dynamic=self.chart_values[x] - self.chart_values[x - 1],
                )
            )
            for x in range(1, len(self.chart_values))
        ]

    def create_dynamic_chain_percentages(self, tight_format: bool = True):
        self.dynamic_chain_index = [
            (
                "{:.0%}".format(self.chart_values[0] / self.total_cards)
                if len(self.chart_values) >= 1
                else ""
            )
        ]
        tight_format = "\n" if tight_format else " "
        [
            self.dynamic_chain_index.append(
                "{main_val:.0%}{tf}{sign_}{dynamic:.0f}pp".format(
                    main_val=self.chart_values[x] / self.total_cards,
                    tf=tight_format,
                    sign_=get_sign(
                        self.chart_values[x] - self.chart_values[x - 1], neg_sign=""
                    ),
                    dynamic=100
                    * (self.chart_values[x] - self.chart_values[x - 1])
                    / self.total_cards,
                )
            )
            for x in range(1, len(self.chart_values))
        ]

    def get_data_for_progress(self, lngs: set):
        self.db.refresh()
        self.db.filter_for_progress(lngs)
        if self.db.db.empty:
            raise ValueError
        df = self.db.db

        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"]).dt.strftime("%m/%y")
        counted = df["TIMESTAMP"].value_counts(sort=False)
        self.revision_count = counted.values
        self.formatted_dates = counted.index

        df.drop_duplicates(["SIGNATURE", "TIMESTAMP"], inplace=True, keep="last")
        df.drop_duplicates("SIGNATURE", inplace=True, keep="first")
        grouped = df.groupby("TIMESTAMP", sort=False)
        self.chart_values = grouped["POSITIVES"].sum()
        self.second_chart_values = grouped["TOTAL"].sum()
