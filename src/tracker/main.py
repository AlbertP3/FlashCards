import logging
from PyQt5.QtWidgets import (
    QTabWidget,
    QGridLayout,
    QWidget,
)
from PyQt5.QtGui import QFont
from enum import Enum
from cfg import config
from tracker.prog import ProgressChartCanvas
from tracker.timechart import TimeChartCanvas
from tracker.timetable import TimeTablePrintout
from tracker.duo import DuoLayout
from tracker.stopwatch import StopwatchTab
from tracker.notes import NotesLayout
from tracker.dal import dal

log = logging.getLogger("TRK")


class TAB(Enum):
    TimeTable = "TimeTable"
    TimeChart = "TimeChart"
    Progress = "Progress"
    Duo = "Duo"
    StopWatch = "StopWatch"
    Notes = "Notes"


class TrackerSideWindow(QGridLayout):

    def __init__(self):
        super().__init__()
        self.__tabs = {}
        self.qfont = QFont(config["theme"]["font"], config["dim"]["font_button_size"])
        self.create_tabs()
        self.addWidget(self.tabs, 0, 0)
        self.on_tab_changed(self.tabs.currentIndex())

    def create_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(config["theme"]["ctx_stylesheet"])
        self.tabs.setFont(self.qfont)
        self.tabs.setContentsMargins(1, 1, 1, 1)

        self.add_tab(self.get_timetable_tab(), TAB.TimeTable.value)
        self.add_tab(self.get_timechart_tab(), TAB.TimeChart.value)
        self.add_tab(self.get_progress_tab(), TAB.Progress.value)
        if config["tracker"]["duo"]["active"]:
            self.add_tab(self.get_duo_tab(), TAB.Duo.value)
        self.add_tab(self.get_stopwatch_tab(), TAB.StopWatch.value)
        self.add_tab(self.get_notes_tab(), TAB.Notes.value)

        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setCurrentIndex(self.__tabs.get(dal.last_tab, 0))

    def add_tab(self, widget, text):
        self.tabs.addTab(widget, text)
        self.__tabs[text] = len(self.__tabs)

    def on_tab_changed(self, index: int):
        tid = self.tabs.tabText(index)
        if tid == TAB.TimeChart.value:
            self.ts_canvas.refresh()
        elif tid == TAB.Progress.value:
            self.prog_canvas.refresh()
        elif tid == TAB.TimeTable.value:
            self.tt_printout.refresh()
        elif tid == TAB.Duo.value:
            self.duo_layout.refresh()
        elif tid == TAB.StopWatch.value:
            self.stopwatch_layout.refresh()
        dal.last_tab = tid

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

    def get_duo_tab(self) -> QWidget:
        tab = QWidget()
        self.duo_layout = DuoLayout()
        tab.setLayout(self.duo_layout.get())
        return tab

    def get_stopwatch_tab(self) -> QWidget:
        tab = QWidget()
        self.stopwatch_layout = StopwatchTab()
        tab.setLayout(self.stopwatch_layout.get())
        return tab

    def get_notes_tab(self) -> QWidget:
        tab = QWidget()
        layout = self._create_layout()
        self.notes_layout = NotesLayout()
        layout.addWidget(self.notes_layout.get(), 0, 0)
        tab.setLayout(layout)
        return tab

    def _create_layout(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        return layout
