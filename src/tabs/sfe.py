from PyQt5.QtWidgets import (
    QVBoxLayout,
    QLineEdit,
    QTableView,
    QHBoxLayout,
    QDialog,
    QHeaderView,
    QAbstractItemView,
    QApplication,
)
from PyQt5.QtCore import QTimer, Qt
import logging
from tabs.base import BaseTab
from DBAC import db_conn, FileDescriptor
from sfe.datatable import DataTableModel
from widgets import AddCardDialog, get_button, CheckableComboBox, ConfirmDeleteDialog
from cfg import config
from utils import fcc_queue, LogLvl
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("SFE")


class SfeTab(BaseTab):
    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.id = "sfe"
        self.mw = mw
        self.__last_auto_pasted = ""
        self.build()
        self.mw.add_tab(self.tab, self.id, "Source File Editor")

    def init_cross_shortcuts(self):
        super().init_cross_shortcuts()
        self.mw.add_ks(config["kbsc"]["sfe_search"], self.search_qle.setFocus, self.tab)
        self.mw.add_ks(config["kbsc"]["sfe_add"], self.on_add, self.tab)
        self.mw.add_ks(config["kbsc"]["sfe_save"], self.on_save, self.tab)
        self.mw.add_ks("Home", lambda: self.scroll(0), self.tab)
        self.mw.add_ks("End", lambda: self.scroll(self.model.rowCount() - 1), self.tab)
        self.mw.add_ks("Delete", self.on_delete, self.tab)
        self.mw.add_ks("F2", self.edit_row, self.tab)

    def open(self):
        self.mw.switch_tab(self.id)
        self.view.setFocus()
        self.tab.focus_in()

    def build(self):
        self.tab.set_exit(self.exit)
        self.tab.set_focus_in(self.on_focus_in)
        self.model = DataTableModel(config["sfe"]["last_file"])
        self.model.fh.mod_signal.connect(lambda x: self.save_btn.setDisabled(x))
        self.sfe_layout = QVBoxLayout(self)
        self.sfe_layout.setContentsMargins(1, 1, 1, 1)
        self.sfe_layout.setSpacing(1)
        self._create_search_layout()
        self._create_table_view()
        self.sfe_layout.addLayout(self.search_layout)
        self.sfe_layout.addWidget(self.view)
        self.tab.setLayout(self.sfe_layout)
        self.scroll(self.model.rowCount() - 1)

    def exit(self) -> bool:
        if self.search_qle.hasFocus():
            self.view.setFocus()
            return True
        return False

    def _create_search_layout(self):
        self.add_btn = get_button(self.tab, text="Add", function=self.on_add)
        self.del_btn = get_button(self.tab, text="Delete", function=self.on_delete)
        self.reload_btn = get_button(
            self.tab, text=config["icons"]["again"], function=self.on_reload
        )
        self.save_btn = get_button(self.tab, text="Save", function=self.on_save)
        self.save_btn.setDisabled(True)
        if config["sfe"]["autosave"]:
            self.save_btn.setVisible(False)
            self.reload_btn.setVisible(False)
        self.iln_btn = get_button(
            self.tab,
            function=lambda: self.mw.ldt.create_from_iln(
                db_conn.files[self.model.fh.filepath]
            ),
        )
        self.set_iln_button()
        self.src_cbx = CheckableComboBox(
            self,
            allow_multichoice=False,
            width=200,
            hide_on_checked=True,
            on_popup_show=self._update_sources,
        )

        self.src_cbx.setMinimumWidth(200)
        self.src_cbx.setFont(config.qfont_button)
        self._update_sources()
        self.src_cbx.model().dataChanged.connect(
            lambda: QTimer.singleShot(0, self.on_src_change)
        )
        self.src_cbx.setMinimumHeight(self.add_btn.height())

        self.search_qle = QLineEdit(self)
        self.search_qle.setPlaceholderText("Search...")
        self.search_qle.textChanged.connect(self.on_search)
        self.search_qle.setMinimumHeight(self.add_btn.height())
        self.search_qle.setFont(config.qfont_console)

        self.search_layout = QHBoxLayout()
        self.search_layout.setSpacing(1)

        self.search_layout.addWidget(self.src_cbx, 20)
        self.search_layout.addWidget(self.search_qle, 45)
        self.search_layout.addWidget(self.add_btn, 10)
        self.search_layout.addWidget(self.del_btn, 10)
        self.search_layout.addWidget(self.save_btn, 10)
        self.search_layout.addWidget(self.reload_btn, 5)
        self.search_layout.addWidget(self.iln_btn, 10)

    def _create_table_view(self):
        self.view = QTableView(self)
        self.view.setFont(config.qfont_console)
        self.view.setModel(self.model)
        self.view.setSortingEnabled(False)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setWordWrap(False)
        self.view.setColumnHidden(-1, True)  # Hide index

    def _update_sources(self):
        self.src_cbx.clear()
        for fd in db_conn.files.values():
            if fd.kind == db_conn.KINDS.lng:
                self.src_cbx.addItem(
                    fd.signature,
                    data=fd.filepath,
                    is_checked=fd.filepath == self.model.fh.filepath,
                )
        if self.model.fh.filepath not in self.src_cbx.getData():
            try:
                fd = db_conn.files[self.model.fh.filepath]
                self.src_cbx.addItem(
                    fd.signature,
                    data=fd.filepath,
                    is_checked=True,
                )
            except KeyError:
                pass

    def on_search(self, query: str):
        self.model.filter(query=query)

    def on_delete(self):
        idxs = [
            self.model.fh.data_view.index[idx.row()]
            for idx in self.view.selectionModel().selectedRows()
        ]
        if idxs:
            dlg = ConfirmDeleteDialog(
                data=[self.model.fh.src_data.iloc[i].to_dict() for i in idxs],
                headers=self.model.fh.headers,
                parent=self.mw,
            )
            if dlg.exec_() == QDialog.Accepted:
                self.model.del_rows(idxs)
                self.scroll(min(idxs) - 1)
                self.update_iln_button()

    def on_add(self):
        dlg = AddCardDialog(fh=self.model.fh, parent=self.mw)
        if dlg.exec_() == QDialog.Accepted:
            self.model.add_row(dlg.values)
            self.scroll(self.model.fh.total_visible_rows - 1)
            self.update_iln_button()

    def edit_row(self):
        index = self.view.selectionModel().currentIndex()
        if index.isValid():
            self.view.edit(index)

    def on_save(self):
        if self.model.fh.is_saved:
            fcc_queue.put_notification("No changes to commit", lvl=LogLvl.warn)
        else:
            self.model.fh.save()
            log.info(f"Saved {self.model.fh.filepath}")

    def on_src_change(self):
        new_src = self.src_cbx.currentDataList()[0]
        if new_src == self.model.fh.filepath:
            return
        self.model.load(new_src)
        self.set_iln_button()

    def set_iln_button(self):
        self.iln_btn.setEnabled(self.model.fh.is_iln)
        self.iln_btn.setVisible(self.model.fh.is_iln)
        self.update_iln_button()

    def update_iln_button(self):
        if self.model.fh.is_iln:
            self.iln_btn.setText(f"+{self.model.fh.iln}")

    def check_update_iln(self):
        self.model.fh.is_iln = self.model.fh.filepath in config["ILN"].keys()
        self.set_iln_button()

    def on_reload(self):
        self.model.reload()
        self.update_iln_button()

    def scroll(self, index: int):
        self.view.setFocus()
        index = self.view.model().index(index, 1)
        self.view.scrollTo(index, QAbstractItemView.PositionAtCenter)
        self.view.selectRow(index.row())

    def lookup(self, query: str, col: int) -> str:
        phrase = self.model.fh.lookup(query, col)
        return phrase

    def open_extra_file(self, fd: FileDescriptor):
        self.src_cbx.addItem(fd.signature, data=fd.filepath)
        i = self.src_cbx.getData().index(fd.filepath)
        self.src_cbx.setChecked(i)
        self.on_src_change()

    def on_file_monitor_update(self):
        return

    def on_focus_in(self):
        pasted = QApplication.clipboard().text()
        if (
            len(pasted.split(config["sfe"]["sep"])) == 2
            and pasted != self.__last_auto_pasted
        ):
            self.on_add()
            self.__last_auto_pasted = pasted
