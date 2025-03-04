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
from PyQt5.QtWidgets import QWidget, QGridLayout, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QTime
from widgets import CheckableComboBox, get_scrollbar
from utils import fcc_queue
from cfg import config
from tracker.dal import dal as tracker_dal
from tabs.base import BaseTab
from DBAC import db_conn

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


class LogsTab(BaseTab):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.id = "logs"
        self.phrase = ""
        self.cur_src = "logs"
        self.sources = self.__get_sources()
        self.build()
        self.mw.tab_names[self.id] = "Logs"
        self.mw.add_tab(self._tab, self.id)

    def open(self, scroll_end = False):
        self.mw.switch_tab(self.id)
        scr_pos = self.console.verticalScrollBar().value()
        self.load_logs()
        if self.phrase:
            self.search()
        self.search_qle.setFocus()
        if scroll_end:
            self.scroll_to_bottom()
        else:
            self.console.verticalScrollBar().setValue(scr_pos)

    def build(self):
        self._tab = QWidget()
        self.logs_layout = QGridLayout()
        self.logs_layout.setContentsMargins(0, 0, 0, 0)
        self.create_log_console()
        self.create_log_src_cbx()
        self.create_log_search_box()
        self.highlighter = LogHighlighter(self.console.document())
        self.logs_layout.addWidget(self.search_qle, 1, 1)
        self.logs_layout.addWidget(self.log_src_cbx, 1, 0)
        self.logs_layout.addWidget(self.console, 0, 0, 1, 2)
        self.set_box(self.logs_layout)
        self._tab.setLayout(self.logs_layout)

    def create_log_console(self):
        self.console = QTextEdit()
        self.console.setFont(config.qfont_logs)
        self.console.setAcceptRichText(False)
        self.console.setReadOnly(True)
        self.console.setVerticalScrollBar(get_scrollbar())
        self.console.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.console.mouseDoubleClickEvent = self.on_log_console_click
        self.console.keyPressEvent = self.console_kbsc

    def console_kbsc(self, event):
        if event.key() == Qt.Key_Home:
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().minimum()
            )
        elif event.key() == Qt.Key_End:
            self.scroll_to_bottom()
        else:
            QTextEdit.keyPressEvent(self.console, event)

    def scroll_to_bottom(self):
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )

    def on_log_console_click(self, event):
        if self.phrase:
            cursor = self.console.cursorForPosition(event.pos())
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selected_line = cursor.selectedText()
            self.search_qle.setText("")
            self.console.find(selected_line)
            scrb = self.console.verticalScrollBar()
            scrb.setValue(
                scrb.value()
                + self.console.height()
                - 2 * self.console.fontMetrics().height()
            )
        else:
            QTextEdit.mousePressEvent(self.console, event)

    def create_log_src_cbx(self):
        self.log_src_cbx = CheckableComboBox(
            None,
            allow_multichoice=False,
            width=120,
        )
        self.log_src_cbx.setMinimumWidth(120)
        self.log_src_cbx.setFont(config.qfont_button)
        for src in self.sources.keys():
            self.log_src_cbx.addItem(src, is_checked=src == self.cur_src)
        self.log_src_cbx.currentIndexChanged.connect(self.on_log_src_change)

    def on_log_src_change(self):
        new_src = self.log_src_cbx.currentDataList()[0]
        if new_src == self.cur_src:
            return
        self.cur_src = new_src
        self.search_qle.setText("")
        self.load_logs()

    def create_log_search_box(self) -> QLineEdit:
        self.search_qle = QLineEdit()
        self.search_qle.setFont(config.qfont_logs)
        self.search_qle.setText(self.phrase)
        self.search_qle.textChanged.connect(self.search)
        self.search_qle.keyPressEvent = self.search_kbsc

    def search_kbsc(self, event):
        if event.key() == Qt.Key_Home:
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().minimum()
            )
        elif event.key() == Qt.Key_End:
            self.console.verticalScrollBar().setValue(
                self.console.verticalScrollBar().maximum()
            )
        else:
            QLineEdit.keyPressEvent(self.search_qle, event)

    def load_logs(self):
        try:
            if self.sources[self.cur_src]["type"] == "file":
                with open(self.sources[self.cur_src]["path"], "r") as f:
                    self._content = f.read()
            elif self.sources[self.cur_src]["type"] == "json":
                self._content = json.dumps(
                    self.sources[self.cur_src]["fn"](),
                    indent=2,
                    ensure_ascii=False,
                )

            if self.sources[self.cur_src]["line_numbers"]:
                content = []
                cnt = 1
                for line in self._content.split("\n"):
                    content.append(f"{cnt:<3} {line}")
                    cnt += 1
                self._content = "\n".join(content)

            # Handle multi-line logs
            self.console.clear()
            for line in self._content.splitlines():
                self.console.append(line)

            self.highlighter.rehighlight()
        except Exception as e:
            log.error(e, exc_info=True)
            self._content = f"Error loading logs: {e}"
            self.console.setText(self._content)

    def search(self):
        phrase = self.search_qle.text()
        filtered = self.__get_filtered(self._content, phrase)
        self.phrase = phrase

        scr_pos = self.console.verticalScrollBar().value()
        self.console.setText(filtered)
        self.console.verticalScrollBar().setValue(scr_pos)

    def __get_filtered(self, text: str, phrase: str) -> str:
        flags = (re.IGNORECASE if phrase == phrase.lower() else 0,)

        try:
            pattern: re.Pattern = re.compile(phrase, sum(flags))
        except re.error:
            pattern: re.Pattern = re.compile(re.escape(phrase), sum(flags))

        filtered = []
        for i in self.sources[self.cur_src]["re"].split(text):
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
                "fn": lambda: config.data,
                "line_numbers": False,
                "re": re.compile("\n"),
            },
            "cache": {
                "type": "json",
                "fn": lambda: config.cache,
                "line_numbers": False,
                "re": re.compile("\n"),
            },
            "file": {
                "path": self.mw.active_file.filepath,
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
                                self.mw,
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
                                    "tab_names",
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
                            "efc_recoms": self.mw.efc._recoms,
                            "_efc_last_calc_time": self.mw.efc._efc_last_calc_time,
                            "_db_load_time_efc": self.mw.efc._db_load_time_efc,
                            "cur_efc_index": self.mw.efc.cur_efc_index,
                            "efc_files_count": self.mw.efc.files_count,
                            "should_hide_tips": self.mw.should_hide_tips(),
                            "active_file_path": self.mw.active_file.filepath,
                        },
                        "db": {
                            **self.extract_attrs(
                                db_conn,
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
                                for k, fd in db_conn.files.items()
                            },
                        },
                        "sod.cli": {
                            **self.extract_attrs(
                                self.mw.sod.sod.cli,
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
                            self.mw.sod.sod.cli.dicts,
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
                            self.mw.sod.sod.cli.fh,
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
