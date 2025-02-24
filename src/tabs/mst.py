from PyQt5.QtWidgets import QGridLayout, QTextEdit
from PyQt5.QtCore import Qt
from utils import fcc_queue, LogLvl, Caliper
from cfg import config
from tabs.base import BaseTab
from DBAC import db_conn


class MistakesTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.id = "mistakes"
        self.mw.tab_names[self.id] = "Mistakes"
        self.caliper = Caliper(config.qfont_console)
        self.build()
        self.mw.add_tab(self.mistakes_qtext, self.id)

    def open(self):
        if self.mw.active_file.kind in db_conn.GRADED:
            self.mw.switch_tab(self.id)
            self.show_mistakes()
        else:
            fcc_queue.put_notification(
                "Mistakes are unavailable for a Language", lvl=LogLvl.warn
            )

    def build(self):
        self.mistakes_layout = QGridLayout()
        self.mistakes_layout.addWidget(self.create_mistakes_list(), 0, 0)

    def show_mistakes(self):
        out, sep = list(), " | "
        cell_args = {
            "pixlim": (config["geo"][0] - self.caliper.strwidth(sep))
            // 2.02,
            "align": config["cell_alignment"],
        }
        for m in self.mw.mistakes_list:
            m1 = self.caliper.make_cell(m[self.mw.default_side], **cell_args)
            m2 = self.caliper.make_cell(m[1 - self.mw.default_side], **cell_args)
            out.append(f"{m1}{sep}{m2}")
        self.mistakes_qtext.setText("\n".join(out))

    def create_mistakes_list(self):
        self.mistakes_qtext = QTextEdit()
        self.mistakes_qtext.setFont(config.qfont_console)
        self.mistakes_qtext.setReadOnly(True)
        self.mistakes_qtext.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return self.mistakes_qtext
