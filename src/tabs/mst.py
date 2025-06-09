from PyQt5.QtWidgets import QFormLayout, QTableWidget, QHeaderView, QTableWidgetItem
from utils import fcc_queue, LogLvl
from tabs.base import BaseTab
from DBAC import db_conn
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI


class MistakesTab(BaseTab):

    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.mw = mw
        self.id = "mistakes"
        self.build()
        self.mw.add_tab(self.tab, self.id, "Mistakes")

    def open(self):
        if self.mw.active_file.kind in db_conn.GRADED:
            self.mw.switch_tab(self.id)
            self.show_mistakes()
        else:
            fcc_queue.put_notification(
                "Mistakes are unavailable for a Language", lvl=LogLvl.warn
            )

    def build(self):
        self.mistakes_layout = QFormLayout()
        self.mst_table = self.create_mistakes_table()
        self.mistakes_layout.addRow(self.mst_table)
        self.tab.setLayout(self.mistakes_layout)

    def show_mistakes(self):
        self.mst_table.setRowCount(len(self.mw.mistakes_list))
        self.mst_table.setHorizontalHeaderLabels(self.mw.active_file.data.columns)
        for i, row in enumerate(self.mw.mistakes_list):
            for c, v in enumerate(row):
                self.mst_table.setItem(i, c, QTableWidgetItem(str(v)))

    def create_mistakes_table(self):
        table = QTableWidget()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setColumnCount(2)
        return table
