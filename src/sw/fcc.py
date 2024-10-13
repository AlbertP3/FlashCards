import re
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from data_types import non_space_lng_re
from typing import Callable
from fcc import FCC
from utils import Caliper, fcc_queue


class FccSideWindow:

    def __init__(self):
        self.console: widget.QTextEdit
        self.cursor_moved_by_mouse = False
        self.DEFAULT_PS1 = self.config["theme"]["default_ps1"]
        self.init_font()
        self.__create_tabs()
        self.add_shortcut("fcc", self.get_fcc_sidewindow, "main")
        self.newline = "\n"
        self.rt_re = re.compile("[^\u0000-\uFFFF]")

    def __create_tabs(self):
        self.active_tab_ident = None
        self.console = None
        self.tabs = dict()

        self.create_tab(
            ident="fcc",
            window_title="Console",
            console_prompt=self.DEFAULT_PS1,
            get_x_sidewindow=self.__get_fcc_sidewindow,
            run_x_command=self.run_fcc_command,
        )

        self.create_tab(
            ident="sod",
            window_title="Search Online Dictionaries",
            console_prompt=self.DEFAULT_PS1,
            get_x_sidewindow=self.__get_fcc_sidewindow,
            run_x_command=self.run_fcc_command,
        )
        self.activate_tab("sod")
        self.console.setGeometry(0, 0, *self.config["geo"]["sod"])
        self.tabs["sod"]["fcc_instance"].sod([])

        self.activate_tab("fcc")

    def create_tab(
        self,
        ident: str,
        window_title: str,
        console_prompt: str,
        get_x_sidewindow: Callable,
        run_x_command: Callable,
    ):
        self.tabs[ident] = {
            "window_title": window_title,
            "console": self.create_console(),
            "console_prompt": console_prompt,
            "console_log": list(),
            "cmds_log": [""],
            "tmp_cmd": "",
            "cmds_cursor": 0,
            "get_x_sidewindow": get_x_sidewindow,
            "run_x_command": run_x_command,
            "fcc_instance": FCC(self),
        }
        self.side_window_titles[ident] = window_title
        self.create_ks_mapping(ident)
        self.add_shortcut("run_command", run_x_command, ident)

    def activate_tab(self, ident: str):
        if self.active_tab_ident == ident:
            return
        elif self.active_tab_ident:
            self._deactivate_tab()
        self.CONSOLE_PROMPT = self.tabs[ident]["console_prompt"]
        self.CONSOLE_LOG = self.tabs[ident]["console_log"]
        self.CMDS_LOG = self.tabs[ident]["cmds_log"]
        self.CMDS_CURSOR = self.tabs[ident]["cmds_cursor"]
        self.console = self.tabs[ident]["console"]
        self.fcc_inst = self.tabs[ident]["fcc_instance"]
        self.fcc_inst.update_console_id(self.tabs[ident]["console"])
        self.tmp_cmd = self.tabs[ident]["tmp_cmd"]
        self.get_terminal_sidewindow = self.tabs[ident]["get_x_sidewindow"]
        self.run_command = self.tabs[ident]["run_x_command"]
        self.active_tab_ident = ident

    def _deactivate_tab(self):
        try:
            self.tabs[self.active_tab_ident]["console_prompt"] = self.CONSOLE_PROMPT
            self.tabs[self.active_tab_ident]["console_log"] = self.CONSOLE_LOG.copy()
            self.tabs[self.active_tab_ident]["cmds_log"] = self.CMDS_LOG.copy()
            self.tabs[self.active_tab_ident]["cmds_cursor"] = self.CMDS_CURSOR
            self.tabs[self.active_tab_ident]["tmp_cmd"] = self.tmp_cmd
            self.active_tab_ident = None
        except KeyError:
            pass

    def __get_fcc_sidewindow(self):
        """Shared method for initializing the terminal"""
        self.arrange_fcc_window()
        self.open_side_window(self.fcc_layout, self.active_tab_ident)
        self.console.setFocus()
        self.move_cursor_to_end()

    def get_fcc_sidewindow(self):
        """Open FCC terminal directly"""
        self.activate_tab("fcc")
        self.get_terminal_sidewindow()

    def get_sod_sidewindow(self):
        """Open SOD terminal directly"""
        self.activate_tab("sod")
        self.get_terminal_sidewindow()

    def init_font(self):
        self.CONSOLE_FONT = QtGui.QFont(
            self.config["theme"]["console_font"],
            self.config["theme"]["console_font_size"],
        )
        self.caliper = Caliper(QtGui.QFontMetricsF(self.CONSOLE_FONT))

    @property
    def curpos(self) -> int:
        return self.console.textCursor().position()

    @property
    def promptend(self) -> int:
        return (
            self.rt_re.sub("  ", self.console.toPlainText()).rfind(
                f"{self.newline}{self.CONSOLE_PROMPT}"
            )
            + len(self.CONSOLE_PROMPT)
            + 1
        )

    def get_input(self) -> str:
        return self.console.toPlainText()[self.promptend :]

    def arrange_fcc_window(self):
        self.fcc_layout = widget.QGridLayout()
        if self.CONSOLE_LOG:
            self.CONSOLE_LOG[:-1] = [
                i for i in self.CONSOLE_LOG[:-1] if i != self.CONSOLE_PROMPT
            ]
            if self.CONSOLE_LOG[-1].startswith(self.CONSOLE_PROMPT):
                self.CONSOLE_LOG[-1] = self.CONSOLE_PROMPT
                self.tmp_cmd = self.console.toPlainText().split("\n")[-1][
                    len(self.CONSOLE_PROMPT) :
                ]
            else:
                self.CONSOLE_LOG.append(self.CONSOLE_PROMPT)
        else:
            self.CONSOLE_LOG = [self.CONSOLE_PROMPT]
        # Dump fcc_queue while preserving the prompt content
        if self.active_tab_ident == "fcc":
            cmd = self.CONSOLE_LOG.pop()
            self.console.setText("\n".join(self.CONSOLE_LOG))
            for msg in fcc_queue.dump():
                self.fcc_inst.post_fcc(
                    f"[{msg.timestamp.strftime('%H:%M:%S')}] {msg.message}"
                )
            self.console.append(cmd + self.tmp_cmd)
            self.CONSOLE_LOG.append(cmd)
        self.fcc_layout.addWidget(self.console, 0, 0)

    def create_console(self) -> widget.QTextEdit:
        console = widget.QTextEdit(self)
        console.keyPressEvent = self.cli_shortcuts
        console.setFont(self.CONSOLE_FONT)
        console.setAcceptRichText(False)
        console.setStyleSheet(self.textbox_stylesheet)
        console.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        console.contextMenuEvent = lambda *args, **kwargs: None
        self.overwrite_mouse_press_event(console)
        return console

    def overwrite_mouse_press_event(self, console: widget.QTextEdit):
        original_mouse_press_event = console.mousePressEvent

        def func(event):
            if event.button() == Qt.LeftButton:
                self.cursor_moved_by_mouse = True
            original_mouse_press_event(event)

        console.mousePressEvent = func

    def cli_shortcuts(self, event: QtGui.QKeyEvent):
        event_key = event.key()
        if event.modifiers() & Qt.ControlModifier:
            if event_key == Qt.Key_L:
                self.fcc_inst.execute_command(["cls"], followup_prompt=False)
            elif event_key == Qt.Key_V:
                if self.curpos < self.promptend:
                    self.move_cursor_to_end()
                self.console.textCursor().insertText(
                    non_space_lng_re.sub(
                        "",
                        widget.QApplication.clipboard()
                        .text()
                        .replace("\n", " ")
                        .strip(),
                    )
                )
            elif event_key == Qt.Key_X:
                if self.console.textCursor().selectionStart() >= self.promptend:
                    widget.QTextEdit.keyPressEvent(self.console, event)
            elif event_key == Qt.Key_A:
                self.cursor_moved_by_mouse = True
                widget.QTextEdit.keyPressEvent(self.console, event)
            elif event_key in {Qt.Key_Backspace, Qt.Key_Left}:
                if self.curpos > self.promptend:
                    widget.QTextEdit.keyPressEvent(self.console, event)
            else:
                widget.QTextEdit.keyPressEvent(self.console, event)
        elif event_key == Qt.Key_Home:
            self.move_cursor_to_start()
        elif event_key == Qt.Key_Return:
            self.nav_mapping[self.side_window_id]["run_command"]()
        elif event_key == Qt.Key_Up:
            if self.CMDS_CURSOR == 0:
                self.tmp_cmd = self.console.toPlainText()[self.promptend :]
            self.CMDS_CURSOR -= 1 if -self.CMDS_CURSOR < len(self.CMDS_LOG) else 0
            self.update_console_cmds_nav()
        elif event_key == Qt.Key_Down:
            if self.CMDS_CURSOR != 0:
                self.CMDS_CURSOR += 1
                self.update_console_cmds_nav()
        elif event_key in {Qt.Key_Left, Qt.Key_Backspace}:
            if self.curpos > self.promptend:
                widget.QTextEdit.keyPressEvent(self.console, event)
            elif self.cursor_moved_by_mouse:
                self.move_cursor_to_start()
        else:
            if self.cursor_moved_by_mouse and self.curpos < self.promptend:
                self.move_cursor_to_end()
            widget.QTextEdit.keyPressEvent(self.console, event)

    def update_console_cmds_nav(self):
        console_content = self.console.toPlainText().split("\n")
        mod_content = console_content[:-1]
        if self.tmp_cmd and self.CMDS_CURSOR == 0:
            c = self.tmp_cmd
            self.tmp_cmd = ""
        else:
            c = self.CMDS_LOG[self.CMDS_CURSOR]
        mod_content.append(f"{self.CONSOLE_PROMPT}{c}")
        self.console.setText("\n".join(mod_content))
        self.move_cursor_to_end()

    def add_cmd_to_log(self, cmd: str):
        if cmd:
            if self.CMDS_LOG[-1] != cmd:
                self.CMDS_LOG.append(cmd)
            if not self.CONSOLE_LOG[-1].endswith(cmd):
                self.CONSOLE_LOG[-1] += cmd
        self.CMDS_CURSOR = 0

    def run_fcc_command(self):
        cmd = self.console.toPlainText().split("\n")[-1][len(self.CONSOLE_PROMPT) :]
        self.add_cmd_to_log(cmd)
        self.fcc_inst.execute_command(cmd.split(" "))
        self.move_cursor_to_end()

    def move_cursor_to_end(self):
        self.console.moveCursor(QtGui.QTextCursor.End)
        self.cursor_moved_by_mouse = False

    def move_cursor_to_start(self):
        cur = self.console.textCursor()
        cur.setPosition(self.promptend)
        self.console.setTextCursor(cur)
        self.cursor_moved_by_mouse = False
