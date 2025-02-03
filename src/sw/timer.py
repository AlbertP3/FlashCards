from cfg import config

try:
    from tracker import TrackerSideWindow
except ImportError:
    pass


class TimerSideWindow:

    def __init__(self):
        self.side_window_titles["timer"] = "Tracker"
        self.timer_button = self.create_button(
            config["icons"]["timer_stop"], self.get_timer_sidewindow
        )
        self.layout_fourth_row.addWidget(self.timer_button, 3, 5)
        self.add_shortcut("timespent", self.get_timer_sidewindow, "main")

    def get_timer_sidewindow(self):
        return
        self.tracker_layout = TrackerSideWindow()
        self.open_side_window(self.tracker_layout, "timer")
