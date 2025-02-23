from sw.fcc import FccTab
from sw.efc import EFCTab
from sw.load import LoadTab
from sw.mst import MistakesTab
from sw.stats import StatsTab
from sw.cfg import CfgTab
from sw.trk import TrackerTab
from sw.logs import LogsTab
from sw.sod import SodTab


class Tabs:
    def __init__(self, mw):
        self.tab_names = dict()

        self.fcc = FccTab(mw)
        self.sod = SodTab(mw)
        self.efc = EFCTab(mw)
        self.ldt = LoadTab(mw)
        self.mst = MistakesTab(mw)
        self.sta = StatsTab(mw)
        self.cft = CfgTab(mw)
        self.trk = TrackerTab(mw)
        self.log = LogsTab(mw)

        self.efc.init_cross_shortcuts()
        self.ldt.init_cross_shortcuts()
        self.mst.init_cross_shortcuts()
        self.sta.init_cross_shortcuts()
        self.cft.init_cross_shortcuts()
        self.trk.init_cross_shortcuts()
        self.log.init_cross_shortcuts()
