from PyQt5.QtWidgets import QWidget
from tracker import Tracker
from tracker.dal import dal
from sw.base import BaseTab


class TrackerTab(BaseTab):

    def __init__(self, mw):
        self.mw = mw
        self.id = "tracker"
        self.mw.tab_names[self.id] = "Tracker"
        self.mw.add_shortcut(self.id, self.open, "main")
        self.build()
        self.mw.add_tab(self._tab, self.id)

    def open(self):
        self.mw.switch_tab(self.id)
        dal.get_data()
        self.tracker_layout.refresh_current_tab()

    def build(self):
        self._tab = QWidget()
        self.tracker_layout = Tracker()
        self._tab.setLayout(self.tracker_layout)
