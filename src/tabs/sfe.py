from PyQt5.QtWidgets import (
    QVBoxLayout,
    QLineEdit,
    QTableView,
    QHBoxLayout,
    QDialog,
    QHeaderView,
    QAbstractItemView,
    QApplication,
    QMenu,
)
from PyQt5.QtCore import QTimer, Qt, QModelIndex
from PyQt5.QtGui import QCursor
import logging
from tabs.base import BaseTab
from DBAC import db_conn, FileDescriptor
from sfe.datatable import DataTableModel, QTableItemDelegate
from widgets import (
    AddCardDialog,
    get_button,
    CheckableComboBox,
    ConfirmDeleteCardDialog,
)
from cfg import config
from utils import singular
from int import fcc_queue, LogLvl, sbus
from data_types import SfeMods
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
        self.sel_idx = 0
        self._unack_move: tuple = None  # ref, offset
        self._disable_src_chg = False
        self.build()
        self.mw.add_tab(self.tab, self.id, "Source File Editor")

    def _set_disable_src_chg(self, b: bool):
        self._disable_src_chg = b

    def init_cross_shortcuts(self):
        super().init_cross_shortcuts()
        self.mw.add_ks(config["kbsc"]["sfe_search"], self.search_qle.setFocus, self.tab)
        self.mw.add_ks(config["kbsc"]["sfe_add"], self.on_add, self.tab)
        self.mw.add_ks(config["kbsc"]["sfe_save"], self.on_save, self.tab)
        self.mw.add_ks("Home", lambda: self.scroll(0), self.tab)
        self.mw.add_ks("End", lambda: self.scroll(self.model.rowCount() - 1), self.tab)
        self.mw.add_ks("Delete", self.on_delete, self.tab)
        self.mw.add_ks("F2", self.edit_row, self.tab)
        self.mw.add_ks("Ctrl+Down", lambda: self.move_row(1), self.tab)
        self.mw.add_ks("Ctrl+Up", lambda: self.move_row(-1), self.tab)

    def open(self):
        self.mw.switch_tab(self.id)
        self.view.setFocus()
        self.tab.focus_in()
        if self.model.fh.fd.is_parent_of(self.mw.active_file) and not self.model.fh.query:
            self.scroll(db_conn.get_oid_by_index(self.mw.current_index))

    def build(self):
        self.tab.set_exit(self.exit)
        self.tab.set_focus_in(self.on_focus_in)
        self.model = DataTableModel(db_conn.files.get(config["sfe"]["last_file"]))
        sbus.sfe_mod.connect(self.on_model_modified)
        self.sfe_layout = QVBoxLayout(self)
        self.sfe_layout.setContentsMargins(1, 1, 1, 1)
        self.sfe_layout.setSpacing(1)
        self._create_search_layout()
        self._create_table_view()
        self.sfe_layout.addLayout(self.search_layout)
        self.sfe_layout.addWidget(self.view)
        self.tab.setLayout(self.sfe_layout)
        self.scroll(self.model.rowCount() - 1)
        self.update_search_placeholder()

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
        self.update_iln_button()
        self.duo_btn = get_button(
            self.tab,
            text="Duo+",
            function=lambda: self.mw.trk.trk.daily_layout.on_submit(
                lng=self.model.fh.fd.lng
            ),
            dtip=self.mw.trk.trk.daily_layout.get_tooltip,
        )
        if not config["tracker"]["duo"]["active"]:
            self.duo_btn.setVisible(False)
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
        self.search_layout.addWidget(self.duo_btn, 10)

    def _create_table_view(self):
        self.view = QTableView(self)
        self.view.setItemDelegate(QTableItemDelegate())
        self.view.setFont(config.qfont_console)
        self.view.setModel(self.model)
        self.view.setSortingEnabled(False)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setEditTriggers(QTableView.DoubleClicked | QTableView.SelectedClicked)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setWordWrap(False)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.open_ctx)
        self.q_ctx = QMenu(self.view)
        self.q_ctx.setFont(config.qfont_button)

    def open_ctx(self, pos: QModelIndex):
        idx = self.view.indexAt(pos)
        if not idx.isValid():
            return
        self.q_ctx.clear()
        act_id = self.q_ctx.addAction(f"ID: {self.model.fh.data_view.index[idx.row()]}")
        act_id.setDisabled(True)
        act_reverse = self.q_ctx.addAction(f"Reverse")
        act_reverse.triggered.connect(self.reverse_row)
        self.q_ctx.exec_(QCursor.pos())

    def _update_sources(self):
        self.src_cbx.clear()
        for fd in db_conn.files.values():
            if fd.kind == db_conn.KINDS.lng:
                self.src_cbx.addItem(
                    text=fd.signature,
                    data=fd,
                    is_checked=fd.filepath == self.model.fh.filepath,
                )
        if self.model.fh not in self.src_cbx.getData():
            try:
                fd = db_conn.files[self.model.fh.filepath]
                self.src_cbx.addItem(
                    text=fd.signature,
                    data=fd,
                    is_checked=True,
                )
            except KeyError:
                pass
        if self.mw.active_file not in self.src_cbx.getData():
            self.src_cbx.addItem(
                text=self.mw.active_file.signature,
                data=self.mw.active_file,
                is_checked=self.mw.active_file.filepath == self.model.fh.filepath,
            )

    def on_search(self, query: str):
        if query:
            try:
                self.sel_idx = self.view.selectedIndexes()[0].row()
            except IndexError:
                pass
            self.model.filter(query=query)
        else:
            self.model.remove_filter()
            self.scroll(self.sel_idx)

    def on_delete(self):
        idxs = [
            self.model.fh.data_view.index[idx.row()]
            for idx in self.view.selectionModel().selectedRows()
        ]
        if idxs:
            dlg = ConfirmDeleteCardDialog(
                data=[self.model.fh.src_data.iloc[i].to_dict() for i in idxs],
                headers=self.model.fh.headers,
                parent=self.mw,
            )
            if dlg.exec_() == QDialog.Accepted:
                self.model.del_rows(idxs)
                self.scroll(min(idxs) - 1)
                self.update_iln_button()
                self.__on_delete_if_active_file(idxs)

    def __on_delete_if_active_file(self, idxs: list[int]):
        if self.model.fh.fd.should_propagate_to(self.mw.active_file):
            self.mw.sfe_apply_delete(oids=idxs)
            if self.model.fh.fd.is_parent_of(self.mw.active_file):
                self.mw.active_file.parent["del"] += sum(
                    1 for i in idxs if i >= self.mw.active_file.parent["from"]
                )
                self.mw.active_file.parent["from"] -= sum(
                    1 for i in idxs if i <= self.mw.active_file.parent["from"]
                )

    @singular
    def on_add(self):
        dlg = AddCardDialog(fh=self.model.fh, parent=self.mw)
        if dlg.exec_() == QDialog.Accepted:
            self.model.add_row(dlg.values)
            self.scroll(self.model.fh.total_visible_rows - 1)
            self.update_iln_button()
            if self.model.fh.fd.should_propagate_to(self.mw.active_file):
                self.mw.sfe_apply_add(row=dlg.values)

    def edit_row(self):
        index = self.view.selectionModel().currentIndex()
        if index.isValid():
            self.view.edit(index)

    def reverse_row(self):
        idx = self.view.selectionModel().currentIndex()
        if idx.isValid():
            self.model.reverse_row(idx.row())
            self.view.setCurrentIndex(idx)

    def move_row(self, by: int):
        idx = self.view.selectionModel().currentIndex()
        if not idx.isValid():
            return
        elif not (0 <= idx.row() + by < len(self.model.fh.data_view)):
            return
        idx = idx.row()
        self.model.move_row(ref=idx, offset=by)
        self.view.selectRow(idx + by)
        self._unack_move = (idx, by)

    def on_model_modified(self, mod: int):
        self.save_btn.setDisabled(self.model.fh.is_saved)
        self.update_search_placeholder()
        if self.model.fh.fd.should_propagate_to(self.mw.active_file):
            if mod == SfeMods.UPDATE:

                def update_active_file():
                    index = self.view.selectionModel().currentIndex()
                    if index.isValid():
                        idx = self.model.fh.data_view.index[index.row()]
                        self.mw.sfe_apply_edit(
                            oid=idx,
                            val=self.model.fh.data_view.iloc[index.row()].to_list(),
                        )

                QTimer.singleShot(1, update_active_file)

            elif mod == SfeMods.MOVE:

                def sync_active_file():
                    ref, by = self._unack_move
                    for idx in (ref, ref + by):
                        idx = self.model.fh.data_view.index[idx]
                        self.mw.sfe_apply_edit(
                            oid=idx,
                            val=self.model.fh.data_view.iloc[idx].to_list(),
                        )
                    self._unack_move = None

                QTimer.singleShot(1, sync_active_file)

    def on_save(self):
        if self.model.fh.is_saved:
            fcc_queue.put_notification("No changes to commit", lvl=LogLvl.warn)
        else:
            self.model.fh.save()
            log.info(f"Saved {self.model.fh.filepath}")

    def on_src_change(self):
        fd: FileDescriptor = self.src_cbx.currentDataList()[0]
        if self._disable_src_chg or fd == self.model.fh.fd:
            return
        self._set_disable_src_chg(True)
        self.model.load(fd)
        self._refresh_search_qle()
        self.update_search_placeholder()
        self.update_iln_button()
        if fd.active:
            self.scroll(db_conn.get_oid_by_index(self.mw.current_index))
        else:
            self.scroll(len(self.model.fh.src_data)-1)
        self.view.setFocus()
        QTimer.singleShot(10, lambda: self._set_disable_src_chg(False))

    def update_iln_button(self):
        self.iln_btn.setText(f"+{self.model.fh.iln}")

    def check_update_iln(self):
        self.model.fh.is_iln = self.model.fh.filepath in config["ILN"].keys()
        self.update_iln_button()

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
        self.src_cbx.addItem(fd.signature, data=fd)
        i = self.src_cbx.getData().index(fd)
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

    def _refresh_search_qle(self):
        self.search_qle.blockSignals(True)
        self.search_qle.setText(self.model.fh.query)
        self.search_qle.blockSignals(False)

    def update_search_placeholder(self):
        try:
            num_cards = len(self.model.fh.src_data)
        except Exception as e:
            log.error(e, stack_info=True)
            num_cards = 0
        self.search_qle.setPlaceholderText(f"Search {num_cards:,} cards...")
