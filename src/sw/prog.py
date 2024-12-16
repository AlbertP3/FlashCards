import logging
import PyQt5.QtWidgets as widget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from utils import fcc_queue
from cfg import config
from stats import Stats

log = logging.getLogger("GUI")


class ProgressSideWindow(Stats):

    def __init__(self):
        Stats.__init__(self)
        self.side_window_titles["progress"] = "Progress"
        self.progress_button = self.create_button(
            self.config["icons"]["progress"], self.get_progress_sidewindow
        )
        self.layout_fourth_row.addWidget(self.progress_button, 3, 2)
        self.init_shortcuts_progress()

    def init_shortcuts_progress(self):
        self.add_shortcut("progress", self.get_progress_sidewindow, "main")
        self.add_shortcut("stats", self.get_stats_sidewindow, "progress")
        self.add_shortcut("efc", self.get_efc_sidewindow, "progress")
        self.add_shortcut("load", self.get_load_sidewindow, "progress")
        self.add_shortcut("timespent", self.get_timer_sidewindow, "progress")
        self.add_shortcut("config", self.get_config_sidewindow, "progress")
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "progress")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "progress")
        self.add_shortcut("sod", self.get_sod_sidewindow, "progress")

    def get_progress_sidewindow(self, lngs: set = None):
        try:
            self.arrange_progress_sidewindow(lngs or self.config["languages"])
            self.open_side_window(self.progress_layout, "progress")
        except ValueError as e:
            fcc_queue.put("No data found for Progress", importance=30)
            log.error(e, exc_info=True)

    def arrange_progress_sidewindow(self, lngs: set):
        self.get_data_for_progress(lngs)
        self.get_progress_chart(lngs)
        self.progress_layout = widget.QGridLayout()
        self.progress_layout.addWidget(self.canvas, 0, 0)

    def get_progress_chart(self, lngs: set):

        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

        # initiate plots
        total_words_plot = self.figure.add_subplot()
        total_words_plot.bar(
            self.formatted_dates,
            self.second_chart_values,
            color="#979dac",
            edgecolor="#000000",
            linewidth=0.7,
            align="center",
            zorder=9,
        )

        positives_plot = total_words_plot.twinx()
        positives_plot.bar(
            self.formatted_dates,
            self.chart_values,
            color=config["theme"]["stat_bar_color"],
            edgecolor="#000000",
            linewidth=0.7,
            align="center",
            zorder=0,
        )

        revision_count_plot = total_words_plot.twinx()
        revision_count_plot.plot(
            self.formatted_dates,
            self.revision_count,
            color="#979dac",
            linewidth=1,
            zorder=9,
        )

        # add labels - last positives sum
        for rect, label in zip(positives_plot.patches, self.chart_values):
            height = rect.get_height()
            label = "" if label == 0 else "{:.0f}".format(label)
            positives_plot.text(
                rect.get_x() + rect.get_width() / 2,
                height / 2,
                label,
                ha="center",
                va="bottom",
                color=self.config["theme"]["stat_chart_text_color"],
                zorder=10,
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # add labels - total sum
        unlearned = self.second_chart_values - self.chart_values
        for rect, label in zip(total_words_plot.patches, unlearned):
            height = rect.get_height()
            x = rect.get_x() + rect.get_width() / 2
            y = height - label / 1.25
            label = "" if label == 0 else "{:.0f}".format(label)
            total_words_plot.text(
                x,
                y,
                label,
                ha="center",
                va="bottom",
                color=self.config["theme"]["stat_chart_text_color"],
                zorder=10,
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # add labels - repeated times
        for x, y in zip(self.formatted_dates, self.revision_count):
            # xytext - distance between points and text label
            revision_count_plot.annotate(
                "#{:.0f}".format(y),
                (x, y),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                color=self.config["theme"]["stat_chart_text_color"],
                fontsize=self.config["dim"]["font_stats_size"],
            )

        # Style
        self.figure.set_facecolor(self.config["theme"]["stat_background_color"])
        total_words_plot.set_facecolor(
            self.config["theme"]["stat_chart_background_color"]
        )
        positives_plot.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
        total_words_plot.tick_params(
            colors=self.config["theme"]["stat_chart_text_color"],
            labelsize=self.config["dim"]["font_stats_size"],
        )
        self.figure.tight_layout(pad=0.1)
        positives_plot.get_yaxis().set_visible(False)
        revision_count_plot.get_yaxis().set_visible(False)
        positives_plot.get_xaxis().set_visible(False)
        title = " & ".join(lngs) if lngs else "All"
        self.figure.suptitle(
            title, fontsize=18, y=0.92, color=self.config["theme"]["font_color"]
        )
        self.figure.subplots_adjust(left=0.0, bottom=0.06, right=0.997, top=0.997)

        # synchronize axes
        max_ = max(self.chart_values.max(), self.second_chart_values.max())
        positives_plot.set_ylim([0, max_ * 1.2])
        total_words_plot.set_ylim([0, max_ * 1.2])
        revision_count_plot.set_ylim([0, max_ * 99])

        self.canvas.draw()
