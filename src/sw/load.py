import PyQt5.QtWidgets as widget
from PyQt5 import QtGui


class LoadSideWindow:

    def __init__(self):
        self.side_window_titles["load"] = "Load"
        self.cur_load_index = 0
        self.load_button = self.create_button(
            self.config["icons"]["load"], self.get_load_sidewindow
        )
        self.layout_third_row.addWidget(self.load_button, 2, 0)
        self.init_shortcuts_load()

    def init_shortcuts_load(self):
        self.add_shortcut("load", self.get_load_sidewindow, "main")
        self.add_shortcut("run_command", self.load_selected_file, "load")
        self.add_shortcut("negative", lambda: self.nagivate_load_list(1), "load")
        self.add_shortcut("reverse", lambda: self.nagivate_load_list(-1), "load")
        self.add_shortcut("efc", self.get_efc_sidewindow, "load")
        self.add_shortcut("progress", self.get_progress_sidewindow, "load")
        self.add_shortcut("timespent", self.get_timer_sidewindow, "load")
        self.add_shortcut("config", self.get_config_sidewindow, "load")
        self.add_shortcut("stats", self.get_stats_sidewindow, "load")
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "load")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "load")
        self.add_shortcut("sod", self.get_sod_sidewindow, "load")

    def get_load_sidewindow(self):
        self.arrange_load_window()
        self.open_side_window(self.load_layout, "load")

    def arrange_load_window(self):
        # Window Parameters
        self.__btn_height = self.config["dim"]["sw_load_btn_height"]
        self.__qlist_width = self.config["dim"]["sw_load_qlist_width"]

        # Elements
        self.load_layout = widget.QGridLayout()
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0)
        self.load_layout.addWidget(self.create_load_button(), 1, 0, 1, 1)

        # Fill
        self.fill_flashcard_files_list()
        if self.files_count:
            self._files_qlist.setCurrentRow(self.cur_load_index)

    def get_flashcard_files_list(self):
        self._files_qlist = widget.QListWidget(self)
        self._files_qlist.setFixedWidth(self.__qlist_width)
        self._files_qlist.setFont(self.BUTTON_FONT)
        self._files_qlist.setStyleSheet(self.textbox_stylesheet)
        self._files_qlist.setVerticalScrollBar(self.get_scrollbar())
        self._files_qlist.itemClicked.connect(self.__lsw_qlist_onclick)
        widget.QShortcut(
            QtGui.QKeySequence("Home"), self._files_qlist
        ).activated.connect(lambda: self._files_qlist.setCurrentRow(0))
        widget.QShortcut(
            QtGui.QKeySequence("End"), self._files_qlist
        ).activated.connect(
            lambda: self._files_qlist.setCurrentRow(self._files_qlist.count() - 1)
        )
        return self._files_qlist

    def __lsw_qlist_onclick(self, item):
        self.cur_load_index = self._files_qlist.currentRow()

    def fill_flashcard_files_list(self):
        self.db.update_fds()
        self.load_map, i = dict(), 0
        for fd in self.db.get_sorted_languages():
            self._files_qlist.addItem(
                f"{self.config['icons']['language']} {fd.basename}"
            )
            self.load_map[i] = fd.filepath
            i += 1
        for fd in self.db.get_sorted_mistakes():
            self._files_qlist.addItem(
                f"{self.config['icons']['mistakes']} {fd.basename}"
            )
            self.load_map[i] = fd.filepath
            i += 1
        _new_revs = {r["fp"] for r in self.get_recommendations() if r["is_init"]}
        for fd in self.db.get_sorted_revisions():
            if fd.filepath in _new_revs:
                prefix = self.config["icons"]["initial"]
            else:
                prefix = self.config["icons"]["revision"]
            self._files_qlist.addItem(f"{prefix} {fd.basename}")
            self.load_map[i] = fd.filepath
            i += 1
        self.files_count = self._files_qlist.count()

    def create_load_button(self):
        load_button = widget.QPushButton(self)
        load_button.setFixedHeight(self.__btn_height)
        load_button.setFixedWidth(self.__qlist_width)
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
        self._files_qlist.setCurrentRow(self.cur_load_index)

    def load_selected_file(self):
        self.initiate_flashcards(
            self.db.files[self.load_map[self._files_qlist.currentRow()]]
        )
