import logging
from utils import fcc_queue, LogLvl

log = logging.getLogger("GUI")


class ProgressSideWindow:

    def __init__(self):
        self.side_window_titles["progress"] = "Progress"
        self.progress_button = self.create_button(
            self.config["icons"]["progress"], self.get_progress_sidewindow
        )
        self.layout_fourth_row.addWidget(self.progress_button, 3, 2)
        self.init_shortcuts_progress()

    def init_shortcuts_progress(self):
        self.add_shortcut("progress", self.get_progress_sidewindow, "main")

    def get_progress_sidewindow(self, lngs: set = None):
        fcc_queue.put_notification("Progress moved to Tracker", lvl=LogLvl.important)
