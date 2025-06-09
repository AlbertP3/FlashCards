import re
from typing import Callable
from PyQt5.QtWidgets import (
    QTextEdit,
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PyQt5.QtGui import QTextCursor, QKeyEvent
from PyQt5.QtCore import Qt, QTimer
from data_types import non_space_lng_re
from utils import Caliper
from cfg import config


class TabWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.__can_focus_in = False
        self.__focus_in = lambda: None

    def set_exit(self, fn: Callable):
        self.exit = fn

    def exit(self) -> bool:
        return False

    def set_focus_in(self, fn: Callable):
        self.__focus_in = fn
        self.__can_focus_in = True

    def __allow_focus_in(self):
        self.__can_focus_in = True

    def focus_in(self):
        if self.__can_focus_in:
            self.__can_focus_in = False
            self.__focus_in()
            QTimer.singleShot(500, self.__allow_focus_in)


class BaseConsole(QWidget):

    def __init__(self):
        super().__init__()
        self.tab = TabWidget()
        self.cursor_moved_by_mouse = False
        self.newline = "\n"
        self.console_prompt = "> "
        self.console_log = []
        self.cmd_log = [""]
        self.cmd_cursor = 0
        self.tmp_cmd = ""
        self.init_font()
        self.rt_re = re.compile("[^\u0000-\uFFFF]")

    @property
    def curpos(self) -> int:
        return self.console.textCursor().position()

    @property
    def promptend(self) -> int:
        return (
            self.rt_re.sub("  ", self.console.toPlainText()).rfind(
                f"{self.newline}{self.console_prompt}"
            )
            + len(self.console_prompt)
            + 1
        )

    def get_input(self) -> str:
        return self.console.toPlainText()[self.promptend :]

    def init_font(self):
        self.caliper = Caliper(config.qfont_console, mg=0.96)

    def run_cmd(self):
        raise NotImplementedError

    def init_cross_shortcuts(self):
        k = config["kbsc"]
        self.mw.add_ks(k[self.id], self.open, self.mw)
        self.mw.add_ks(f"{k['mod']}+{k['efc']}", self.mw.efc.open, self.console)
        self.mw.add_ks(
            f"{k['mod']}+{k['next_efc']}", self.mw.efc.load_next_efc, self.console
        )
        self.mw.add_ks(f"{k['mod']}+{k['tracker']}", self.mw.trk.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['config']}", self.mw.cft.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['stats']}", self.mw.sta.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['mistakes']}", self.mw.mst.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['fcc']}", self.mw.fcc.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['sod']}", self.mw.sod.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['load']}", self.mw.ldt.open, self.console)
        self.mw.add_ks(f"{k['mod']}+{k['logs']}", self.mw.log.open, self.console)

    def build(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.console = self.create_console()
        self.layout.addWidget(self.console, stretch=1)
        self.tab.setLayout(self.layout)

    def create_console(self) -> QTextEdit:
        console = QTextEdit()
        console.keyPressEvent = self.cli_shortcuts
        console.setFont(config.qfont_console)
        console.setAcceptRichText(False)
        console.contextMenuEvent = lambda *args, **kwargs: None
        console.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        console.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.overwrite_mouse_press_event(console)
        return console

    def overwrite_mouse_press_event(self, console: QTextEdit):
        original_mouse_press_event = console.mousePressEvent

        def func(event):
            if event.button() == Qt.LeftButton:
                self.cursor_moved_by_mouse = True
            original_mouse_press_event(event)

        console.mousePressEvent = func

    def cli_shortcuts(self, event: QKeyEvent):
        event_key = event.key()
        if event.modifiers() & Qt.ControlModifier:
            if event_key == Qt.Key_L:
                self.cls()
            elif event_key == Qt.Key_V:
                if self.curpos < self.promptend:
                    self.move_cursor_to_end()
                self.console.textCursor().insertText(
                    non_space_lng_re.sub(
                        "",
                        QApplication.clipboard().text().replace("\n", " ").strip(),
                    )
                )
            elif event_key == Qt.Key_X:
                if self.console.textCursor().selectionStart() >= self.promptend:
                    QTextEdit.keyPressEvent(self.console, event)
            elif event_key == Qt.Key_A:
                cursor = self.console.textCursor()
                cursor.setPosition(self.promptend)
                cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                self.console.setTextCursor(cursor)
            elif event_key in {Qt.Key_Backspace, Qt.Key_Left}:
                if self.curpos > self.promptend:
                    QTextEdit.keyPressEvent(self.console, event)
            else:
                QTextEdit.keyPressEvent(self.console, event)
        elif event.modifiers() & Qt.ShiftModifier:
            if event_key == Qt.Key_Home:
                cursor = self.console.textCursor()
                cursor.setPosition(self.promptend, QTextCursor.KeepAnchor)
                self.console.setTextCursor(cursor)
            else:
                QTextEdit.keyPressEvent(self.console, event)
        elif event_key == Qt.Key_Home:
            self.move_cursor_to_start()
        elif event_key == Qt.Key_Return:
            self.run_cmd()
        elif event_key == Qt.Key_Up:
            if self.cmd_cursor == 0:
                self.tmp_cmd = self.console.toPlainText()[self.promptend :]
            self.cmd_cursor -= 1 if -self.cmd_cursor < len(self.cmd_log) else 0
            self.update_console_cmds_nav()
        elif event_key == Qt.Key_Down:
            if self.cmd_cursor != 0:
                self.cmd_cursor += 1
                self.update_console_cmds_nav()
        elif event_key == Qt.Key_Left:
            if self.curpos > self.promptend:
                QTextEdit.keyPressEvent(self.console, event)
            elif self.cursor_moved_by_mouse:
                self.move_cursor_to_start()
        elif event_key == Qt.Key_Backspace:
            has_sel = int(self.console.textCursor().hasSelection())
            if self.curpos + has_sel > self.promptend > 0:
                QTextEdit.keyPressEvent(self.console, event)
            elif self.cursor_moved_by_mouse:
                self.move_cursor_to_start()
        else:
            if self.cursor_moved_by_mouse and self.curpos < self.promptend:
                self.move_cursor_to_end()
            QTextEdit.keyPressEvent(self.console, event)

    def update_console_cmds_nav(self):
        console_content = self.console.toPlainText().split("\n")
        mod_content = console_content[:-1]
        if self.tmp_cmd and self.cmd_cursor == 0:
            c = self.tmp_cmd
            self.tmp_cmd = ""
        else:
            c = self.cmd_log[self.cmd_cursor]
        mod_content.append(f"{self.console_prompt}{c}")
        self.console.setText("\n".join(mod_content))
        self.move_cursor_to_end()

    def add_cmd_to_log(self, cmd: str):
        if cmd:
            try:
                if self.cmd_log[-1] != cmd:
                    self.cmd_log.append(cmd)
                if not self.console_log[-1].endswith(cmd):
                    self.console_log[-1] += cmd
            except IndexError:
                pass
        self.cmd_cursor = 0

    def move_cursor_to_end(self):
        self.console.moveCursor(QTextCursor.End)
        self.cursor_moved_by_mouse = False

    def move_cursor_to_start(self):
        cur = self.console.textCursor()
        cur.setPosition(self.promptend)
        self.console.setTextCursor(cur)
        self.cursor_moved_by_mouse = False

    def cls(self):
        last_line = self.console.toPlainText().split("\n")[-1]
        if last_line.startswith(self.console_prompt):
            new_console_log = [last_line]
            new_text = last_line
        else:
            new_console_log = []
            new_text = ""
        self.console.setText(new_text)
        self.console_log = new_console_log
        self.move_cursor_to_end()


class BaseTab(QWidget):

    def __init__(self):
        super().__init__()
        self.tab = TabWidget()

    def open(self):
        raise NotImplementedError

    def init_cross_shortcuts(self):
        self.mw.add_ks(config["kbsc"][self.id], self.open, self.mw)
        self.mw.add_ks(config["kbsc"]["efc"], self.mw.efc.open, self)
        self.mw.add_ks(config["kbsc"]["next_efc"], self.mw.efc.load_next_efc, self)
        self.mw.add_ks(config["kbsc"]["tracker"], self.mw.trk.open, self)
        self.mw.add_ks(config["kbsc"]["config"], self.mw.cft.open, self)
        self.mw.add_ks(config["kbsc"]["stats"], self.mw.sta.open, self)
        self.mw.add_ks(config["kbsc"]["mistakes"], self.mw.mst.open, self)
        self.mw.add_ks(config["kbsc"]["fcc"], self.mw.fcc.open, self)
        self.mw.add_ks(config["kbsc"]["sod"], self.mw.sod.open, self)
        self.mw.add_ks(config["kbsc"]["load"], self.mw.ldt.open, self)
        self.mw.add_ks(config["kbsc"]["logs"], self.mw.log.open, self)
        self.mw.add_ks(config["kbsc"]["sfe"], self.mw.sfe.open, self)

    def set_box(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(config["theme"]["spacing"])

    def create_label(self, text) -> QLabel:
        label = QLabel()
        label.setFont(config.qfont_button)
        label.setText(text)
        label.setFocusPolicy(Qt.NoFocus)
        return label
