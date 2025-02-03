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

log = logging.getLogger("GUI")


class TAB(Enum):
    TimeTable = 0
    TimeChart = 1
    Progress = 2
    Duo = 3
    StopWatch = 4
    Notes = 5

    def get(tab_name: str, default: int = 0):
        try:
            return TAB[tab_name].value
        except KeyError:
            return default


class TrackerSideWindow(QGridLayout):

    def __init__(self):
        super().__init__()
        self.qfont = QFont(config["theme"]["font"], config["dim"]["font_button_size"])
        self.create_tabs()
        dal.reset_monitor()
        self.addWidget(self.tabs, 0, 0)
        self.on_tab_changed(self.tabs.currentIndex())

    def create_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(config["theme"]["ctx_stylesheet"])
        self.tabs.setFont(self.qfont)
        self.tabs.setContentsMargins(1, 1, 1, 1)

        self.tabs.addTab(self.get_timetable_tab(), TAB.TimeTable.name)
        self.tabs.addTab(self.get_timechart_tab(), TAB.TimeChart.name)
        self.tabs.addTab(self.get_progress_tab(), TAB.Progress.name)
        self.tabs.addTab(self.get_duo_tab(), TAB.Duo.name)
        self.tabs.addTab(self.get_stopwatch_tab(), TAB.StopWatch.name)
        self.tabs.addTab(self.get_notes_tab(), TAB.Notes.name)

        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.tabs.setCurrentIndex(TAB.get(config["tracker"]["initial_tab"]))

    def on_tab_changed(self, index: int):
        tid = self.tabs.tabText(index)
        if tid == TAB.TimeChart.name:
            self.ts_canvas.refresh()
        elif tid == TAB.Progress.name:
            self.prog_canvas.refresh()
        elif tid == TAB.TimeTable.name:
            self.tt_printout.refresh()
        elif tid == TAB.Duo.name:
            self.duo_layout.refresh()
        elif tid == TAB.StopWatch.name:
            self.stopwatch_layout.refresh()

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
