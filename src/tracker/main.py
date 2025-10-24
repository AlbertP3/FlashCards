import logging
from typing import Callable, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QTabWidget,
    QGridLayout,
    QWidget,
)
from typing import NamedTuple
from cfg import config
from tracker.prog import ProgressChartCanvas
from tracker.timechart import TimeChartCanvas
from tracker.timetable import TimeTablePrintout
from tracker.daily import DailyLayout
from tracker.stopwatch import StopwatchTab
from tracker.notes import NotesLayout

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("TRK")


class TAB(NamedTuple):
    TimeTable = "TimeTable"
    TimeChart = "TimeChart"
    Progress = "Progress"
    Daily = "Daily"
    StopWatch = "StopWatch"
    Notes = "Notes"


class Tracker(QGridLayout):

    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.mw = mw
        self.trk_tab_map = {}
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(1)
        self.create_tabs()
        self.addWidget(self.trk_tabs, 0, 0)
        self.on_tab_changed(self.trk_tabs.currentIndex())

    def create_tabs(self):
        self.trk_tabs = QTabWidget()
        self.trk_tabs.setFont(config.qfont_button)
        self.trk_tabs.setContentsMargins(1, 1, 1, 1)

        self.add_tab(
            self.get_timetable_tab(), TAB.TimeTable, self.tt_printout.refresh
        )
        self.add_tab(
            self.get_timechart_tab(), TAB.TimeChart, self.ts_canvas.refresh
        )
        self.add_tab(
            self.get_progress_tab(), TAB.Progress, self.prog_canvas.refresh
        )
        self.add_tab(self.get_daily_tab(), TAB.Daily, self.daily_layout.refresh)
        self.add_tab(
            self.get_stopwatch_tab(), TAB.StopWatch, self.stopwatch_layout.refresh
        )
        self.add_tab(
            self.get_notes_tab(), TAB.Notes, self.notes_layout.qTextEdit.setFocus
        )

        self.trk_tabs.currentChanged.connect(self.on_tab_changed)
        self.trk_tabs.setCurrentIndex(
            self.trk_tab_map.get(config["tracker"]["initial_tab"], 0)["idx"]
        )

    def add_tab(self, widget, text, on_refresh: Callable):
        self.trk_tabs.addTab(widget, text)
        self.trk_tab_map[text] = {"idx": len(self.trk_tab_map), "fn": on_refresh}

    def invalidate_tabs(self):
        self.prog_canvas.upd = -1
        self.ts_canvas.upd = -1
        self.tt_printout.upd = -1
        self.daily_layout.upd = -1
        self.stopwatch_layout.upd = -1
        self.notes_layout.upd = -1

    def refresh_current_tab(self):
        ci = self.trk_tabs.currentIndex()
        self.on_tab_changed(ci)

    def switch_tab(self, move: int):
        new_index = self.trk_tabs.currentIndex() + move
        cnt = self.trk_tabs.count()
        if new_index >= cnt:
            new_index = 0
        elif new_index < 0:
            new_index = cnt - 1
        self.trk_tabs.setCurrentIndex(new_index)

    def on_tab_changed(self, index: int):
        tid = self.trk_tabs.tabText(index)
        self.trk_tab_map[tid]["fn"]()
        config["tracker"]["initial_tab"] = tid

    def get_progress_tab(self) -> QWidget:
        tab = QWidget()
        layout = self._create_layout()
        self.prog_canvas = ProgressChartCanvas()
        layout.addWidget(self.prog_canvas.get(), 0, 0)
        tab.setLayout(layout)
        return tab

    def get_timechart_tab(self) -> QWidget:
        tab = QWidget()
        layout = self._create_layout()
        self.ts_canvas = TimeChartCanvas()
        layout.addWidget(self.ts_canvas.get(), 0, 0)
        tab.setLayout(layout)
        return tab

    def get_timetable_tab(self) -> QWidget:
        tab = QWidget()
        layout = self._create_layout()
        self.tt_printout = TimeTablePrintout()
        layout.addWidget(self.tt_printout.get(), 0, 0)
        tab.setLayout(layout)
        return tab

    def get_daily_tab(self) -> QWidget:
        tab = QWidget()
        self.daily_layout = DailyLayout()
        tab.setLayout(self.daily_layout.get())
        return tab

    def get_stopwatch_tab(self) -> QWidget:
        tab = QWidget()
        self.stopwatch_layout = StopwatchTab(mw=self.mw)
        tab.setLayout(self.stopwatch_layout.get())
        return tab

    def get_notes_tab(self) -> QWidget:
        tab = QWidget()
        layout = self._create_layout()
        self.notes_layout = NotesLayout(trk=self)
        layout.addWidget(self.notes_layout.get(), 0, 0)
        tab.setLayout(layout)
        return tab

    def _create_layout(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        return layout
