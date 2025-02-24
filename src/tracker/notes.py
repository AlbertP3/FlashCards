import logging
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont, QKeyEvent
from cfg import config
from widgets import get_scrollbar

log = logging.getLogger("TRK")


class NotesLayout:

    def __init__(self):
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
        QTextEdit.keyPressEvent(self.qTextEdit, event)
        config.cache["notes"] = self.qTextEdit.toPlainText()

    def get(self) -> QTextEdit:
        return self.qTextEdit
