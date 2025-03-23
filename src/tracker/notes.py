import logging
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtCore import Qt
from typing import TYPE_CHECKING
from cfg import config
from widgets import get_scrollbar

if TYPE_CHECKING:
    from tracker.main import Tracker


log = logging.getLogger("TRK")


class NotesLayout:

    def __init__(self, trk: "Tracker"):
        self.trk = trk
        self.upd = -1
        self._create_text_edit()

    def _create_text_edit(self):
        self.qTextEdit = QTextEdit()
        self.qTextEdit.setFont(config.qfont_textbox)
        self.qTextEdit.setAcceptRichText(False)
        self.qTextEdit.setVerticalScrollBar(get_scrollbar())
        self.qTextEdit.setText(config.cache.get("notes", ""))
        self.qTextEdit.keyPressEvent = self.qte_ks

    def qte_ks(self, event: QKeyEvent):
        event_key = event.key()
        if event_key == Qt.Key_PageDown:
            self.trk.switch_tab(1)
        elif event_key == Qt.Key_PageUp:
            self.trk.switch_tab(-1)
        else:
            QTextEdit.keyPressEvent(self.qTextEdit, event)
            config.cache["notes"] = self.qTextEdit.toPlainText()

    def get(self) -> QTextEdit:
        return self.qTextEdit
