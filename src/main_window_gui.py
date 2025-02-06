import os
import traceback
import sys
import logging
from PyQt5 import QtCore
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QTimer
from main_window_logic import MainWindowLogic
from sw import SideWindows
from utils import fcc_queue, format_seconds_to, Caliper, LogLvl
from DBAC.api import FileDescriptor
from widgets import NotificationPopup

log = logging.getLogger("GUI")


class MainWindowGUI(widget.QWidget, MainWindowLogic, SideWindows):

    def __init__(self):
        self.__last_focus_out_timer_state = False
        self.window_title = "FlashCards"
        self.q_app = widget.QApplication([self.window_title])
        widget.QWidget.__init__(self)
        sys.excepthook = self.excepthook

    @staticmethod
    def configure_scaling():
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        widget.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        widget.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    def excepthook(self, exc_type, exc_value, exc_tb):
        err_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.notify_on_error(err_traceback, exc_value)

    def launch_app(self):
        self.initiate_file_monitor()
        self.build_interface()
        self.initiate_timer()
        self.initiate_pace_timer()
        self.initiate_notification_timer()
        self.__onload_initiate_flashcards()
        self.__onload_notifications()
        self.start_notification_timer()
        self.q_app.installEventFilter(self)
        self.q_app.exec()

    def __onload_initiate_flashcards(self):
        if metadata := self.config.cache["snapshot"]["file"]:
            try:
                self.db.load_tempfile(
                    data=self.db.read_csv(metadata["filepath"]),
                    kind=metadata["kind"],
                    basename=metadata["basename"],
                    lng=metadata["lng"],
                    parent=metadata["parent"],
                    signature=metadata["signature"],
                )
                if self.config.cache["snapshot"]["session"]:
                    self.apply_session_snapshot()
                else:
                    self.db.shuffle_dataset()
                    self.update_backend_parameters()
                    self.update_interface_parameters()
                    log.debug("Started a new session")
                os.remove(self.db.TMP_BACKUP_PATH)
                self.config.cache["snapshot"]["file"] = None
                log.debug(f"Used temporary backup file from {self.db.TMP_BACKUP_PATH}")
                return
            except Exception as e:
                log.error(e, exc_info=True)
        # if cached snapshot file fails to load or n/a
        fd = self.db.files.get(
            self.config["onload_filepath"],
            FileDescriptor(filepath=self.config["onload_filepath"], tmp=True),
        )
        if self.config.cache["snapshot"]["session"]:
            try:
                self.load_flashcards(
                    fd, seed=self.config.cache["snapshot"]["session"]["pd_random_seed"]
                )
                self.apply_session_snapshot()
                return
            except Exception as e:
                log.error(e, exc_info=True)
        # if cached snapshot session fails to load or n/a
        self.initiate_flashcards(fd)
        log.debug("Started a new session")

    def apply_session_snapshot(self):
        self._apply_session_snapshot_backend()
        suffix = self.config["icons"]["init-rev-suffix"] if self.is_initial_rev else ""
        self.window_title = f"{self.active_file.basename}{suffix}"
        self.setWindowTitle(self.window_title)
        self.change_revmode(self.revmode)
        self.update_words_button()
        self.update_score_button()
        if self.is_synopsis:
            self.display_text(self.synopsis or self.config["synopsis"])
        else:
            self.display_text(self.get_current_card().iloc[self.side])
        if not self.active_file.tmp:
            self.file_monitor_add_path(self.active_file.filepath)
        ts = self.config.cache["snapshot"]["session"]["timestamp"]
        fcc_queue.put_log(f"Applied a session snapshot from {ts}", log.debug)
        self.config.cache["snapshot"]["session"] = None

    def __onload_notifications(self):
        self.notify_on_outstanding_initial_revisions()
        self.notify_on_mistakes()

    def build_interface(self):
        self.configure_window()
        self.build_layout()
        self.add_shortcuts()
        SideWindows.__init__(self)

    def configure_window(self):
        # Set Window Parameters
        self.setWindowIcon(QtGui.QIcon(os.path.join(self.db.RES_PATH, "icon.png")))
        self.set_geometry(self.config.get_geo("main"))
        self.q_app.setStyle("Fusion")

        # Shortcuts
        self.used_keybindings = set()
        self.nav_mapping = dict()
        for sw_id in {
            "main",
            "load",
            "efc",
            "config",
            "mistakes",
            "stats",
            "progress",
            "timer",
        }:
            self.create_ks_mapping(sw_id)

        # Initialize
        self.popup = NotificationPopup(self)
        self.layout = None
        self.side_window_id: str = "main"
        self.center_window()
        self.show()

    def create_ks_mapping(self, ident: str):
        # create dict[window_id][nagivation]=dummy_function
        # for managing keybindings calls dependent on context of the current side_window
        self.nav_mapping[ident] = {k: lambda: "" for k in self.config["kbsc"].keys()}

    def build_layout(self):
        if self.layout is None:
            self.layout = widget.QGridLayout()
            self.setLayout(self.layout)
        self.LAYOUT_MARGINS = (1, 1, 1, 1)
        self.BUTTONS_HEIGHT = self.config["dim"]["buttons_height"]
        self.layout.setContentsMargins(*self.LAYOUT_MARGINS)
        self.FONT = self.config["theme"]["font"]
        self.FONT_BUTTON_SIZE = self.config["dim"]["font_button_size"]
        self.FONT_TEXTBOX_SIZE = self.config["dim"]["font_textbox_size"]
        self.TEXTBOX_FONT = QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE)
        self.BUTTON_FONT = QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE)

        # Organize Layout
        self.setStyleSheet(self.config["theme"]["main_stylesheet"])
        self.textbox_stylesheet = self.config["theme"]["textbox_stylesheet"]
        self.button_stylesheet = self.config["theme"]["button_stylesheet"]

        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()
        self.layout_next_navigation = widget.QGridLayout()
        self.side_window_layout = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        self.layout.setSpacing(self.config["dim"]["spacing"])
        self.layout_first_row.setSpacing(self.config["dim"]["spacing"])
        self.layout_second_row.setSpacing(self.config["dim"]["spacing"])
        self.layout_third_row.setSpacing(self.config["dim"]["spacing"])
        self.layout_fourth_row.setSpacing(self.config["dim"]["spacing"])
        self.layout_next_navigation.setSpacing(self.config["dim"]["spacing"])
        self.side_window_layout.setSpacing(self.config["dim"]["spacing"])

        # Buttons
        self.next_button = self.create_button(
            self.config["icons"]["next"], self.click_next_button
        )
        self.prev_button = self.create_button(
            self.config["icons"]["prev"], self.click_prev_button
        )
        self.reverse_button = self.create_button(
            self.config["icons"]["reverse"], self.reverse_side
        )
        self.positive_button = self.create_button(
            self.config["icons"]["positive"], self.click_positive
        )
        self.negative_button = self.create_button(
            self.config["icons"]["negative"], self.click_negative
        )
        self.score_button = self.create_button(self.config["icons"]["score"])
        self.save_button = self.create_button(
            self.config["icons"]["save"], self.click_save_button
        )
        self.del_button = self.create_button(
            self.config["icons"]["del"], self.delete_current_card
        )
        self.load_again_button = self.create_button(
            self.config["icons"]["again"], self.load_again_click
        )
        self.words_button = self.create_button(self.config["icons"]["words"])

        # Widgets
        self.layout_second_row.addWidget(self.prev_button, 0, 0)
        self.layout_second_row.addWidget(self.reverse_button, 0, 1)
        self.layout_second_row.addLayout(self.layout_next_navigation, 0, 2)
        self.layout_next_navigation.addWidget(self.next_button, 0, 0)
        self.layout_next_navigation.addWidget(self.negative_button, 0, 0)
        self.layout_next_navigation.addWidget(self.positive_button, 0, 1)
        self.negative_button.hide()
        self.positive_button.hide()
        self.layout_third_row.addWidget(self.load_again_button, 2, 1)
        self.layout_third_row.addWidget(self.del_button, 2, 3)
        self.layout_third_row.addWidget(self.save_button, 2, 4)
        self.layout_fourth_row.addWidget(self.score_button, 3, 0)
        self.layout_fourth_row.addWidget(self.words_button, 3, 3)
        self.create_sod_button()
        self.layout_first_row.addWidget(self.create_textbox(), 0, 0)
        self.create_hint_qbutton()

    def create_sod_button(self):
        self.sod_button = self.create_button(
            self.config["icons"]["sod"], self.get_sod_sidewindow
        )
        self.add_shortcut("sod", self.get_sod_sidewindow, "main")
        self.layout_fourth_row.addWidget(self.sod_button, 3, 4)

    def create_hint_qbutton(self):
        self.hint_qbutton = widget.QPushButton(self.config["icons"]["hint"], self)
        self.hint_qbutton.setFont(QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE))
        self.hint_qbutton.setFixedSize(
            self.config["dim"]["hint_size"], self.config["dim"]["hint_size"]
        )
        self.hint_qbutton.setFocusPolicy(Qt.NoFocus)
        self.hint_qbutton.setStyleSheet(self.config["theme"]["hint_stylesheet"])
        self.hint_qbutton.clicked.connect(self.show_hint)
        self.layout_first_row.addWidget(
            self.hint_qbutton, 0, 0, Qt.AlignBottom | Qt.AlignRight
        )
        self.hint_qbutton.hide()

    def get_scrollbar(self) -> widget.QScrollBar:
        scrollbar = widget.QScrollBar()
        scrollbar.setStyleSheet(self.config["theme"]["scrollbar_stylesheet"])
        return scrollbar

    def set_theme(self):
        for i in self.get_children_layouts(self.layout):
            self.remove_layout(i)
        self.build_layout()
        SideWindows.__init__(self)
        self.display_text(self.get_current_card().iloc[self.side])
        self.update_words_button()

    def update_default_side(self):
        super().update_default_side()

    def create_textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox_last_selection = ""
        self.textbox.setFont(self.TEXTBOX_FONT)
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet(self.textbox_stylesheet)
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)
        self.textbox.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textbox.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.__attach_textbox_ctx()
        self.tb_cal = Caliper(self.TEXTBOX_FONT)
        self.tb_cmg = 0.93
        self.tb_vp = (
            self.tb_cmg * self.config.get_geo("main")[0],
            self.tb_cmg
            * (
                self.config.get_geo("main")[1]
                - 3 * self.config["dim"]["buttons_height"]
            ),
        )
        self.tb_nl = self.tb_vp[1] // self.tb_cal.ls
        self.textbox.showEvent = self.__textbox_show_event
        return self.textbox

    def __textbox_show_event(self, event):
        widget.QTextEdit.showEvent(self.textbox, event)
        self._set_textbox_chr_space()

    def _set_textbox_chr_space(self, event=None):
        _, _, w, h = self.textbox.geometry().getRect()
        self.tb_nl = self.tb_cmg * h // self.tb_cal.sch
        self.tb_vp = (self.tb_cmg * w, self.tb_cmg * h)

    def __attach_textbox_ctx(self):
        self.textbox_ctx = widget.QMenu()
        self.textbox_ctx.setStyleSheet(self.config["theme"]["ctx_stylesheet"])
        self.textbox_ctx.setFont(self.BUTTON_FONT)
        self.textbox.setContextMenuPolicy(Qt.CustomContextMenu)
        copy_action = widget.QAction("Copy", self)
        copy_action.triggered.connect(self.textbox.copy)
        self.textbox_ctx.addAction(copy_action)

        if self.config["lookup"]["mode"] =="auto":
            self.textbox.mouseReleaseEvent = self.__lookup_sod_auto
        else:
            sod_lookup = widget.QAction("Lookup", self)
            if self.config["lookup"]["mode"] == "full":
                sod_lookup.triggered.connect(self.__lookup_sod_full)
            elif self.config["lookup"]["mode"] == "quick":
                sod_lookup.triggered.connect(self.__lookup_sod_quick)
            self.textbox_ctx.addAction(sod_lookup)

        self.textbox.customContextMenuRequested.connect(self.textbox_ctx_menu_open)

    def textbox_ctx_menu_open(self, position):
        self.textbox_ctx.exec_(self.mapToGlobal(position))

    def __lookup_sod_auto(self, event):
        widget.QTextEdit.mouseReleaseEvent(self.textbox, event)
        sel = self.textbox.textCursor().selectedText()
        if sel != self.textbox_last_selection:
            if len(sel) >= 1:
                if self.side == 0:
                    lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.foreign_lng
                else:
                    lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.native_lng
                msg = self.tabs["sod"]["fcc_ins"].sod_object.cli.lookup(sel, lng)
                fcc_queue.put_notification(
                    msg, lvl=LogLvl.important, func=lambda: self.__lookup_sod_full()
                )
                if self.notification_timer:
                    # Immediately show the notification
                    self.notification_timer_func()
            self.textbox_last_selection = sel

    def __lookup_sod_quick(self):
        sel = self.textbox.textCursor().selectedText()
        if self.side == 0:
            lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.foreign_lng
        else:
            lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.native_lng
        msg = self.tabs["sod"]["fcc_ins"].sod_object.cli.lookup(sel, lng)
        fcc_queue.put_notification(
            msg, lvl=LogLvl.important, func=lambda: self.__lookup_sod_full()
        )
        if self.notification_timer:
            # Immediately show the notification
            self.notification_timer_func()

    def __lookup_sod_full(self):
        sel = self.textbox.textCursor().selectedText()
        if self.tabs["sod"]["fcc_ins"].sod_object.can_do_lookup():
            self.activate_tab("sod")
            self.tabs["sod"]["fcc_ins"].sod_object.cli.cls()
            self.tabs["sod"]["fcc_ins"].sod_object.cli.reset_state()
            self.get_sod_sidewindow()
            self.add_cmd_to_log(sel)
            if self.side == 0:
                lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.foreign_lng
            else:
                lng = self.tabs["sod"]["fcc_ins"].sod_object.cli.fh.native_lng
            self.fcc_inst.execute_command(f"{lng} {sel}".split(" "))
            self.move_cursor_to_end()
        else:
            fcc_queue.put_notification(
                "Lookup is unavailable in the current state", lvl=LogLvl.warn
            )

    def create_button(self, text, function=None) -> widget.QPushButton:
        button = widget.QPushButton(self)
        button.setFixedHeight(self.BUTTONS_HEIGHT)
        button.setFont(self.BUTTON_FONT)
        button.setText(text)
        button.setFocusPolicy(Qt.NoFocus)
        button.setStyleSheet(self.button_stylesheet)
        if function is not None:
            button.clicked.connect(function)
        return button

    def create_label(self, text) -> widget.QLabel:
        label = widget.QLabel(self)
        label.setFont(self.BUTTON_FONT)
        label.setText(text)
        label.setFocusPolicy(Qt.NoFocus)
        label.setStyleSheet(self.button_stylesheet)
        return label

    def show_hint(self):
        if not self.is_synopsis:
            self.allow_hide_tips = not self.allow_hide_tips
            self.display_text(self.get_current_card().iloc[self.side])

    def display_text(self, text: str):
        if self.allow_hide_tips and self.should_hide_tips():
            text, chg = self.tips_hide_re.subn("", text)
        else:
            chg = 0

        # Ensure text fits the textbox
        nl = self.tb_cal.strwidth(text) // self.tb_vp[0] + 1
        if nl > self.tb_nl:
            font_size = int(self.FONT_TEXTBOX_SIZE * self.tb_nl / nl)
            qfm = QtGui.QFontMetricsF(QtGui.QFont(self.FONT, font_size))
            nl_ = qfm.horizontalAdvance(text) // self.tb_vp[0] + 1
            margin_top = int((self.tb_vp[1] - qfm.lineSpacing() * nl_) / 2)
        else:
            font_size = self.FONT_TEXTBOX_SIZE
            margin_top = int((self.tb_vp[1] - self.tb_cal.ls * nl - self.tb_cal.ls) / 2)
        margin_top = margin_top if margin_top > 0 else 0
        self.textbox.setFontPointSize(font_size)
        self.textbox.setText(text)
        self.textbox.setViewportMargins(0, margin_top, 0, 0)
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)

        if chg:
            self.hint_qbutton.show()
        else:
            self.hint_qbutton.hide()

    def click_save_button(self):
        if self.active_file.kind == self.db.KINDS.rev:

            if not self.is_recorded:
                fcc_queue.put_notification(
                    "Complete the revision before saving", lvl=LogLvl.warn
                )
            elif self.mistakes_list:
                if self.active_file.filepath in self.config["CRE"]["items"]:
                    self._update_cre(self.active_file)
                    fcc_queue.put_log(self._get_cre_stat())
                if self.should_save_mistakes():
                    self.save_current_mistakes()
                if len(self.mistakes_list) >= self.config["min_eph_cards"]:
                    self.init_eph_from_mistakes()
            else:
                fcc_queue.put_notification("No mistakes to save", lvl=LogLvl.warn)

        elif self.active_file.kind == self.db.KINDS.lng:

            if self.cards_seen != 0:
                super().handle_creating_revision(seconds_spent=self.seconds_spent)
            else:
                fcc_queue.put_notification(
                    "Unable to save an empty file", lvl=LogLvl.warn
                )

        elif self.active_file.kind == self.db.KINDS.mst:

            if (
                self.is_recorded
                and len(self.mistakes_list) >= self.config["min_eph_cards"]
            ):
                self.init_eph_from_mistakes()
            else:
                fcc_queue.put_notification(
                    "Review all mistakes before saving", lvl=LogLvl.warn
                )

        else:

            fcc_queue.put_notification(
                f"Unable to save a {self.db.KFN[self.active_file.kind]}",
                lvl=LogLvl.warn,
            )

    def delete_current_card(self):
        if self.active_file.kind not in self.db.GRADED:
            if not self.is_synopsis:
                super().delete_current_card()
                self.update_words_button()
                fcc_queue.put_notification("Card deleted", lvl=LogLvl.important)
                self.allow_hide_tips = True
                self.display_text(self.get_current_card().iloc[self.side])
        else:
            fcc_queue.put_notification(
                f"Cannot remove cards from a {self.db.KFN[self.active_file.kind]}",
                lvl=LogLvl.warn,
            )

    def reverse_side(self):
        if not self.is_synopsis:
            super().reverse_side()
            self.display_text(self.get_current_card().iloc[self.side])
            if not self.TIMER_RUNNING_FLAG and not self.is_recorded:
                self.start_timer()
                self.start_pace_timer()

    def load_again_click(self):
        if not self.active_file.valid:
            fcc_queue.put_notification("Cannot reload an empty file", lvl=LogLvl.warn)
            return
        elif self.active_file.tmp:
            self.db.shuffle_dataset()
        else:
            self.db.load_dataset(self.active_file)
        self.update_backend_parameters()
        self.update_interface_parameters()

    def initiate_flashcards(self, fd):
        """Manage the whole process of loading a flashcards file"""
        if not self.active_file.tmp:
            self.file_monitor_del_path(self.active_file.filepath)
        self.load_flashcards(fd)
        self.update_backend_parameters()
        self.update_interface_parameters()
        self.del_side_window()
        if not self.active_file.tmp:
            self.file_monitor_add_path(self.active_file.filepath)

    def update_interface_parameters(self):
        suffix = self.config["icons"]["init-rev-suffix"] if self.is_initial_rev else ""
        self.window_title = f"{self.active_file.basename}{suffix}"
        self.setWindowTitle(self.window_title)
        self.change_revmode(self.active_file.kind in self.db.GRADED)
        self.display_text(self.get_current_card().iloc[self.side])
        self.update_words_button()
        self.update_score_button()
        self.reset_timer(clear_indicator=True)
        self.reset_pace_timer()
        self.stop_pace_timer()

    def click_prev_button(self):
        if self.is_synopsis:
            self.current_index += 1
            self.is_synopsis = False
        if self.current_index >= 1:
            self.allow_hide_tips = True
            self.goto_prev_card()
            if self.revmode and self.words_back == 1:
                self.change_revmode(False)
            self.display_text(self.get_current_card().iloc[self.side])
            self.update_words_button()
        if not self.TIMER_RUNNING_FLAG and not self.is_recorded:
            self.start_timer()
            self.start_pace_timer()

    def goto_last_seen_card(self):
        if self.words_back > 0:
            if self.synopsis:
                self.current_index = self.cards_seen
                self.words_back = 0
            else:
                self.current_index = self.cards_seen - 1
                self.words_back = 1
            self.click_next_button()
            self.update_words_button()
            self.update_score_button()

    def click_next_button(self):
        if self.total_words - self.current_index - 1 > 0:
            self.allow_hide_tips = True
            self.goto_next_card()
            if not self.revmode and self.words_back == 0 and not self.is_recorded:
                self.change_revmode(True)
            self.display_text(self.get_current_card().iloc[self.side])
            if not self.TIMER_RUNNING_FLAG and not self.is_recorded:
                self.start_timer()
                self.start_pace_timer()
            self.update_words_button()
            self.update_score_button()
            self.reset_pace_timer()
        elif self.should_create_db_record():
            self.handle_graded_complete()
        else:
            if self.is_synopsis:
                self.handle_final_actions()
            else:
                self.is_synopsis = True
                self.display_text(self.synopsis or self.config["synopsis"])
                self.stop_timer()
                self.stop_pace_timer()

    def handle_final_actions(self):
        if self.active_file.kind == self.db.KINDS.rev:
            self._handle_final_actions_rev()
        elif self.active_file.kind == self.db.KINDS.mst:
            self._handle_final_actions_mst()
        elif self.active_file.kind == self.db.KINDS.eph:
            self._handle_final_actions_eph()
        elif self.active_file.kind == self.db.KINDS.lng:
            self._handle_final_actions_lng()

    def _handle_final_actions_rev(self):
        if (
            self.config["final_actions"]["save_mistakes"]
            and self.should_save_mistakes()
        ):
            self.save_current_mistakes()
        if (
            self.config["final_actions"]["init_ephemeral"]
            and len(self.mistakes_list) >= self.config["min_eph_cards"]
        ):
            self.init_eph_from_mistakes()
            return
        if self.config["final_actions"]["next_efc"]:
            self.load_next_efc()

    def _handle_final_actions_mst(self):
        if (
            self.config["final_actions"]["save_mistakes"]
            and self.should_save_mistakes()
        ):
            self.save_current_mistakes()
        if (
            self.config["final_actions"]["init_ephemeral"]
            and len(self.mistakes_list) >= self.config["min_eph_cards"]
        ):
            self.init_eph_from_mistakes()
            return
        if self.config["final_actions"]["next_efc"]:
            self.load_next_efc()

    def _handle_final_actions_eph(self):
        if (
            self.config["final_actions"]["save_mistakes"]
            and self.should_save_mistakes()
        ):
            self.save_current_mistakes()
        if (
            self.config["final_actions"]["init_ephemeral"]
            and len(self.mistakes_list) >= self.config["min_eph_cards"]
        ):
            self.init_eph_from_mistakes()
            return
        if self.config["final_actions"]["next_efc"]:
            self.load_next_efc()

    def _handle_final_actions_lng(self):
        if self.config["final_actions"]["create_revision"]:
            super().handle_creating_revision(seconds_spent=self.seconds_spent)

    def click_negative(self):
        self.result_negative()
        self.click_next_button()

    def click_positive(self):
        self.result_positive()
        self.click_next_button()

    def handle_graded_complete(self):
        if self.positives + self.negatives == self.total_words:
            self.update_score_button()
            if self.active_file.kind == self.db.KINDS.rev:
                self.synopsis = self.get_rating_message()
            else:
                self.synopsis = self.config["synopsis"]
            self.is_synopsis = True
            self.display_text(self.synopsis)
            self.record_revision_to_db(seconds_spent=self.seconds_spent)
        self.change_revmode(False)
        self.reset_timer(clear_indicator=False)
        self.stop_timer()
        self.stop_pace_timer()
        if (
            self.negatives != 0
            and self.config["mst"]["opt"]["show_mistakes_after_revision"]
        ):
            self.get_mistakes_sidewindow()

    def add_shortcuts(self):
        self.add_shortcut("next", self.ks_nav_next, "main")
        self.add_shortcut("negative", self.ks_nav_negative, "main")
        self.add_shortcut("prev", self.click_prev_button, "main")
        self.add_shortcut("reverse", self.reverse_side, "main")
        self.add_shortcut("del_cur_card", self.delete_current_card, "main")
        self.add_shortcut("load_again", self.load_again_click, "main")
        self.add_shortcut("save", self.click_save_button, "main")
        self.add_shortcut("hint", self.show_hint, "main")
        self.add_shortcut("last_seen", self.goto_last_seen_card, "main")

    def add_shortcut(self, action: str, function, sw_id: str = "main"):
        # binding twice on the same key breaks the shortcut permanently
        key = self.config["kbsc"][action]
        self.nav_mapping[sw_id][action] = function
        if key not in self.used_keybindings:
            self.used_keybindings.add(key)
            shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(lambda: self._exec_ks(action))

    def _exec_ks(self, action):
        self.nav_mapping[self.side_window_id][action]()

    def ks_nav_next(self):
        if self.revmode:
            self.click_positive()
        else:
            self.click_next_button()

    def ks_nav_negative(self):
        if self.revmode:
            self.click_negative()
        else:
            self.click_next_button()

    def open_side_window(self, layout, name):
        if self.config["opt"]["side_by_side"]:
            self.open_side_by_side(layout, name)
        else:
            self.open_in_place(layout, name)
        self.setWindowTitle(self.side_window_titles[name])
        self.stop_timer()
        self.stop_pace_timer()

    def del_side_window(self):
        if self.config["opt"]["side_by_side"]:
            self.del_side_window_side_by_side()
        else:
            self.del_side_window_in_place()
        self.setWindowTitle(self.window_title)
        self.resume_timer()
        self.resume_pace_timer()

    def open_in_place(self, layout, name):
        if self.side_window_id != name:
            if self.side_window_id != "main":
                self.del_side_window_in_place()
            self.add_window_in_place(layout, name)
        else:
            self.del_side_window_in_place()

    def add_window_in_place(self, layout, name):
        self.side_window_layout = layout
        self.set_main_widgets_visibility(False)
        self.layout.addLayout(self.side_window_layout, 0, 0)
        self.side_window_id = name
        self.set_geometry(self.config.get_geo(name))

    def del_side_window_in_place(self):
        self.remove_layout(self.side_window_layout)
        self.set_main_widgets_visibility(True)
        self.side_window_id = "main"
        self.set_geometry(self.config.get_geo("main"))

    def open_side_by_side(self, layout, name):
        if self.side_window_id != name:
            if self.side_window_id != "main":
                self.del_side_window_side_by_side()
            self.add_window_to_side(layout, name)
        else:
            self.del_side_window_side_by_side()

    def add_window_to_side(self, layout, name):
        self.side_window_layout = layout
        self.side_window_id = name
        self.textbox.setFixedWidth(self.textbox.width())
        self.textbox.setFixedHeight(self.textbox.height())
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setFixedWidth(self.config.get_geo(name)[0])
        self.setFixedHeight(self.config.get_geo("main")[1])
        self.setMinimumWidth(self.config.get_geo("main")[0])
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)

    def del_side_window_side_by_side(self):
        self.unfix_size(self)
        self.unfix_size(self.textbox)
        self.remove_layout(self.side_window_layout)
        self.side_window_id = "main"
        self.set_geometry(self.config.get_geo("main"))

    def unfix_size(self, obj):
        obj.setMinimumWidth(0)
        obj.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        obj.setMinimumHeight(0)
        obj.setMaximumHeight(widget.QWIDGETSIZE_MAX)

    def set_main_widgets_visibility(self, show: bool):
        if show:
            for widget in self.get_children_widgets(self.layout):
                widget.show()
            if not self.revmode or self.words_back or self.is_recorded:
                self.positive_button.hide()
                self.negative_button.hide()
            else:
                self.next_button.hide()
            if not self.tips_hide_re.match(self.textbox.toPlainText()):
                self.hint_qbutton.hide()
        else:
            for widget in self.get_children_widgets(self.layout):
                widget.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.side_window_id != "main":
                self.del_side_window()
        elif event.key() == Qt.Key_Return:
            self.nav_mapping[self.side_window_id]["run_command"]()

    def center_window(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())

    def change_revmode(self, new_mode: bool):
        self.revmode = new_mode if self.active_file.kind in self.db.GRADED else False
        if self.revmode:
            self.nav_buttons_visibility_control(True, True, False)
        else:
            self.nav_buttons_visibility_control(False, False, True)

    def nav_buttons_visibility_control(
        self, pos_button: bool, neg_button: bool, next_button: bool
    ):
        if pos_button is True:
            self.positive_button.show()
        else:
            self.positive_button.hide()
        if neg_button is True:
            self.negative_button.show()
        else:
            self.negative_button.hide()
        if next_button is True:
            self.next_button.show()
        else:
            self.next_button.hide()

    def update_words_button(self):
        self.words_button.setText(f"{self.current_index+1}/{self.total_words}")

    def update_score_button(self):
        total = self.positives + self.negatives
        try:
            self.score_button.setText(f"{self.positives/total:.0%}")
        except ZeroDivisionError:
            self.score_button.setText(self.config["icons"]["null-score"])

    def set_geometry(self, rect: tuple[int, int]):
        cur_geo = self.geometry().getRect()
        # x_adj + int((cur_geo[2] - rect[0]) // 2)
        # y_adj + int((cur_geo[3] - rect[1]) // 2)
        self.setGeometry(cur_geo[0], cur_geo[1], rect[0], rect[1])

    # region File Update Monitor
    def file_monitor_handler(self, path):
        if path == self.active_file.filepath and not self.active_file.tmp:
            self.db.load_dataset(self.active_file, seed=self.config["pd_random_seed"])
            if not self.is_synopsis:
                self.display_text(self.get_current_card().iloc[self.side])
            fcc_queue.put_notification("Active dataset refreshed", lvl=LogLvl.info)
        if path == self.config["SOD"]["last_file"]:
            prev_tab = self.active_tab_ident
            self.activate_tab("sod")
            self.tabs["sod"]["fcc_ins"].sod_object.refresh_db()
            self.activate_tab(prev_tab)
        # if path == "./src/res/config.json":
        #     log.debug("Config updated")  # TODO

    def initiate_file_monitor(self):
        self.protected_monitor_paths = set()
        if not self.config["allow_file_monitor"]:
            self.file_watcher = None
        else:
            self.file_watcher = QtCore.QFileSystemWatcher()
            self.file_watcher.fileChanged.connect(self.file_monitor_handler)
            # self.file_watcher.addPath("./src/res/config.json")
            log.debug("FileMonitor Started the watcher", stacklevel=2)

    def file_monitor_add_path(self, path: str):
        if self.file_watcher:
            self.file_watcher.addPath(path)
            log.debug(
                f"FileMonitor Add '{path}'. Status: {self.file_watcher.files()}",
                stacklevel=2,
            )

    def file_monitor_del_path(self, path: str):
        if self.file_watcher:
            if path in self.protected_monitor_paths:
                log.debug(f"FileMonitor Unable to delete a protected path '{path}'")
            else:
                self.file_watcher.removePath(path)
                log.debug(
                    f"FileMonitor Del '{path}'. Status: {self.file_watcher.files()}",
                    stacklevel=2,
                )

    def file_monitor_add_protected_path(self, path: str):
        self.protected_monitor_paths.add(path)
        self.file_monitor_add_path(path)

    def file_monitor_del_protected_path(self, path: str):
        self.protected_monitor_paths.discard(path)
        self.file_monitor_del_path(path)

    def file_monitor_clear(self):
        if self.file_watcher:
            self.file_watcher.removePaths(self.file_watcher.files())
            log.debug(
                f"FileMonitor Unwatched all files. Status: {self.file_watcher.files()}",
                stacklevel=2,
            )

    # endregion

    # region Revision Timer
    def initiate_timer(self):
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        self.timer_prev_text = self.config["icons"]["timer_stop"]
        self.revtimer_hide_timer = self.config["opt"]["hide_timer"]
        self.revtimer_show_cpm_timer = self.config["opt"]["show_cpm_timer"]
        self.set_append_seconds_spent_function()

    def start_timer(self):
        self.timer.start(1000)
        self.TIMER_RUNNING_FLAG = True

    def resume_timer(self):
        if self.conditions_to_resume_timer_are_met():
            self.timer_button.setText(self.timer_prev_text)
            self.start_timer()

    def conditions_to_resume_timer_are_met(self):
        if (
            self.seconds_spent != 0
            and self.is_recorded is False
            and self.side_window_id == "main"
        ):
            conditions_met = True
        else:
            conditions_met = False
        return conditions_met

    def stop_timer(self):
        self.timer.stop()
        self.TIMER_RUNNING_FLAG = False
        self.timer_prev_text = self.timer_button.text()
        self.timer_button.setText(
            self.config["icons"]["timer_stop"]
            if self.is_recorded or not self.seconds_spent
            else self.config["icons"]["timer_pause"]
        )

    def reset_timer(self, clear_indicator=True):
        self.timer.stop()
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        if clear_indicator:
            self.timer_button.setText(self.config["icons"]["timer_stop"])

    def set_append_seconds_spent_function(self):
        self.timer = QTimer()
        if self.revtimer_hide_timer:
            self.append_seconds_spent = self._revtimer_func_hidden
        elif self.revtimer_show_cpm_timer:
            self.append_seconds_spent = self._revtimer_func_cpm
        else:
            self.append_seconds_spent = self._revtimer_func_time
        self.timer.timeout.connect(self.append_seconds_spent)

    def _revtimer_func_hidden(self):
        self.seconds_spent += 1
        self.timer_button.setText(self.config["icons"]["timer_run"])

    def _revtimer_func_cpm(self):
        self.seconds_spent += 1
        cpm = self.cards_seen / (self.seconds_spent / 60)
        self.timer_button.setText(f"{cpm:.0f}")

    def _revtimer_func_time(self):
        self.seconds_spent += 1
        self.timer_button.setText(
            format_seconds_to(self.seconds_spent, "minute", rem=2, sep=":")
        )

    # endregion

    # region Pace Timer
    def initiate_pace_timer(self):
        interval = self.config["pace_card_interval"]
        self.pace_spent = 0
        if interval > 0:
            self.pace_timer = QTimer()
            self.pace_timer_interval = interval
            self.start_pace_timer = self._start_pace_timer
            self.resume_pace_timer = self._resume_pace_timer
            self.stop_pace_timer = self._stop_pace_timer
            self.reset_pace_timer = self._reset_pace_timer
        else:
            self.pace_timer = None
            self.start_pace_timer = lambda: None
            self.resume_pace_timer = lambda: None
            self.stop_pace_timer = lambda: None
            self.reset_pace_timer = lambda: None

    def _start_pace_timer(self):
        self.pace_timer = QTimer()
        self.pace_timer.timeout.connect(self.pace_timer_func)
        self.pace_timer.start(1000)

    def pace_timer_func(self):
        if self.words_back > 0:
            return
        self.pace_spent += 1
        if self.pace_spent >= self.pace_timer_interval:
            self.click_negative()

    def _resume_pace_timer(self):
        if (
            not self.is_recorded
            and self.cards_seen != 0
            and self.side_window_id == "main"
        ):
            self.start_pace_timer()

    def _stop_pace_timer(self):
        self.pace_timer.stop()

    def _reset_pace_timer(self):
        self.pace_spent = 0

    # endregion

    # region Notification Timer
    def initiate_notification_timer(self):
        if self.config["popups"]["enabled"]:
            self.notification_timer = QTimer()
            self.start_notification_timer = self._start_notification_timer
            self.resume_notification_timer = self._resume_notification_timer
            self.stop_notification_timer = self._stop_notification_timer
            self.set_interval_notification_timer = self._set_interval_notification_timer
        else:
            self.notification_timer = None
            self.start_notification_timer = lambda: None
            self.resume_notification_timer = lambda: None
            self.stop_notification_timer = lambda: None
            self.set_interval_notification_timer = lambda i: None

    def _start_notification_timer(self):
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.notification_timer_func)
        self.notification_timer.start(self.config["popups"]["active_interval_ms"])

    def notification_timer_func(self):
        try:
            if fcc_queue.unacked_notifications and not self.popup.is_visible:
                record = fcc_queue.pull_notification()
                self.popup.show_notification(
                    message=record.message, func=record.func, persist=record.persist
                )
                fcc_queue.unacked_notifications -= 1
        except Exception as e:
            log.error(e, exc_info=True)
            fcc_queue.put_notification(
                "Exception raised while pulling a notification. See log file for more details.",
                lvl=LogLvl.exc,
            )

    def _resume_notification_timer(self):
        self.notification_timer.start()

    def _stop_notification_timer(self):
        self.notification_timer.stop()

    def _set_interval_notification_timer(self, i: int):
        self.notification_timer.setInterval(i)

    # endregion

    def remove_layout(self, layout):
        # https://stackoverflow.com/questions/37564728/pyqt-how-to-remove-a-layout-from-a-layout
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                else:
                    self.remove_layout(item.layout())

    def get_children_layouts(self, layout):
        layouts = list()
        for l in layout.children():
            layouts.append(l)
            for w in range(l.count()):
                wdg = l.itemAt(w).widget()
                if wdg is None:
                    layouts.append(l.itemAt(w))
        return layouts

    def get_children_widgets(self, layout) -> set[widget.QPushButton]:
        widgets = set()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                widgets.add(item.widget())
            elif item.layout():
                widgets.update(self.get_children_widgets(item.layout()))
        return widgets

    def eventFilter(self, source, event):
        if isinstance(source, QtGui.QWindow):
            if event.type() == QtCore.QEvent.FocusOut:
                self.__last_focus_out_timer_state = self.TIMER_RUNNING_FLAG
                self.stop_timer()
                self.stop_pace_timer()
                self.set_interval_notification_timer(self.config["popups"]["idle_interval_ms"])
            elif event.type() == QtCore.QEvent.FocusIn:
                if not self.is_synopsis and self.__last_focus_out_timer_state:
                    self.resume_timer()
                    self.resume_pace_timer()
                self.set_interval_notification_timer(self.config["popups"]["active_interval_ms"])
        return super(MainWindowGUI, self).eventFilter(source, event)

    def closeEvent(self, event):
        self.file_monitor_clear()
        if self.active_file.tmp and self.active_file.data.shape[0] > 1:
            self.db.create_tmp_file_backup()
        self.create_session_snapshot()
        self.config.save()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.config.set_geo(self.side_window_id, self.geometry().getRect()[2:])
        try:
            self._set_textbox_chr_space()
            self.tabs["sod"][
                "fcc_ins"
            ].sod_object.cli.__class__.pix_lim.fget.cache_clear()
            self.tabs["sod"][
                "fcc_ins"
            ].sod_object.cli.__class__.lines_lim.fget.cache_clear()
        except AttributeError:
            pass

    def moveEvent(self, a0: QtGui.QMoveEvent) -> None:
        if self.popup.is_visible:
            self.popup.update_position()
        return super().moveEvent(a0)
