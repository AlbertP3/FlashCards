import timer
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from cfg import config


class TimerSideWindow:

    def __init__(self):
        self.config = config
        self.side_window_titles["timer"] = "Time Spent"
        self.data_getter = timer.Timespent_BE()
        self.TIMER_FONT_SIZE = 12
        self.timer_button = self.create_button(
            self.config["icons"]["timer"], self.get_timer_sidewindow
        )
        self.layout_fourth_row.addWidget(self.timer_button, 3, 5)
        self.TIMER_FONT = QtGui.QFont("Consolas", self.TIMER_FONT_SIZE)
        self.init_shortcuts_timer()

    def init_shortcuts_timer(self):
        self.add_shortcut("timespent", self.get_timer_sidewindow, "main")
        self.add_shortcut("progress", self.get_progress_sidewindow, "timer")
        self.add_shortcut("stats", self.get_stats_sidewindow, "timer")
        self.add_shortcut("efc", self.get_efc_sidewindow, "timer")
        self.add_shortcut("load", self.get_load_sidewindow, "timer")
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "timer")
        self.add_shortcut("config", self.get_config_sidewindow, "timer")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "timer")
        self.add_shortcut("sod", self.get_sod_sidewindow, "timer")

    def get_timer_sidewindow(self):
        self.create_timer_console()
        self.arrange_timer_sidewindow()
        self.show_data()
        self.open_side_window(self.timer_layout, "timer")

    def arrange_timer_sidewindow(self, width_=500):
        self.timer_layout = widget.QGridLayout()
        self.timer_layout.addWidget(self.timer_console, 0, 0)

    def create_timer_console(self):
        self.timer_console = widget.QTextEdit(self)
        self.timer_console.setFont(self.TIMER_FONT)
        self.timer_console.setStyleSheet(self.textbox_stylesheet)
        self.timer_console.setReadOnly(True)

    def show_data(self):
        last_n = self.config["timespent_len"]
        interval = "m"
        res = self.data_getter.get_timespent_printout(last_n, interval)
        self.timer_console.setText(res)
