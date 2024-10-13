import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from utils import fcc_queue
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
        self.textbox_stylesheet = self.config["theme"]["textbox_style_sheet"]
        self.button_style_sheet = self.config["theme"]["button_style_sheet"]
        self.BUTTON_FONT = QtGui.QFont(
            self.config["theme"]["font"], self.config["theme"]["font_button_size"]
        )
        self.textbox_width = 275
        self.textbox_height = 200
        self.buttons_height = 45

        # Elements
        self.efc_layout = widget.QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(self.create_load_efc_button(), 1, 0, 1, 1)

        # Fill List Widget
        [self.recommendation_list.addItem(str(r)) for r in self.get_recommendations()]
        self.files_count = self.recommendation_list.count()
        if self.files_count:
            self.cur_efc_index = min(self.files_count - 1, self.cur_efc_index)
            self.recommendation_list.setCurrentRow(self.cur_efc_index)

    def create_recommendations_list(self):
        self.recommendation_list = widget.QListWidget(self)
        self.recommendation_list.setFixedWidth(self.textbox_width)
        self.recommendation_list.setFont(self.BUTTON_FONT)
        self.recommendation_list.setStyleSheet(self.textbox_stylesheet)
        return self.recommendation_list

    def create_load_efc_button(self):
        efc_button = widget.QPushButton(self)
        efc_button.setFixedHeight(self.buttons_height)
        efc_button.setFixedWidth(self.textbox_width)
        efc_button.setFont(self.BUTTON_FONT)
        efc_button.setText("Load")
        efc_button.setStyleSheet(self.button_style_sheet)
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
        self.recommendation_list.setCurrentRow(self.cur_efc_index)

    def load_next_efc(self):

        if self.config["next_efc"]["require_recorded"] and not self.is_recorded:
            fcc_queue.put("Review current revision before proceeding")
            return

        fd = None
        recs = self.get_recommendations()

        if not recs:
            fcc_queue.put("There are no EFC recommendations")
            return

        if self.config["next_efc"]["reversed"]:
            recs = reversed(recs)
        if self.config["next_efc"]["random"]:
            shuffle(recs)

        for rec in recs:
            try:
                tmp_fd = [fd for fd in self.db.files.values() if fd.basename == rec][0]
                if (
                    self.config["next_efc"]["skip_mistakes"]
                    and tmp_fd.kind == self.db.KINDS.mst
                ):
                    continue
                else:
                    fd = tmp_fd
                    break
            except IndexError:
                if not self.config["next_efc"]["skip_new"]:
                    fd = self.db.files[self.paths_to_suggested_lngs[recs[0]]]
                    break

        if fd:
            self.initiate_flashcards(fd)
            self.del_side_window()
        else:
            fcc_queue.put("There are no EFC recommendations", importance=20)

    def load_selected_efc(self):
        if fd := self.get_fd_from_selected_file():
            self.initiate_flashcards(fd)
            self.del_side_window()
