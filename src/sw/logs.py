import os
import json
import logging
import re
from collections import UserDict, deque
from dataclasses import asdict, dataclass
from types import NoneType
from PyQt5.QtGui import (
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QColor,
    QFont,
    QTextCursor,
)
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import Qt, QTime
from widgets import CheckableComboBox
from utils import fcc_queue
from tracker.dal import dal as tracker_dal

log = logging.getLogger("GUI")


class LogHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = [
            (r" EXCEPTION ", QColor("purple")),
            (r" ERROR ", QColor("#990918")),
            (r" WARNING ", QColor("#ad7c28")),
            (r" INFO ", QColor("green")),
            (r" DEBUG ", QColor("#7a5206")),
            (r"^\d+ ", QColor("#505050")),
            (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}", QColor("#505050")),
        ]

    def highlightBlock(self, text):
        for pattern, color in self.rules:
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            fmt.setFontWeight(QFont.Bold)
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class LogsSideWindow:

    def __init__(self):
        self.side_window_titles["logs"] = "Logs"
        self.__phrase = ""
        self.__cur_src = "logs"
        self.add_shortcut("logs", self.get_logs_sidewindow, "main")

    def get_logs_sidewindow(self):
        self.__sources = self.__get_sources()
        self.arrange_logs_window()
        self.open_side_window(self.__logs_layout, "logs")
        self.__load_logs()
        if self.__phrase:
            self.__search()
        self.__console.moveCursor(QTextCursor.End)
        self.__console.ensureCursorVisible()
        self.__search_qle.setFocus()

    def arrange_logs_window(self):
        self.__logs_layout = widget.QGridLayout()
        self.__logs_layout.setContentsMargins(0, 0, 0, 0)
        self.create_log_console()
        self.create_log_src_cbx()
        self.create_log_search_box()
        self.highlighter = LogHighlighter(self.__console.document())
        self.__logs_layout.addWidget(self.__search_qle, 1, 1)
        self.__logs_layout.addWidget(self.__log_src_cbx, 1, 0)
        self.__logs_layout.addWidget(self.__console, 0, 0, 1, 2)

    def create_log_console(self):
        self.__console = widget.QTextEdit(self)
        self.__console.setFont(QFont(self.config["theme"]["console_font"], 8))
        self.__console.setAcceptRichText(False)
        self.__console.setReadOnly(True)
        self.__console.setStyleSheet(self.textbox_stylesheet)
        self.__console.setVerticalScrollBar(self.get_scrollbar())
        self.__console.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.__console.mouseDoubleClickEvent = self.on_log_console_click
        self.__console.keyPressEvent = self.__console_kbsc

    def __console_kbsc(self, event):
        if event.key() == Qt.Key_Home:
            self.__console.verticalScrollBar().setValue(
                self.__console.verticalScrollBar().minimum()
            )
        elif event.key() == Qt.Key_End:
            self.__console.verticalScrollBar().setValue(
                self.__console.verticalScrollBar().maximum()
            )
        else:
            widget.QTextEdit.keyPressEvent(self.__console, event)

    def on_log_console_click(self, event):
        if self.__phrase:
            cursor = self.__console.cursorForPosition(event.pos())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selected_line = cursor.selectedText()
            self.__search_qle.setText("")
            self.__console.find(selected_line)
            scrb = self.__console.verticalScrollBar()
            scrb.setValue(
                scrb.value()
                + self.__console.height()
                - 2 * self.__console.fontMetrics().height()
            )
        else:
            widget.QTextEdit.mousePressEvent(self.__console, event)

    def create_log_src_cbx(self):
        self.__log_src_cbx = CheckableComboBox(
            self,
            allow_multichoice=False,
            width=120,
        )
        self.__log_src_cbx.setMinimumWidth(120)
        self.__log_src_cbx.setStyleSheet(self.button_stylesheet)
        self.__log_src_cbx.setFont(self.BUTTON_FONT)
        for src in self.__sources.keys():
            self.__log_src_cbx.addItem(src, is_checked=src == self.__cur_src)
        self.__log_src_cbx.currentIndexChanged.connect(self.on_log_src_change)

    def on_log_src_change(self):
        new_src = self.__log_src_cbx.currentDataList()[0]
        if new_src == self.__cur_src:
            return
        self.__cur_src = new_src
        self.__search_qle.setText("")
        self.__load_logs()
        self.__console.moveCursor(QTextCursor.End)
        self.__console.ensureCursorVisible()

    def create_log_search_box(self) -> widget.QLineEdit:
        self.__search_qle = widget.QLineEdit(self)
        self.__search_qle.setFont(QFont(self.config["theme"]["console_font"], 8))
        self.__search_qle.setStyleSheet(self.textbox_stylesheet)
        self.__search_qle.setText(self.__phrase)
        self.__search_qle.textChanged.connect(self.__search)

    def __load_logs(self):
        try:
            if self.__sources[self.__cur_src]["type"] == "file":
                with open(self.__sources[self.__cur_src]["path"], "r") as f:
                    self.__content = f.read()
            elif self.__sources[self.__cur_src]["type"] == "json":
                self.__content = json.dumps(
                    self.__sources[self.__cur_src]["fn"](),
                    indent=2,
                    ensure_ascii=False,
                )

            if self.__sources[self.__cur_src]["line_numbers"]:
                content = []
                cnt = 1
                for line in self.__content.split("\n"):
                    content.append(f"{cnt:<3} {line}")
                    cnt += 1
                self.__content = "\n".join(content)

            # Handle multi-line logs
            self.__console.clear()
            for line in self.__content.splitlines():
                self.__console.append(line)

            self.highlighter.rehighlight()
        except Exception as e:
            log.error(e, exc_info=True)
            self.__content = f"Error loading logs: {e}"
            self.__console.setText(self.__content)

    def __search(self):
        phrase = self.__search_qle.text()
        filtered = self.__get_filtered(self.__content, phrase)
        self.__phrase = phrase

        scr_pos = self.__console.verticalScrollBar().value()
        self.__console.setText(filtered)
        self.__console.verticalScrollBar().setValue(scr_pos)

    def __get_filtered(self, text: str, phrase: str) -> str:
        flags = (re.IGNORECASE if phrase == phrase.lower() else 0,)

        try:
            pattern: re.Pattern = re.compile(phrase, sum(flags))
        except re.error:
            pattern: re.Pattern = re.compile(re.escape(phrase), sum(flags))

        filtered = []
        for i in self.__sources[self.__cur_src]["re"].split(text):
            if pattern.search(i):
                filtered.append(i.removesuffix("\n"))

        return "\n".join(filtered)

    def serialize(self, obj):
        res = {}
        if isinstance(obj, (dict, UserDict)):
            for k, v in obj.items():
                res[k] = self.serialize(v)
        elif isinstance(obj, (list, tuple, set, deque)):
            return list(self.serialize(x) for x in obj)
        elif isinstance(obj, (int, float, bool, NoneType)):
            return obj
        elif isinstance(obj, QTime):
            return f"{obj.hour()}:{obj.minute()}:{obj.second()}"
        else:
            return str(obj)
        return res

    def extract_attrs(self, obj, attributes: tuple) -> dict:
        """Extracts selected attributes from an object into a dictionary."""
        return {attr: getattr(obj, attr) for attr in attributes if hasattr(obj, attr)}

    def dataclass_as_dict(self, dc: dataclass, skipkeys: set) -> dict:
        d = {k: v for k, v in asdict(dc).items() if k not in skipkeys}
        return d

    def __get_sources(self):
        return {
            "logs": {
                "path": "fcs.log",
                "line_numbers": False,
                "type": "file",
                "re": re.compile(r"(?=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})"),
            },
            "rev": {
                "path": "src/res/db.csv",
                "line_numbers": True,
                "type": "file",
                "re": re.compile("\n"),
            },
            "duo": {
                "path": "src/res/duo.csv",
                "line_numbers": True,
                "type": "file",
                "re": re.compile("\n"),
            },
            "imm": {
                "path": "src/res/imm.csv",
                "line_numbers": True,
                "type": "file",
                "re": re.compile("\n"),
            },
            "cfg": {
                "type": "json",
                "fn": lambda: self.config.data,
                "line_numbers": False,
                "re": re.compile("\n"),
            },
            "cache": {
                "type": "json",
                "fn": lambda: self.config.cache,
                "line_numbers": False,
                "re": re.compile("\n"),
            },
            "file": {
                "path": self.active_file.filepath,
                "line_numbers": True,
                "type": "file",
                "re": re.compile("\n"),
            },
            "props": {
                "type": "json",
                "line_numbers": True,
                "re": re.compile(r"\n"),
                "fn": lambda: self.serialize(
                    {
                        "main": {
                            **self.extract_attrs(
                                self,
                                (
                                    "current_index",
                                    "words_back",
                                    "cards_seen_sides",
                                    "default_side",
                                    "side",
                                    "revmode",
                                    "is_initial_rev",
                                    "positives",
                                    "negatives",
                                    "total_words",
                                    "cards_seen",
                                    "synopsis",
                                    "is_recorded",
                                    "tips_hide_re",
                                    "allow_hide_tips",
                                    "allow_hide_tips",
                                    "mistakes_saved",
                                    "is_revision",
                                    "side_window_titles",
                                    "notification_timer",
                                    "pace_spent",
                                    "pace_timer_interval",
                                    "seconds_spent",
                                    "TIMER_RUNNING_FLAG",
                                    "timer",
                                    "pace_timer",
                                    "notification_timer",
                                ),
                            ),
                            "should_hide_tips": self.should_hide_tips(),
                            "active_file_path": self.active_file.filepath,
                        },
                        "db": {
                            **self.extract_attrs(
                                self.db,
                                (
                                    "KINDS",
                                    "KFN",
                                    "GRADED",
                                    "RES_PATH",
                                    "DB_PATH",
                                    "TMP_BACKUP_PATH",
                                    "REV_DIR",
                                    "LNG_DIR",
                                    "MST_DIR",
                                    "TSFORMAT",
                                    "MST_BASENAME",
                                    "DB_COLS",
                                    "filters",
                                    "last_update",
                                    "last_load",
                                ),
                            ),
                            "files": {
                                k: self.dataclass_as_dict(
                                    fd,
                                    {"data"},
                                )
                                for k, fd in self.db.files.items()
                            },
                        },
                        "sod.cli": {
                            **self.extract_attrs(
                                self.tabs["sod"]["fcc_ins"].sod_object.cli,
                                (
                                    "transl",
                                    "phrase",
                                    "queue_dict",
                                    "selection_queue",
                                    "status_message",
                                    "pix_lim",
                                    "lines_lim",
                                ),
                            ),
                        },
                        "sod.dicts": self.extract_attrs(
                            self.tabs["sod"]["fcc_ins"].sod_object.cli.dicts,
                            (
                                "available_dicts",
                                "dict_service",
                                "word",
                                "source_lng",
                                "target_lng",
                                "available_lngs",
                            ),
                        ),
                        "sod.cli.fh": self.extract_attrs(
                            self.tabs["sod"]["fcc_ins"].sod_object.cli.fh,
                            (
                                "path",
                                "filename",
                                "dtracker",
                                "last_write_time",
                                "native_lng",
                                "foreign_lng",
                                "total_rows",
                            ),
                        ),
                        "fcc_queue": vars(fcc_queue),
                        "env": {
                            k: v
                            for k, v in os.environ.items()
                            if k
                            in {
                                "QT_QPA_PLATFORM",
                                "QT_SCALE_FACTOR",
                                "QT_AUTO_SCREEN_SCALE_FACTOR",
                                "XDG_SESSION_TYPE",
                                "_",
                                "PWD",
                            }
                        },
                        "tracker.dal": self.extract_attrs(
                            tracker_dal,
                            (
                                "upd",
                                "last_tab",
                                "stopwatch_running",
                                "stopwatch_elapsed",
                            ),
                        ),
                    }
                ),
            },
        }
