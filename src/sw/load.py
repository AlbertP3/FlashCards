from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QListWidget,
    QShortcut,
    QAction,
    QMenu,
    QPushButton,
)
from PyQt5.QtGui import QKeySequence, QCursor
from utils import fcc_queue, LogLvl
from widgets import CFIDialog
from widgets import get_scrollbar
from cfg import config
from DBAC import db_conn, FileDescriptor
from sw.base import BaseTab


class LoadTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.id = "load"
        self.mw = mw
        self.mw.tab_names["load"] = "Load"
        self.cur_load_index = 0
        self.build()
        self.mw.add_tab(self._tab, self.id)
        self.mw.add_shortcut("run_command", self.load_selected_file, self.id)
        self.mw.add_shortcut("negative", lambda: self.nagivate_load_list(1), self.id)
        self.mw.add_shortcut("reverse", lambda: self.nagivate_load_list(-1), self.id)

    def open(self):
        self.mw.switch_tab(self.id)
        self.show_files()

    def show_files(self):
        self.files_qlist.clear()
        self.fill_flashcard_files_list()
        if self.files_count:
            self.files_qlist.setCurrentRow(self.cur_load_index)

    def build(self):
        self.qlist_width = config["dim"]["sw_load_qlist_width"]
        self._tab = QWidget()
        self.load_layout = QGridLayout()
        self.set_box(self.load_layout)
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0)
        self.load_layout.addWidget(self.create_load_button(), 1, 0, 1, 1)
        self._tab.setLayout(self.load_layout)

    def get_flashcard_files_list(self):
        self.files_qlist = QListWidget()
        self.files_qlist.setFixedWidth(self.qlist_width)
        self.files_qlist.setFont(self.BUTTON_FONT)
        self.files_qlist.setStyleSheet(self.textbox_stylesheet)
        self.files_qlist.setVerticalScrollBar(get_scrollbar())
        self.files_qlist.itemClicked.connect(self.lsw_qlist_onclick)
        self.files_qlist.itemDoubleClicked.connect(self.lsw_qlist_onDoubleClick)
        self.attach_files_qlist_ctx()
        QShortcut(QKeySequence("Home"), self.files_qlist).activated.connect(
            lambda: self.files_qlist.setCurrentRow(0)
        )
        QShortcut(QKeySequence("End"), self.files_qlist).activated.connect(
            lambda: self.files_qlist.setCurrentRow(self.files_qlist.count() - 1)
        )
        return self.files_qlist

    def attach_files_qlist_ctx(self):
        self._files_qlist_ctx = QMenu()
        self._files_qlist_ctx.setStyleSheet(config["theme"]["ctx_stylesheet"])
        self._files_qlist_ctx.setFont(self.BUTTON_FONT)
        self.files_qlist.setContextMenuPolicy(3)
        self.files_qlist.customContextMenuRequested.connect(self.show_files_qlist_ctx)

    def show_files_qlist_ctx(self, position):
        self._files_qlist_ctx.clear()
        act = QAction("Create…", self.files_qlist)
        act.triggered.connect(self.show_input_dialog)
        self._files_qlist_ctx.addAction(act)
        self._files_qlist_ctx.exec_(QCursor.pos())

    def show_input_dialog(self):
        fd = db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        start = config["ILN"].get(fd.filepath, 0)
        cnt = db_conn.get_lines_count(fd) - start
        dialog = CFIDialog(self.files_qlist, start, cnt)
        if dialog.exec_():
            start, cnt = dialog.get_values()
            self.cfi(fd, start, cnt)

    def cfi(self, fd: FileDescriptor, start: int, cnt: int):
        data = db_conn.load_dataset(fd, do_shuffle=False, activate=False)
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
                len_parent = data.shape[0] - start + cnt
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

        db_conn.load_tempfile(
            basename=f"{fd.lng}{len_child}",
            data=data,
            lng=fd.lng,
            kind=db_conn.KINDS.lng,
            parent={
                "filepath": fd.filepath,
                "len_": len_parent,
            },
        )
        db_conn.shuffle_dataset()
        self.mw.switch_tab("main")
        self.mw.update_backend_parameters()
        self.mw.update_interface_parameters()
        self.mw.reset_timer()

    def lsw_qlist_onclick(self, item):
        self.cur_load_index = self.files_qlist.currentRow()

    def lsw_qlist_onDoubleClick(self, item):
        self.cur_load_index = self.files_qlist.currentRow()
        self.load_selected_file()

    def fill_flashcard_files_list(self):
        db_conn.update_fds()
        self.load_map, i = dict(), 0
        for fd in db_conn.get_sorted_languages():
            self.files_qlist.addItem(f"{config['icons']['language']} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        for fd in db_conn.get_sorted_mistakes():
            self.files_qlist.addItem(f"{config['icons']['mistakes']} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        _new_revs = {r["fp"] for r in self.mw.efc.get_recommendations() if r["is_init"]}
        for fd in db_conn.get_sorted_revisions():
            if fd.filepath in _new_revs:
                prefix = config["icons"]["initial"]
            else:
                prefix = config["icons"]["revision"]
            self.files_qlist.addItem(f"{prefix} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        self.files_count = self.files_qlist.count()

    def create_load_button(self):
        load_button = QPushButton()
        load_button.setFixedHeight(self.BUTTON_HEIGHT)
        load_button.setFixedWidth(self.qlist_width)
        load_button.setFont(self.BUTTON_FONT)
        load_button.setText("Load")
        load_button.setStyleSheet(self.button_stylesheet)
        load_button.clicked.connect(self.load_selected_file)
        return load_button

    def nagivate_load_list(self, move: int):
        new_index = self.cur_load_index + move
        if new_index < 0:
            self.cur_load_index = self.files_count - 1
        elif new_index >= self.files_count:
            self.cur_load_index = 0
        else:
            self.cur_load_index = new_index
        self.files_qlist.setCurrentRow(self.cur_load_index)

    def load_selected_file(self):
        self.mw.initiate_flashcards(
            db_conn.files[self.load_map[self.files_qlist.currentRow()]]
        )
