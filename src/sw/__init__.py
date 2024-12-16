from sw.fcc import FccSideWindow
from sw.efc import EFCSideWindow
from sw.load import LoadSideWindow
from sw.mst import MistakesSideWindow
from sw.stats import StatsSideWindow
from sw.prog import ProgressSideWindow
from sw.cfg import ConfigSideWindow
from sw.timer import TimerSideWindow


class SideWindows(
    FccSideWindow,
    EFCSideWindow,
    LoadSideWindow,
    MistakesSideWindow,
    StatsSideWindow,
    ProgressSideWindow,
    ConfigSideWindow,
    TimerSideWindow,
):
    def __init__(self):
        self.side_window_titles = dict()
        FccSideWindow.__init__(self)
        EFCSideWindow.__init__(self)
        LoadSideWindow.__init__(self)
        MistakesSideWindow.__init__(self)
        StatsSideWindow.__init__(self)
        ProgressSideWindow.__init__(self)
        ConfigSideWindow.__init__(self)
        TimerSideWindow.__init__(self)

    def __del__(self):
        del self
