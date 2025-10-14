import logging
from datetime import date
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pandas as pd
from cfg import config
from DBAC import db_conn
from tracker.dal import dal

log = logging.getLogger("TRK")


class ProgressChartCanvas:

    def __init__(self):
        self.upd = -1
        self.upd_date = date.today()
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

    def get(self) -> FigureCanvas:
        return self.canvas

    def refresh(self):
        if self.upd < dal.upd or self.upd_date < date.today():
            self._calculate()
            self._generate()
            self.upd = dal.upd
            self.upd_date = date.today()

    def _calculate(self):
        db_conn.refresh()
        db_conn.filter_for_progress(config["languages"])
        df = db_conn.db

        df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
        mths = pd.date_range(
            pd.Timestamp(df["TIMESTAMP"].min()).normalize().replace(day=1),
            pd.Timestamp(date.today()).normalize().replace(day=1),
            freq="MS",
        ).strftime("%b\n%y")
        df["TIMESTAMP"] = df["TIMESTAMP"].dt.strftime("%b\n%y")

        counted = df["TIMESTAMP"].value_counts(sort=False).reindex(mths, fill_value=0)
        self.revision_count = counted.values

        df.drop_duplicates(["SIGNATURE", "TIMESTAMP"], inplace=True, keep="last")
        df.drop_duplicates("SIGNATURE", inplace=True, keep="first")
        grouped = df.groupby("TIMESTAMP", sort=False)

        self.formatted_dates = mths
        self.chart_values = grouped["POSITIVES"].sum().reindex(mths, fill_value=0)
        self.second_chart_values = grouped["TOTAL"].sum().reindex(mths, fill_value=0)

    def _generate(self):
        self.figure.clear()

        # initiate plots
        total_words_plot = self.figure.add_subplot()
        total_words_plot.bar(
            self.formatted_dates,
            self.second_chart_values,
            color=config.mpl["chart_secondary_color"],
            edgecolor=config.mpl["chart_edge_color"],
            linewidth=0.7,
            align="center",
            zorder=9,
        )

        positives_plot = total_words_plot.twinx()
        positives_plot.bar(
            self.formatted_dates,
            self.chart_values,
            color=config.mpl["stat_bar_color"],
            edgecolor=config.mpl["chart_edge_color"],
            linewidth=0.7,
            align="center",
            zorder=0,
        )

        revision_count_plot = total_words_plot.twinx()
        revision_count_plot.plot(
            self.formatted_dates,
            self.revision_count,
            color=config.mpl["chart_secondary_color"],
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
                color=config.mpl["stat_chart_text_color"],
                zorder=10,
                fontsize=config["theme"]["font_stats_size"],
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
                color=config.mpl["stat_chart_text_color"],
                zorder=10,
                fontsize=config["theme"]["font_stats_size"],
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
                color=config.mpl["stat_chart_text_color"],
                fontsize=config["theme"]["font_stats_size"],
            )

        # Style
        self.figure.set_facecolor(config.mpl["stat_background_color"])
        total_words_plot.set_facecolor(config.mpl["stat_chart_background_color"])
        total_words_plot.tick_params(
            colors=config.mpl["stat_chart_text_color"],
            labelsize=config["theme"]["font_stats_size"],
        )
        self.figure.tight_layout()
        positives_plot.get_yaxis().set_visible(False)
        revision_count_plot.get_yaxis().set_visible(False)
        positives_plot.get_xaxis().set_visible(False)
        title = " & ".join(config["languages"])
        self.figure.suptitle(title, fontsize=18, y=0.92, color=config.mpl["font_color"])
        self.figure.subplots_adjust(left=0, bottom=0.1, right=1, top=1)

        # synchronize axes
        max_ = max(self.chart_values.max(), self.second_chart_values.max())
        positives_plot.set_ylim([0, max_ * 1.2])
        total_words_plot.set_ylim([0, max_ * 1.2])
        revision_count_plot.set_ylim([0, max_ * 99])

        # Remove horizontal padding
        hpad_args = (-0.5, len(self.formatted_dates) - 0.5)
        total_words_plot.set_xlim(*hpad_args)
        positives_plot.set_xlim(*hpad_args)
        revision_count_plot.set_xlim(*hpad_args)
        total_words_plot.margins(x=0)

        self.canvas.draw()
