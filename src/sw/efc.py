import PyQt5.QtWidgets as widget
from PyQt5.QtGui import QFont
from utils import fcc_queue, LogLvl
from efc import EFC
from random import shuffle


class EFCSideWindow(EFC):

    def __init__(self):
        EFC.__init__(self)
        self.side_window_titles["efc"] = "EFC"
        self.cur_efc_index = 0
        # add button to main window
        self.efc_button = self.create_button(
            self.config["icons"]["efc"], self.get_efc_sidewindow
        )
        self.layout_third_row.addWidget(self.efc_button, 2, 2)
        self.init_shortcuts_efc()

    def init_shortcuts_efc(self):
        self.add_shortcut("efc", self.get_efc_sidewindow, "main")
        self.add_shortcut("next_efc", self.load_next_efc, "main")
        self.add_shortcut("run_command", self.load_selected_efc, "efc")
        self.add_shortcut("negative", lambda: self.nagivate_efc_list(1), "efc")
        self.add_shortcut("reverse", lambda: self.nagivate_efc_list(-1), "efc")
        self.add_shortcut("load", self.get_load_sidewindow, "efc")
        self.add_shortcut("progress", self.get_progress_sidewindow, "efc")
        self.add_shortcut("timespent", self.get_timer_sidewindow, "efc")
        self.add_shortcut("config", self.get_config_sidewindow, "efc")
        self.add_shortcut("stats", self.get_stats_sidewindow, "efc")
        self.add_shortcut("mistakes", self.get_mistakes_sidewindow, "efc")
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "efc")
        self.add_shortcut("sod", self.get_sod_sidewindow, "efc")

    def get_efc_sidewindow(self):
        self.arrange_efc_window()
        self.open_side_window(self.efc_layout, "efc")

    def arrange_efc_window(self):
        # Style
        self.__qlist_stylesheet = self.config["theme"]["textbox_stylesheet"]
        self.__btn_stylesheet = self.config["theme"]["button_stylesheet"]
        self.__efc_sw_font = QFont(
            self.config["theme"]["font"], self.config["dim"]["font_button_size"]
        )
        self.__qlist_width = self.config["dim"]["sw_efc_qlist_width"]
        self.__btn_height = self.config["dim"]["sw_efc_btn_height"]

        # Elements
        self.efc_layout = widget.QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(self.create_load_efc_button(), 1, 0, 1, 1)

        # Fill List Widget
        for r in self.get_recommendations():
            self.recoms_qlist.addItem(r["disp"])
        self.files_count = self.recoms_qlist.count()
        if self.files_count:
            self.cur_efc_index = min(self.files_count - 1, self.cur_efc_index)
            self.recoms_qlist.setCurrentRow(self.cur_efc_index)

    def create_recommendations_list(self):
        self.recoms_qlist = widget.QListWidget(self)
        self.recoms_qlist.setFixedWidth(self.__qlist_width)
        self.recoms_qlist.setFont(self.__efc_sw_font)
        self.recoms_qlist.setStyleSheet(self.__qlist_stylesheet)
        self.recoms_qlist.setVerticalScrollBar(self.get_scrollbar())
        self.recoms_qlist.itemClicked.connect(self.__recoms_qlist_onclick)
        self.recoms_qlist.itemDoubleClicked.connect(self.__recoms_qlist_onDoubleClick)
        return self.recoms_qlist

    def __recoms_qlist_onclick(self, item):
        self.cur_efc_index = self.recoms_qlist.currentRow()

    def __recoms_qlist_onDoubleClick(self, item):
        self.cur_efc_index = self.recoms_qlist.currentRow()
        self.load_selected_efc()

    def create_load_efc_button(self):
        efc_button = widget.QPushButton(self)
        efc_button.setFixedHeight(self.__btn_height)
        efc_button.setFixedWidth(self.__qlist_width)
        efc_button.setFont(self.__efc_sw_font)
        efc_button.setText("Load")
        efc_button.setStyleSheet(self.__btn_stylesheet)
        efc_button.clicked.connect(self.load_selected_efc)
        return efc_button

    def nagivate_efc_list(self, move: int):
        new_index = self.cur_efc_index + move
        if new_index < 0:
            self.cur_efc_index = self.files_count - 1
        elif new_index >= self.files_count:
            self.cur_efc_index = 0
        else:
            self.cur_efc_index = new_index
        self.recoms_qlist.setCurrentRow(self.cur_efc_index)

    def load_selected_efc(self):
        if fd := self.get_fd_from_selected_file():
            self.initiate_flashcards(fd)
            self.del_side_window()

    def load_next_efc(self):
        if (
            self.config["efc"]["opt"]["require_recorded"]
            and self.positives + self.negatives != 0
        ):
            fcc_queue.put_notification(
                "Finish your current revision before proceeding", lvl=LogLvl.warn
            )
            return
        elif self.config["efc"]["opt"]["save_mistakes"] and self.should_save_mistakes():
            self.save_current_mistakes()

        if self.config["CRE"]["items"]:
            self.activate_tab("fcc")
            self.fcc_inst.execute_command(["cre"])
        else:
            self.__load_next_efc()

    def __load_next_efc(self):
        fd = None
        recs = [
            rec
            for rec in self.get_recommendations()
            if rec["fp"] != self.active_file.filepath
        ]

        if not recs:
            fcc_queue.put_notification(
                "There are no EFC recommendations", lvl=LogLvl.warn
            )
            return

        if self.config["efc"]["opt"]["random"]:
            shuffle(recs)
        if self.config["efc"]["opt"]["reversed"]:
            recs = reversed(recs)
        if self.config["efc"]["opt"]["new_first"]:
            recs.sort(key=lambda x: x["is_init"], reverse=True)

        for rec in recs:
            _fd = self.db.files[rec["fp"]]
            if (
                self.config["efc"]["opt"]["skip_mistakes"]
                and _fd.kind == self.db.KINDS.mst
            ):
                continue
            else:
                fd = _fd
                break

        if fd:
            self.initiate_flashcards(fd)
            self.del_side_window()
        else:
            fcc_queue.put_notification(
                "There are no EFC recommendations", lvl=LogLvl.warn
            )
