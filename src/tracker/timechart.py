import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from cfg import config
from tracker.dal import dal
from tracker.helpers import merge_records_by_date

log = logging.getLogger("GUI")


class TimeChartCanvas:

    def __init__(self):
        self.upd = -1
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)

    def get(self) -> FigureCanvas:
        return self.canvas

    def refresh(self):
        if self.upd < dal.upd:
            self._calculate()
            self._generate()
            self.upd = dal.upd
    
    def _calculate(self):
        data = dal.get_data()
        data = merge_records_by_date(data, "%b\n%y")
        self.formatted_dates = list(data.keys())
        self.chart_values = [r.total_hours for r in data.values()]
        self.timespent_hours = [f"{round(r.total_hours):.0f}" for r in data.values()]

    def _generate(self):
        ax = self.figure.add_subplot()
        ax.bar(
            self.formatted_dates,
            self.chart_values,
            color=config["theme"]["stat_bar_color"],
            edgecolor="#000000",
            linewidth=0.7,
            align="center",
        )

        for rect, label in zip(ax.patches, self.timespent_hours):
            height = rect.get_height()
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                height / 2,
                label,
                ha="center",
                va="bottom",
                color=config["theme"]["stat_chart_text_color"],
                fontsize=config["dim"]["font_stats_size"],
            )

        # Style
        self.figure.set_facecolor(config["theme"]["stat_background_color"])
        ax.set_facecolor(config["theme"]["stat_chart_background_color"])
        ax.set_ylim([0, max(self.chart_values) * 1.2])
        ax.tick_params(
            colors=config["theme"]["stat_chart_text_color"],
            labelrotation=0,
            pad=1,
            labelsize=config["dim"]["font_stats_size"],
        )
        self.figure.tight_layout()
        ax.get_yaxis().set_visible(False)
        self.figure.subplots_adjust(left=0, bottom=0.08, right=1, top=1)

        self.canvas.draw()
