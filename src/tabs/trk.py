from PyQt5.QtWidgets import QWidget
from tracker import Tracker
from tracker.dal import dal
from tabs.base import BaseTab
from PyQt5.QtCore import Qt


class TrackerTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.id = "tracker"
        self.build()
        self.mw.add_tab(self._tab, self.id, "Tracker")

    def init_cross_shortcuts(self):
        super().init_cross_shortcuts()
        self.mw.add_ks(
            Qt.Key_PageDown,
            lambda: self.trk.switch_tab(1),
            self.trk.trk_tabs,
        )
        self.mw.add_ks(
            Qt.Key_PageUp,
            lambda: self.trk.switch_tab(-1),
            self.trk.trk_tabs,
        )

    def open(self):
        self.mw.switch_tab(self.id)
        dal.get_data()
        self.trk.refresh_current_tab()

    def build(self):
        self._tab = QWidget()
        self.trk = Tracker()
        self._tab.setLayout(self.trk)
