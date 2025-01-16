from PyQt5 import QtGui
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from utils import format_seconds_to, fcc_queue, LogLvl
from cfg import config
from stats import Stats


class StatsSideWindow(Stats):

    def __init__(self):
        self.side_window_titles["stats"] = "Statistics"
        Stats.__init__(self)
        self.stats_button = self.create_button(
            self.config["icons"]["stats"], self.get_stats_sidewindow
        )
        self.layout_fourth_row.addWidget(self.stats_button, 3, 1)
        self.init_shortcuts_stats()

    def init_shortcuts_stats(self):
        self.add_shortcut("stats", self.get_stats_sidewindow, "main")
        self.add_shortcut("efc", self.get_efc_sidewindow, "stats")
        self.add_shortcut("load", self.get_load_sidewindow, "stats")
        self.add_shortcut("progress", self.get_progress_sidewindow, "stats")
        self.add_shortcut("timespent", self.get_timer_sidewindow, "stats")
        self.add_shortcut("config", self.get_config_sidewindow, "stats")
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "stats")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "stats")
        self.add_shortcut("sod", self.get_sod_sidewindow, "stats")

    def get_stats_sidewindow(self):
        if self.active_file.kind == self.db.KINDS.rev:
            self.arrange_stats_sidewindow()
            self.open_side_window(self.stats_layout, "stats")
        else:
            fcc_queue.put_notification(
                f"Statistics are not available for a {self.db.KFN[self.active_file.kind]}",
                lvl=LogLvl.warn
            )

    def arrange_stats_sidewindow(self):
        self.get_data_for_current_revision(self.active_file.signature)
        self.get_stats_chart()
        self.get_stats_table()
        self.stats_layout = widget.QGridLayout()
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stats_layout.addLayout(self.stat_table, 1, 0)

    def get_stats_chart(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        rect = None

        ax = self.figure.add_subplot()
        ax.bar(
            self.formatted_dates,
            self.chart_values,
            color=config["theme"]["stat_bar_color"],
            edgecolor="#000000",
            linewidth=0.7,
            align="center",
        )

        # Time spent for each revision
        time_spent_plot = ax.twinx()
        time_spent_plot.plot(
            self.formatted_dates,
            self.time_spent_minutes,
            color="#979dac",
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
                color=self.config["theme"]["stat_chart_text_color"],
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # horizontal line at EFC predicate
        if rect and self.config["opt"]["show_efc_line"]:
            ax.axhline(
                y=self.total_cards * 0.8, color="#a0a0a0", linestyle="--", zorder=-3
            )
            ax.text(
                rect.get_x() + rect.get_width() / 1,
                self.total_cards * 0.8,
                f'{self.config["efc_threshold"]}%',
                va="bottom",
                color="#a0a0a0",
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # add labels - time spent
        if self.config["opt"]["show_cpm_stats"]:
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
                color=self.config["theme"]["stat_chart_text_color"],
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # Style
        self.figure.set_facecolor(self.config["theme"]["stat_background_color"])
        ax.set_facecolor(self.config["theme"]["stat_chart_background_color"])
        ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
        ax.set_ylim([0, self.total_cards + 2])
        ax.tick_params(
            colors=self.config["theme"]["stat_chart_text_color"],
            labelrotation=0,
            pad=1,
            labelsize=self.config["dim"]["font_stats_size"],
        )
        self.figure.tight_layout(pad=0.1)
        ax.get_yaxis().set_visible(False)
        time_spent_plot.get_yaxis().set_visible(False)
        time_spent_plot.set_ylim([0, 9999])
        self.figure.subplots_adjust(left=0.0, bottom=0.1, right=0.999, top=0.997)

        self.canvas.draw()

    def get_stats_table(self):
        self.stat_table = widget.QGridLayout()

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
                int_name=interval.capitalize(),
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
                int_name=interval.capitalize(),
                rem=rem,
                sep=":",
            )
            self.missing_records_adj = f"±{fmt_time}"
        else:
            # no time records for this revision
            fmt_time = format_seconds_to(
                self.sum_repeated * (60 * self.total_cards / 12),
                interval,
                int_name=interval.capitalize(),
                rem=rem,
                sep=":",
            )
            self.missing_records_adj = f"±{fmt_time}"

        self.total_time_spent = self.create_stats_button(f"Spent\n{self.missing_records_adj}")

        self.stat_table.addWidget(self.repeated_times_button, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev, 0, 1)
        self.stat_table.addWidget(self.days_from_creation, 0, 2)
        self.stat_table.addWidget(self.total_time_spent, 0, 3)

    def create_stats_button(self, text: str) -> widget.QPushButton:
        new_button = widget.QPushButton(self)
        new_button.setMinimumHeight(self.config["dim"]["stats_btn_height"])
        new_button.setFont(
            QtGui.QFont(
                self.config["theme"]["font"], self.config["dim"]["font_stats_size"]
            )
        )
        new_button.setText(text)
        new_button.setStyleSheet(self.config["theme"]["button_stylesheet"])
        new_button.setFocusPolicy(Qt.NoFocus)
        return new_button
