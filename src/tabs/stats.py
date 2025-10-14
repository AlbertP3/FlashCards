import logging
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from cfg import config
from utils import format_seconds_to, fcc_queue, LogLvl, format_timedelta, get_sign
from DBAC import db_conn
from tabs.base import BaseTab
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("GUI")


class StatsTab(BaseTab):

    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.mw = mw
        self.id = "stats"
        self.upd = 0
        self.sig = ""
        self.build()
        self.mw.add_tab(self.tab, self.id, "Statistics")

    @property
    def cache_valid(self):
        return (
            self.upd >= db_conn.last_update
            and self.sig == self.mw.active_file.signature
        )

    def open(self):
        if self.mw.active_file.kind == db_conn.KINDS.rev:
            self.mw.switch_tab(self.id)
            if not self.cache_valid:
                self.show()
                self.upd = db_conn.last_update
                self.sig = self.mw.active_file.signature
        else:
            fcc_queue.put_notification(
                f"Statistics are not available for a {db_conn.KFN[self.mw.active_file.kind]}",
                lvl=LogLvl.warn,
            )

    def show(self):
        with self.mw.loading_ctx("load_and_show_stats"):
            self.figure.clear()
            self.get_data_for_current_revision(self.mw.active_file.signature)
            self.get_stats_chart()
            self.get_stats_table()

    def build(self):
        self.stats_layout = QGridLayout()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stat_table = QGridLayout()
        self.stats_layout.addLayout(self.stat_table, 1, 0)
        self.set_box(self.stats_layout)
        self.tab.setLayout(self.stats_layout)

    def get_stats_chart(self):
        rect = None
        ax = self.figure.add_subplot()
        ax.bar(
            self.formatted_dates,
            self.chart_values,
            color=config.mpl["stat_bar_color"],
            edgecolor=config.mpl["chart_edge_color"],
            linewidth=0.7,
            align="center",
        )

        # Time spent for each revision
        time_spent_plot = ax.twinx()
        time_spent_plot.plot(
            self.formatted_dates,
            self.time_spent_minutes,
            color=config.mpl["chart_secondary_color"],
            linewidth=1,
            zorder=9,
        )

        # Labels
        for rect, label in zip(ax.patches, self.dynamic_chain_index):
            height = rect.get_height()
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                height / 2,
                label,
                ha="center",
                va="bottom",
                color=config.mpl["stat_chart_text_color"],
                fontsize=config["theme"]["font_stats_size"],
            )

        # horizontal line at EFC predicate
        if rect and config["opt"]["show_efc_line"]:
            ax.axhline(
                y=self.total_cards * 0.8,
                color=config.mpl["chart_line_color"],
                linestyle="--",
                zorder=-3,
            )
            ax.text(
                rect.get_x() + rect.get_width() / 1,
                self.total_cards * 0.8,
                f'{config["efc"]["threshold"]}%',
                va="bottom",
                color=config.mpl["chart_line_color"],
                fontsize=config["theme"]["font_stats_size"],
            )

        # add labels - time spent
        if config["opt"]["show_cpm_stats"]:
            time_spent_labels = [
                "{:.0f}".format(self.total_cards / (x / 60)) if x else "-"
                for x in self.time_spent_seconds
            ]
        else:
            time_spent_labels = self.time_spent_minutes
        for x, y in zip(self.formatted_dates, time_spent_labels):
            # xytext - distance between points and text label
            time_spent_plot.annotate(
                y,
                (x, y),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                color=config.mpl["stat_chart_text_color"],
                fontsize=config["theme"]["font_stats_size"],
            )

        # Style
        self.figure.set_facecolor(config.mpl["stat_background_color"])
        ax.set_facecolor(config.mpl["stat_chart_background_color"])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
        ax.set_ylim([0, self.total_cards + 2])
        ax.set_xlim(-0.5, abs(len(self.formatted_dates) - 0.5))
        ax.tick_params(
            colors=config.mpl["stat_chart_text_color"],
            labelrotation=0,
            pad=1,
            labelsize=config["theme"]["font_stats_size"],
        )
        self.figure.tight_layout(pad=0.1)
        ax.get_yaxis().set_visible(False)
        time_spent_plot.get_yaxis().set_visible(False)
        time_spent_plot.set_ylim([0, 9999])
        self.figure.subplots_adjust(left=0.0, bottom=0.1, right=0.999, top=0.997)

        self.canvas.draw()

    def get_stats_table(self):
        self.repeated_times_button = self.create_stats_button(
            f'Repeated\n{self.sum_repeated} time{"s" if self.sum_repeated > 1 else ""}'
        )
        self.days_from_last_rev = self.create_stats_button(
            f'Last Revision\n{str(self.last_rev_days_ago).split(",")[0]} ago'
        )
        self.days_from_creation = self.create_stats_button(
            f'Created\n{str(self.days_ago).split(",")[0]} ago'
        )

        # estimate total time spent if some records miss time_spent
        interval, rem = (("minute", 0), ("hour", 2))[self.total_seconds_spent > 3600]
        if self.missing_records_cnt == 0:
            self.missing_records_adj = format_seconds_to(
                self.total_seconds_spent,
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
        elif self.total_seconds_spent != 0:
            # estimate total time by adding to actual total_seconds_spent,
            # the estimate = X * count of missing records multiplied by average time spent on non-zero revision
            # X is an arbitrary number to adjust for learning curve
            adjustment = (
                1.481
                * self.missing_records_cnt
                * (
                    self.total_seconds_spent
                    / (self.sum_repeated - self.missing_records_cnt)
                )
            )
            fmt_time = format_seconds_to(
                self.total_seconds_spent + adjustment,
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
            self.missing_records_adj = f"±{fmt_time}"
        else:
            # no time records for this revision
            fmt_time = format_seconds_to(
                self.sum_repeated * (60 * self.total_cards / 12),
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
            self.missing_records_adj = f"±{fmt_time}"

        self.total_time_spent = self.create_stats_button(
            f"Spent\n{self.missing_records_adj}"
        )

        self.stat_table.addWidget(self.repeated_times_button, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev, 0, 1)
        self.stat_table.addWidget(self.days_from_creation, 0, 2)
        self.stat_table.addWidget(self.total_time_spent, 0, 3)

    def create_stats_button(self, text: str) -> QPushButton:
        new_button = QPushButton()
        new_button.setFont(config.qfont_stats)
        new_button.setText(text)
        new_button.setFocusPolicy(Qt.NoFocus)
        return new_button

    def get_data_for_current_revision(self, signature):
        db_conn.refresh()
        db_conn.filter_where_signature_is_equal_to(signature)
        self.chart_values = db_conn.get_chart_positives()
        self.chart_dates = db_conn.get_chart_dates()
        self.total_cards = db_conn.get_total_words()
        self.total_seconds_spent = db_conn.get_total_time_spent_for_signature()
        self.time_spent_seconds = db_conn.get_chart_time_spent()
        self.missing_records_cnt = db_conn.get_count_of_records_missing_time()
        self.time_spent_minutes = [
            datetime.fromtimestamp(x).strftime("%M:%S") for x in self.time_spent_seconds
        ]
        self.formatted_dates = [date.strftime("%d-%m\n%Y") for date in self.chart_dates]
        self.sum_repeated = db_conn.get_sum_repeated(db_conn.active_file.signature)
        self.days_ago = format_timedelta(
            db_conn.get_timedelta_from_creation(db_conn.active_file.signature)
        )
        self.last_rev_days_ago = format_timedelta(
            db_conn.get_timedelta_from_last_rev(db_conn.active_file.signature)
        )

        # Create Dynamic Chain Index
        if config["opt"]["show_percent_stats"]:
            self.create_dynamic_chain_percentages(tight_format=True)
        else:
            self.create_dynamic_chain_values(tight_format=True)
        db_conn.refresh()

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
