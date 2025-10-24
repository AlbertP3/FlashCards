import logging
from dataclasses import asdict
from datetime import datetime
from PyQt5.QtWidgets import QGridLayout, QPushButton
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from cfg import config
from utils import format_seconds_to, format_timedelta, get_sign
from int import fcc_queue, LogLvl
from DBAC import db_conn
from tabs.base import BaseTab
from typing import TYPE_CHECKING
from data_types import StatChartData

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
            if self.cache_valid:
                self._set_stat_btns_texts()
            else:
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
            self.get_data(self.mw.active_file.signature)
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
        x_ticks = list(range(len(self._data.dates_fmtd)))

        ax = self.figure.add_subplot()
        ax.bar(
            x_ticks,
            self._data.positives,
            color=config.mpl["stat_bar_color"],
            edgecolor=config.mpl["chart_edge_color"],
            linewidth=0.7,
            align="center",
        )

        # Time spent for each revision
        time_spent_plot = ax.twinx()
        time_spent_plot.plot(
            x_ticks,
            self._data.time_spent_minutes_fmtd,
            color=config.mpl["chart_secondary_color"],
            linewidth=1,
            zorder=9,
        )

        # Labels
        for rect, label in zip(ax.patches, self._data.dynamic_chain_index):
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

        # Horizontal line at EFC predicate
        if rect and config["opt"]["show_efc_line"]:
            ax.axhline(
                y=self._data.total_cards * 0.8,
                color=config.mpl["chart_line_color"],
                linestyle="--",
                zorder=-3,
            )
            ax.text(
                rect.get_x() + rect.get_width() / 1,
                self._data.total_cards * 0.8,
                f'{config["efc"]["threshold"]}%',
                va="bottom",
                color=config.mpl["chart_line_color"],
                fontsize=config["theme"]["font_stats_size"],
            )

        # Add labels - time spent
        if config["opt"]["show_cpm_stats"]:
            time_spent_labels = [
                "{:.0f}".format(self._data.total_cards / (x / 60)) if x else "-"
                for x in self._data.time_spent_seconds
            ]
        else:
            time_spent_labels = self._data.time_spent_minutes_fmtd
        for x, y in zip(x_ticks, time_spent_labels):
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
        ax.set_ylim((0, self._data.total_cards + 2))
        ax.set_xlim(-0.5, abs(len(x_ticks) - 0.5))
        ax.set_xticks(x_ticks, self._data.dates_fmtd)
        ax.tick_params(
            colors=config.mpl["stat_chart_text_color"],
            labelrotation=0,
            pad=1,
            labelsize=config["theme"]["font_stats_size"],
        )
        self.figure.tight_layout(pad=0.1)
        ax.get_yaxis().set_visible(False)
        time_spent_plot.get_yaxis().set_visible(False)
        time_spent_plot.set_ylim((0, 9999))
        self.figure.subplots_adjust(left=0.0, bottom=0.1, right=0.999, top=0.997)

        self.canvas.draw()

    def get_stats_table(self):
        self.repeated_times_btn = self.create_stats_button()
        self.days_from_last_rev_btn = self.create_stats_button()
        self.days_from_creation_btn = self.create_stats_button()
        self._set_stat_btns_texts()

        # estimate total time spent if some records miss time_spent
        interval, rem = (("minute", 0), ("hour", 2))[
            self._data.sum_seconds_spent > 3600
        ]
        if self._data.missing_records_cnt == 0:
            missing_records_adj = format_seconds_to(
                self._data.sum_seconds_spent,
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
        elif self._data.sum_seconds_spent != 0:
            # estimate total time by adding to actual total_seconds_spent,
            # the estimate = X * count of missing records multiplied by average time spent on non-zero revision
            # X is an arbitrary number to adjust for learning curve
            adjustment = (
                1.481
                * self._data.missing_records_cnt
                * (
                    self._data.sum_seconds_spent
                    / (self.sum_repeated - self._data.missing_records_cnt)
                )
            )
            fmt_time = format_seconds_to(
                self._data.sum_seconds_spent + adjustment,
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
            missing_records_adj = f"±{fmt_time}"
        else:
            # no time records for this revision
            fmt_time = format_seconds_to(
                self.sum_repeated * (60 * self._data.total_cards / 12),
                interval,
                interval_name=interval,
                rem=rem,
                sep=":",
            )
            missing_records_adj = f"±{fmt_time}"

        self.total_time_spent_btn = self.create_stats_button(
            f"Spent\n{missing_records_adj}"
        )

        self.stat_table.addWidget(self.repeated_times_btn, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev_btn, 0, 1)
        self.stat_table.addWidget(self.days_from_creation_btn, 0, 2)
        self.stat_table.addWidget(self.total_time_spent_btn, 0, 3)

    def _set_stat_btns_texts(self):
        self.repeated_times_btn.setText(
            f'Repeated\n{self._data.sum_repeated} time{"s" if self._data.sum_repeated > 1 else ""}'
        )
        last_rev_diff_fmtd = format_timedelta(datetime.now() - self._data.last_rev_date)
        self.days_from_last_rev_btn.setText(
            f'Last Revision\n{str(last_rev_diff_fmtd).split(",")[0]} ago'
        )
        created_days_ago_diff_fmtd = format_timedelta(datetime.now() - self._data.creation_date)
        self.days_from_creation_btn.setText(
            f'Created\n{str(created_days_ago_diff_fmtd).split(",")[0]} ago'
        )

    def create_stats_button(self, text: str = "") -> QPushButton:
        new_button = QPushButton()
        new_button.setFont(config.qfont_stats)
        new_button.setText(text)
        new_button.setFocusPolicy(Qt.NoFocus)
        return new_button

    def get_data(self, signature: str):
        db_conn.refresh()
        data = db_conn.get_stat_chart_data(signature)
        self._data = StatChartData(
            **asdict(data),
            time_spent_minutes_fmtd=[
                datetime.fromtimestamp(x).strftime("%M:%S")
                for x in data.time_spent_seconds
            ],
            dates_fmtd=[date.strftime("%d-%m\n%Y") for date in data.dates],
        )
        if config["opt"]["show_percent_stats"]:
            self.create_dynamic_chain_percentages(self._data, use_tight_format=True)
        else:
            self.create_dynamic_chain_values(self._data, use_tight_format=True)

    def create_dynamic_chain_values(
        self, data: StatChartData, use_tight_format: bool = True
    ) -> None:
        tight_format = "\n" if use_tight_format else " "
        dynamic_chain_index = [
            str(data.positives[0]) if len(data.positives) >= 1 else ""
        ]
        [
            dynamic_chain_index.append(
                "{main_val}{tf}({sign_}{dynamic})".format(
                    main_val=data.positives[x],
                    tf=tight_format,
                    sign_=get_sign(
                        data.positives[x] - data.positives[x - 1], neg_sign=""
                    ),
                    dynamic=data.positives[x] - data.positives[x - 1],
                )
            )
            for x in range(1, len(data.positives))
        ]
        data.dynamic_chain_index = dynamic_chain_index

    def create_dynamic_chain_percentages(
        self, data: StatChartData, use_tight_format: bool = True
    ) -> None:
        tight_format = "\n" if use_tight_format else " "
        dynamic_chain_index = [
            (
                "{:.0%}".format(data.positives[0] / data.total_cards)
                if len(data.positives) >= 1
                else ""
            )
        ]
        [
            dynamic_chain_index.append(
                "{main_val:.0%}{tf}{sign_}{dynamic:.0f}pp".format(
                    main_val=data.positives[x] / data.total_cards,
                    tf=tight_format,
                    sign_=get_sign(
                        data.positives[x] - data.positives[x - 1], neg_sign=""
                    ),
                    dynamic=100
                    * (data.positives[x] - data.positives[x - 1])
                    / data.total_cards,
                )
            )
            for x in range(1, len(data.positives))
        ]
        data.dynamic_chain_index = dynamic_chain_index
