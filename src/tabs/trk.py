from PyQt5.QtWidgets import QWidget
from tracker import Tracker
from tracker.dal import dal
from tabs.base import BaseTab


class TrackerTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.id = "tracker"
        self.mw.tab_names[self.id] = "Tracker"
        self.build()
        self.mw.add_tab(self._tab, self.id)

    def open(self):
        self.mw.switch_tab(self.id)
        dal.get_data()
        self.trk.refresh_current_tab()

    def build(self):
        self._tab = QWidget()
        self.trk = Tracker()
        self._tab.setLayout(self.trk)
