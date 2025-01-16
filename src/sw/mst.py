import PyQt5.QtWidgets as widget
from utils import fcc_queue, LogLvl


class MistakesSideWindow:

    def __init__(self):
        self.side_window_titles["mistakes"] = "Mistakes"
        self.score_button.clicked.connect(self.get_mistakes_sidewindow)
        self.init_shortcuts_mistakes()

    def init_shortcuts_mistakes(self):
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "main")
        self.add_shortcut("efc", self.get_efc_sidewindow, "mistakes")
        self.add_shortcut("load", self.get_load_sidewindow, "mistakes")
        self.add_shortcut("progress", self.get_progress_sidewindow, "mistakes")
        self.add_shortcut("timespent", self.get_timer_sidewindow, "mistakes")
        self.add_shortcut("config", self.get_config_sidewindow, "mistakes")
        self.add_shortcut("stats", self.get_stats_sidewindow, "mistakes")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "mistakes")
        self.add_shortcut("sod", self.get_sod_sidewindow, "mistakes")

    def get_mistakes_sidewindow(self):
        if self.active_file.kind in self.db.GRADED:
            self.arrange_mistakes_window()
            self.open_side_window(self.mistakes_layout, "mistakes")
            self.show_mistakes()
        else:
            fcc_queue.put_notification(
                "Mistakes are unavailable for a Language", lvl=LogLvl.warn
            )

    def arrange_mistakes_window(self):
        self.textbox_stylesheet = self.config["theme"]["textbox_stylesheet"]
        self.button_stylesheet = self.config["theme"]["button_stylesheet"]
        self.mistakes_layout = widget.QGridLayout()
        self.mistakes_layout.addWidget(self.create_mistakes_list(), 0, 0)

    def show_mistakes(self):
        out, sep = list(), " | "
        cell_args = {
            "pixlim": (self.config.get_geo("mistakes")[0] - self.caliper.strwidth(sep))
            / 2,
            "align": self.config["cell_alignment"],
        }
        for m in self.mistakes_list:
            m1 = self.caliper.make_cell(m[self.default_side], **cell_args)
            m2 = self.caliper.make_cell(m[1 - self.default_side], **cell_args)
            out.append(f"{m1}{sep}{m2}")
        self.mistakes_qtext.setText("\n".join(out))

    def create_mistakes_list(self):
        self.mistakes_qtext = widget.QTextEdit(self)
        self.mistakes_qtext.setFont(self.CONSOLE_FONT)
        self.mistakes_qtext.setReadOnly(True)
        self.mistakes_qtext.setStyleSheet(self.textbox_stylesheet)
        return self.mistakes_qtext
