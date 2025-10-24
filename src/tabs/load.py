import os
import subprocess
import logging
import pandas as pd
from PyQt5.QtWidgets import (
    QGridLayout,
    QListWidget,
    QAction,
    QMenu,
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QCursor
from utils import find_case_insensitive
from int import fcc_queue, LogLvl
from widgets import (
    CFIDialog,
    RenameDialog,
    CreateFileDialog,
    ConfirmDeleteFileDialog,
    get_button,
    get_scrollbar,
)
from cfg import config
from DBAC import db_conn, FileDescriptor
from tabs.base import BaseTab
from typing import TYPE_CHECKING
from logtools import audit_log_rename

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("GUI")


class LoadTab(BaseTab):

    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.id = "load"
        self.mw = mw
        self.cur_load_index = 0
        self._files = dict()
        self.is_view_outdated = True
        self.build()
        self.mw.add_tab(self.tab, self.id, "Load")

    def init_cross_shortcuts(self):
        super().init_cross_shortcuts()
        self.mw.add_ks(
            config["kbsc"]["negative"],
            lambda: self.nagivate_load_list(1),
            self.files_qlist,
        )
        self.mw.add_ks(
            config["kbsc"]["reverse"],
            lambda: self.nagivate_load_list(-1),
            self.files_qlist,
        )
        self.mw.add_ks("Home", lambda: self.set_load_list_index(0), self.files_qlist)
        self.mw.add_ks(
            "End",
            lambda: self.set_load_list_index(self.files_count - 1),
            self.files_qlist,
        )
        self.mw.add_ks(Qt.Key_Return, self.load_selected_file, self.files_qlist)

    def open(self):
        self.mw.switch_tab(self.id)
        if not self.mw.efc.cache_valid:
            with self.mw.loading_ctx("load.load_files_data_with_efc"):
                self.mw.efc.calc_recommendations()
                self.is_view_outdated = True
        if self.is_view_outdated:
            self.load_files_data()
            self.show_files()
        self.scroll_to_active()

    def show_files(self):
        self.fill_files_list()
        self.is_view_outdated = False

    def fill_files_list(self):
        self.load_map = dict()  # index: filepath
        i = 0
        self.files_qlist.clear()
        for fd in self._files["lngs"]:
            self.files_qlist.addItem(f"{config['icons']['language']} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        for fd in self._files["msts"]:
            self.files_qlist.addItem(f"{config['icons']['mistakes']} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        for fd in self._files["revs"]:
            if fd.filepath in self._files["new_revs"]:
                prefix = config["icons"]["initial"]
            else:
                prefix = config["icons"]["revision"]
            self.files_qlist.addItem(f"{prefix} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        self.files_count = self.files_qlist.count()

    @pyqtSlot()
    def load_files_data(self):
        self._files["lngs"] = db_conn.get_sorted_languages()
        self._files["msts"] = db_conn.get_sorted_mistakes()
        self._files["new_revs"] = {
            r.filepath for r in self.mw.efc.get_recommendations() if r.is_initial
        }
        self._files["revs"] = db_conn.get_sorted_revisions()

    def scroll_to_active(self):
        for k, v in self.load_map.items():
            if v == self.mw.active_file.filepath:
                index = k
                break
        else:
            index = 0
        item = self.files_qlist.item(index)
        self.files_qlist.scrollToItem(item, hint=QListWidget.PositionAtCenter)
        self.cur_load_index = index
        self.files_qlist.setCurrentRow(self.cur_load_index)

    def build(self):
        self.load_layout = QGridLayout()
        self.set_box(self.load_layout)
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0, 1, 10)
        self.load_layout.addWidget(
            get_button(None, "Load", self.load_selected_file), 1, 0, 1, 9
        )
        self.load_layout.addWidget(
            get_button(None, "+", self.show_create_file), 1, 9, 1, 1
        )
        self.tab.setLayout(self.load_layout)

    def get_flashcard_files_list(self):
        self.files_qlist = QListWidget()
        self.files_qlist.setFont(config.qfont_button)
        self.files_qlist.setVerticalScrollBar(get_scrollbar())
        self.files_qlist.itemClicked.connect(self.lsw_qlist_onclick)
        self.files_qlist.itemDoubleClicked.connect(self.lsw_qlist_onDoubleClick)
        self.attach_files_qlist_ctx()
        return self.files_qlist

    def attach_files_qlist_ctx(self):
        self._files_qlist_ctx = QMenu(self.files_qlist)
        self._files_qlist_ctx.setFont(config.qfont_button)
        self.files_qlist.setContextMenuPolicy(3)
        self.files_qlist.customContextMenuRequested.connect(self.show_files_qlist_ctx)

    def show_files_qlist_ctx(self, position):
        self._files_qlist_ctx.clear()

        create_iln = QAction("Create…", self.files_qlist)
        create_iln.triggered.connect(self.ctx_ILN)
        self._files_qlist_ctx.addAction(create_iln)

        reveal = QAction("Edit")
        reveal.triggered.connect(self.ctx_reveal_file)
        self._files_qlist_ctx.addAction(reveal)

        folder = QAction("Folder")
        folder.triggered.connect(self.ctx_open_folder)
        self._files_qlist_ctx.addAction(folder)

        rename = QAction("Rename")
        rename.triggered.connect(self.ctx_rename)
        self._files_qlist_ctx.addAction(rename)

        delete = QAction("Delete")
        delete.triggered.connect(self.ctx_delete_file)
        self._files_qlist_ctx.addAction(delete)

        self._files_qlist_ctx.exec_(QCursor.pos())

    def ctx_reveal_file(self):
        """Opens selected file in SFE"""
        try:
            fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
            self.mw.sfe.open_extra_file(fd)
            self.mw.switch_tab(self.mw.sfe.id)
        except Exception as e:
            log.error(f"Error opening {fd.filepath}: {e}", exc_info=True)
            fcc_queue.put_notification(
                f"Error opening {fd.filepath}", LogLvl.err, func=self.mw.log.open
            )

    def ctx_open_folder(self):
        """Opens containing folder"""
        try:
            fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
            dir = os.path.dirname(fd.filepath)
            cmd = config["open_containing_dir_cmd"]
            if not cmd:
                raise KeyError
            subprocess.Popen([cmd, dir], shell=False)
        except KeyError:
            fcc_queue.put_notification("Open folder command is missing", LogLvl.err)
        except Exception as e:
            log.error(f"Error opening directory {dir}: {e}", exc_info=True)
            fcc_queue.put_notification(
                f"Error opening directory {dir}", LogLvl.err, func=self.mw.log.open
            )

    def ctx_delete_file(self):
        fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        dialog = ConfirmDeleteFileDialog(fd, self.mw)
        if dialog.exec_() == QDialog.Accepted:
            os.remove(fd.filepath)
            log.info(f"Removed file: {fd.filepath}")
            self.mw.update_files_lists()
            if self.mw.active_file.filepath == fd.filepath:
                self.mw.efc._load_next_efc()
            self.open()

    def ctx_ILN(self):
        fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        self.create_from_iln(fd)

    def create_from_iln(self, fd: FileDescriptor):
        start = config["ILN"].get(fd.filepath, 0)
        cnt = db_conn.get_lines_count(fd) - start
        dialog = CFIDialog(self.files_qlist, start, cnt)
        if dialog.exec_():
            start, cnt = dialog.get_values()
            self._cfi(fd, start, cnt)

    def _cfi(self, fd: FileDescriptor, start: int, cnt: int):
        """Loads a temporary language set"""
        data = db_conn.get_data(fd)
        if cnt == 0:
            len_parent = data.shape[0]
            data = data.iloc[start:, :]
        elif cnt < 0:
            if start >= 0:
                len_parent = start
                data = data.iloc[start + cnt : start, :]
            else:
                len_parent = data.shape[0] + start
                data = data.iloc[start + cnt : start, :]
        else:
            if start >= 0:
                len_parent = start + cnt
                data = data.iloc[start : start + cnt, :]
            else:
                len_parent = data.shape[0] + start + cnt
                data = data.iloc[start : start + cnt, :]

        len_child = data.shape[0]
        if len_child <= 0:
            fcc_queue.put_notification("Not enough cards", lvl=LogLvl.warn)
            return

        if not self.mw.active_file.tmp:
            self.mw.file_monitor_del_path(self.mw.active_file.filepath)

        db_conn.activate_tmp_file(
            basename=f"{fd.lng}{len_child}",
            signature=f"{fd.lng}{len_child}",
            data=data,
            lng=fd.lng,
            kind=db_conn.KINDS.lng,
            parent={
                "filepath": fd.filepath,
                "len_": len_parent,
            },
        )
        db_conn.shuffle_dataset(self.mw.active_file)
        self.mw.switch_tab("main")
        self.mw.update_backend_parameters(is_score_allowed=config["opt"]["graded_cfi"])
        self.mw.update_interface_parameters()
        self.mw.reset_timer()

    def ctx_rename(self):
        """Rename selected file"""
        fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        dialog = RenameDialog(self.files_qlist, fd.basename)
        if dialog.exec_():
            old_signature = fd.signature
            old_filepath = fd.filepath
            new_filename = dialog.get_filename()
            new_filepath = os.path.join(
                os.path.dirname(old_filepath), f"{new_filename}{fd.ext}"
            )

            self.mw.file_monitor_del_protected_path(old_filepath)
            os.rename(old_filepath, new_filepath)
            self.mw.update_files_lists()

            if fd.kind in db_conn.GRADED:
                db_conn.rename_signature(fd.signature, new_filename)
                msgp1 = " and Signature "
            else:
                msgp1 = " "

            if iln := config["ILN"].get(old_filepath):
                config["ILN"][new_filepath] = iln
                del config["ILN"][old_filepath]

            self.open()

            if fd.active:
                fd.filepath = new_filepath
                fd.signature = new_filename
                fd.basename = new_filename
                self.mw.file_monitor_add_path(new_filepath)
                self.mw.get_title()
                config["onload_filepath"] = new_filepath

            if old_filepath == config["sfe"]["last_file"]:
                config["sfe"]["last_file"] = new_filepath
                self.mw.sfe.model.fh.fd.filepath = new_filepath
                self.mw.sfe.src_cbx.showPopup()
                self.mw.sfe.src_cbx.hidePopup()
                self.mw.sfe.on_reload()

            if old_filepath in config["sigenpat"].keys():
                config["sigenpat"][new_filepath] = config["sigenpat"][old_filepath]
                config["sigenpat"].pop(old_filepath)

            audit_log_rename(old_filepath, new_filepath, old_signature, new_filename)

            log.info(f"Renamed '{old_filepath}' to '{new_filepath}'")
            fcc_queue.put_notification(
                f"Filename{msgp1}changed successfully", lvl=LogLvl.important
            )

    def lsw_qlist_onclick(self, item):
        self.cur_load_index = self.files_qlist.currentRow()

    def lsw_qlist_onDoubleClick(self, item):
        self.cur_load_index = self.files_qlist.currentRow()
        self.load_selected_file()

    def nagivate_load_list(self, move: int):
        new_index = self.cur_load_index + move
        if new_index < 0:
            self.cur_load_index = self.files_count - 1
        elif new_index >= self.files_count:
            self.cur_load_index = 0
        else:
            self.cur_load_index = new_index
        self.files_qlist.setCurrentRow(self.cur_load_index)

    def set_load_list_index(self, index: int):
        self.cur_load_index = index
        self.files_qlist.setCurrentRow(self.cur_load_index)

    def load_selected_file(self):
        self.mw.initiate_flashcards(
            db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        )

    def show_create_file(self):
        dialog = CreateFileDialog(parent=self.mw)

        if dialog.exec_():
            spc = dialog.get_data()
            lngs = db_conn.get_available_languages(ignore=set())

            try:
                spc.tgt_lng_id = find_case_insensitive(spc.tgt_lng_id, lngs)
            except KeyError:
                db_conn.create_language_dir_tree(spc.tgt_lng_id)
                config["languages"].append(spc.tgt_lng_id)

            df = pd.DataFrame(
                columns=[spc.tgt_lng_id.lower(), spc.src_lng_id.lower()], data=[]
            )
            filepath = (
                db_conn.make_filepath(spc.tgt_lng_id, db_conn.LNG_DIR, spc.filename)
                + ".csv"
            )
            df.to_csv(
                filepath,
                index=False,
                encoding="utf-8",
                header=True,
                mode="w",
            )
            log.info(f"Created new Language file: {filepath}")
            fcc_queue.put_notification(
                f"Created new Language file: {filepath}", lvl=LogLvl.important
            )
            self.mw.update_files_lists()
            self.open()
