import re
from PyQt5.QtWidgets import (
    QComboBox,
    QStyledItemDelegate,
    qApp,
    QWidget,
    QGridLayout,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QDialog,
    QFormLayout,
    QLineEdit,
    QScrollBar,
    QApplication,
    QDialogButtonBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QToolTip,
)
from PyQt5.QtCore import (
    Qt,
    QPropertyAnimation,
    QTimer,
    QEvent,
    QPoint,
    QObject,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QPalette,
    QFontMetrics,
    QStandardItem,
    QKeyEvent,
    QKeySequence,
)
from collections import OrderedDict
from typing import Callable, Optional, TYPE_CHECKING
from utils import is_valid_filename, parse_to_seconds
from int import fcc_queue, LogLvl, sbus
from data_types import CreateFileDialogData
from DBAC import db_conn, FileDescriptor
from cfg import config

if TYPE_CHECKING:
    from sfe.fh import FileHandler


def get_button(
    parent=None,
    text="",
    function=None,
    tooltip: str = "",
    dtip: Callable = None,
) -> QPushButton:
    button = QPushButton(parent)
    button.setFont(config.qfont_button)
    button.setText(text)
    button.setFocusPolicy(Qt.NoFocus)
    if tooltip:
        button.setToolTip(tooltip)
    if dtip:

        def show_dynamic_tooltip(event):
            QToolTip.showText(
                button.mapToGlobal(QPoint(0, button.height())),
                dtip(),
                button,
            )

        button.enterEvent = show_dynamic_tooltip
    if function:
        button.clicked.connect(function)
        button.setCursor(Qt.PointingHandCursor)
    return button


def get_scrollbar() -> QScrollBar:
    scrollbar = QScrollBar()
    scrollbar.setCursor(Qt.PointingHandCursor)
    return scrollbar


class CheckableComboBox(QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            return size

    def __init__(
        self,
        layout,
        allow_multichoice: bool = True,
        width: float = 0,
        hide_on_checked: bool = False,
        on_popup_show: Callable = lambda: None,
    ):
        self.allow_multichoice = allow_multichoice
        self.hide_on_checked = hide_on_checked
        self._width = width or self.lineEdit().width()
        self.on_popup_show = on_popup_show
        super().__init__(layout)

        # Make the combo editable to set a custom text, but readonly
        self.setFont(config.qfont_button)
        self.setMinimumWidth(1)
        self.setEditable(True)
        palette = qApp.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setAlignment(Qt.AlignCenter)

        # Use custom delegate
        self.setItemDelegate(CheckableComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, object, event):

        if object == self.lineEdit():
            if event.type() == QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if object == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if not self.allow_multichoice:
                    for i in range(self.model().rowCount()):
                        self.model().item(i).setCheckState(Qt.Unchecked)

                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)
                    if self.hide_on_checked:
                        self.hidePopup()
                return True
        return False

    def showPopup(self):
        self.on_popup_show()
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        checked_items = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                checked_items.append(self.model().item(i).text())

        if len(checked_items) == 1:
            text = checked_items[0]
        else:
            text = f"{len(checked_items) or 'No'} items selected"

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.ElideRight, self._width)
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data=None, is_checked=False):
        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData([Qt.Unchecked, Qt.Checked][is_checked], Qt.CheckStateRole)
        self.model().appendRow(item)

    def setChecked(self, index: int):
        if not self.allow_multichoice:
            for i in range(self.model().rowCount()):
                self.model().item(i).setCheckState(Qt.Unchecked)
        self.model().item(index).setCheckState(Qt.Checked)

    def addItems(self, texts: list[str], datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentDataList(self) -> list:
        """Return the list of selected items data"""
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                res.append(self.model().item(i).data())
        return res

    def currentDataDict(self) -> dict:
        """Return the dict {item: is_selected}"""
        res = dict()
        for i in range(self.model().rowCount()):
            res[self.model().item(i).data()] = (
                self.model().item(i).checkState() == Qt.Checked
            )
        return res

    def getData(self) -> list:
        res = list()
        for i in range(self.model().rowCount()):
            res.append(self.model().item(i).data())
        return res

    def wheelEvent(self, *args, **kwargs):
        """Disable scrolling"""
        return


class ScrollableOptionsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.__create_layout()
        self.pos = self.__list_pos_gen()

    def __create_layout(self):
        self.layout = QGridLayout()
        self.layout.setHorizontalSpacing(1)
        self.layout.setVerticalSpacing(1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def add_widget(self, button: QPushButton, label: QLabel):
        self.layout.addWidget(label, next(self.pos), 0)
        self.layout.addWidget(button, next(self.pos), 1)

    def add_label(self, text: str):
        label = QLabel()
        label.setFont(config.qfont_button)
        label.setText(text)
        label.setFocusPolicy(Qt.NoFocus)
        label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(label, next(self.pos), 0, 1, 2)
        next(self.pos)

    def add_spacer(self) -> QLabel:
        spacer = QLabel()
        spacer.setFocusPolicy(Qt.NoFocus)
        spacer.setFont(config.qfont_button)
        self.layout.addWidget(spacer, next(self.pos), 0, 1, 2)
        next(self.pos)

    def __list_pos_gen(self):
        """increments iterator every 2 calls"""
        i = 0
        while True:
            yield int(i)
            i += 0.5


class NotificationPopup(QWidget):

    def __init__(self, parent: QWidget = None):
        super(NotificationPopup, self).__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.installEventFilter(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 0)
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFont(config.qfont_button)
        self.label.setObjectName("notification")
        layout.addWidget(self.label)
        self.__configure_animations()
        self.__func = lambda: None
        self.is_visible = False
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)

    def __configure_animations(self):
        self.enter_animation = QPropertyAnimation(self, b"windowOpacity")
        self.enter_animation.setDuration(config["popups"]["show_animation_ms"])
        self.enter_animation.setStartValue(0.8)
        self.enter_animation.setEndValue(1)
        self.exit_animation = QPropertyAnimation(self, b"windowOpacity")
        self.exit_animation.setDuration(config["popups"]["hide_animation_ms"])
        self.exit_animation.setStartValue(1)
        self.exit_animation.setEndValue(0.8)
        self.exit_animation.finished.connect(self.close_notification)

    def show_notification(
        self,
        message: str,
        func: Optional[Callable] = None,
        *args,
        **kwargs,
    ):
        self.label.setText(message)
        if callable(func):
            self.__func = lambda: func(*args, **kwargs)
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.__func = lambda: None
            self.setCursor(Qt.ArrowCursor)
        self.show()
        self.update_position()
        self.enter_animation.start()
        if QApplication.activeWindow():
            self.timer.start(config["popups"]["timeout_ms"])
        self.is_visible = True

    def update_position(self):
        pargeo = self.parent().geometry()
        x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
        self.move(x, pargeo.y())

    def hide_notification(self):
        self.exit_animation.start()

    def close_notification(self):
        self.exit_animation.stop()
        self.enter_animation.stop()
        self.close()
        self.timer.stop()
        self.is_visible = False
        if fcc_queue.unacked_notifications:
            sbus.fcc_queue_msg.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.__func()
            self.close_notification()
        elif event.button() == Qt.RightButton:
            self.close_notification()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Enter:
            self.timer.stop()
        elif event.type() == QEvent.Leave:
            self.timer.start(config["popups"]["timeout_ms"])
        return super(NotificationPopup, self).eventFilter(source, event)


class CFIDialog(QDialog):
    def __init__(self, parent, start: int, cnt: int):
        super().__init__(parent)
        self.setFont(config.qfont_button)
        self.setWindowTitle(" ")
        self.setMinimumWidth(250)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(config["theme"]["spacing"])
        self.form_layout = QFormLayout()
        self.start_qle = self.create_qle(str(start))
        self.start_qle.textChanged.connect(self.validate)
        self.cnt_qle = self.create_qle()
        self.cnt_qle.setText(f"{cnt}")
        self.cnt_qle.setPlaceholderText("<END>")
        self.cnt_qle.textChanged.connect(self.validate)
        self.total_qle = self.create_qle(f"{start+cnt}")
        self.total_qle.setFocusPolicy(Qt.NoFocus)
        self.total_qle.setReadOnly(True)
        self.allow_score_cbx = CheckableComboBox(
            parent, allow_multichoice=False, width=250, hide_on_checked=True
        )
        self.allow_score_cbx.addItem(
            "Yes", True, is_checked=config["opt"]["graded_cfi"]
        )
        self.allow_score_cbx.addItem(
            "No", False, is_checked=not config["opt"]["graded_cfi"]
        )
        self.form_layout.addRow("Total", self.total_qle)
        self.form_layout.addRow("From ", self.start_qle)
        self.form_layout.addRow("Count", self.cnt_qle)
        self.form_layout.addRow("Graded", self.allow_score_cbx)
        self.layout.addLayout(self.form_layout)
        self.submit_btn = get_button(self, "Create", self.accept)
        self.layout.addWidget(self.submit_btn)
        self.setLayout(self.layout)
        self.validate()

    def keyPressEvent(self, event: QKeyEvent):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.submit_btn.isEnabled():
                    return self.accept()
        return super().keyPressEvent(event)

    def validate(self):
        try:
            start = int(self.start_qle.text())
            total = int(self.total_qle.text())
            if start < total:
                msg = "Create"
                res = True
            else:
                msg = "Not enough cards"
                res = False
        except ValueError:
            msg = "Invalid Data"
            res = False
        self.submit_btn.setText(msg)
        self.submit_btn.setEnabled(res)

    def get_values(self) -> tuple[int, int, bool]:
        """Returns start index and count"""
        if start := self.start_qle.text():
            start = int(start)
        else:
            start = 0

        if cnt := self.cnt_qle.text():
            cnt = int(cnt)
        else:
            cnt = 0

        is_score_allowed = self.allow_score_cbx.currentDataList()[0]

        return start, cnt, is_score_allowed

    def create_qle(self, text: str = "") -> QLineEdit:
        qle = QLineEdit()
        qle.setFont(config.qfont_button)
        qle.setText(text)
        qle.setObjectName("qdialog")
        return qle


class RenameDialog(QDialog):
    def __init__(self, parent, old_filename: str):
        super().__init__(parent)
        self.old_filename = old_filename
        self.setFont(config.qfont_button)
        self.setWindowTitle(" ")
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(config["theme"]["spacing"])
        self.form_layout = QFormLayout()
        self.filename_qle = self.create_qle(self.old_filename)
        self.form_layout.addRow("New Filename  ", self.filename_qle)
        self.layout.addLayout(self.form_layout)
        self.submit_btn = get_button(self, "Rename", self.on_submit)
        self.layout.addWidget(self.submit_btn)
        self.setLayout(self.layout)

    def on_submit(self):
        new_filename = self.filename_qle.text()
        if not is_valid_filename(new_filename):
            fcc_queue.put_notification("Invalid filename provided", lvl=LogLvl.err)
        elif new_filename in db_conn.get_all_files(
            use_basenames=True, excl_ext=True, incl_tmp=True
        ):
            fcc_queue.put_notification(
                "Provided filename already exists", lvl=LogLvl.err
            )
        else:
            self.accept()

    def get_filename(self) -> str:
        return self.filename_qle.text()

    def create_qle(self, text: str = "") -> QLineEdit:
        qle = QLineEdit()
        qle.setFont(config.qfont_button)
        qle.setText(text)
        qle.setObjectName("qdialog")
        return qle


class CreateFileDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFont(config.qfont_button)
        self.setWindowTitle(" ")
        self.setMinimumWidth(350)
        self._create_form()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(config["theme"]["spacing"])
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.submit_btn)
        self.setLayout(self.layout)

    def _create_form(self):
        self.form_layout = QFormLayout()
        self.filename_qle = self.create_qle(parent=self.parent)
        self.lng_qle = self.create_qle(parent=self.parent)
        self.lng_qle.keyPressEvent = self._on_lng_change
        self.lng_qle.setPlaceholderText(
            f"{', '.join(db_conn.get_available_languages())}, ..."
        )
        self.tgt_lng_qle = self.create_qle(parent=self.parent)
        self.src_lng_qle = self.create_qle(parent=self.parent, text=config["native"])
        self.form_layout.addRow("CSV Filename  ", self.filename_qle)
        self.form_layout.addRow("Language      ", self.lng_qle)
        self.form_layout.addRow("Target Lng ID ", self.tgt_lng_qle)
        self.form_layout.addRow("Source Lng ID ", self.src_lng_qle)
        self.submit_btn = get_button(self, "Create", self.accept)

    def accept(self):
        if self.validate():
            super().accept()

    def validate(self) -> bool:
        if not is_valid_filename(self.filename_qle.text()):
            fcc_queue.put_notification("Invalid Filename!", lvl=LogLvl.err)
            return False
        if "." in self.filename_qle.text():
            fcc_queue.put_notification(
                "Filename cannot contain an extension!", lvl=LogLvl.err
            )
            return False
        elif not is_valid_filename(self.lng_qle.text()):
            fcc_queue.put_notification("Invalid Language!", lvl=LogLvl.err)
            return False
        elif not is_valid_filename(self.tgt_lng_qle.text()):
            fcc_queue.put_notification("Invalid Target Language ID!", lvl=LogLvl.err)
            return False
        elif not is_valid_filename(self.src_lng_qle.text()):
            fcc_queue.put_notification("Invalid Source Language ID!", lvl=LogLvl.err)
            return False
        elif self.tgt_lng_qle.text().lower() == self.src_lng_qle.text().lower():
            fcc_queue.put_notification(
                "Source and Target Languages must differ!", lvl=LogLvl.err
            )
            return False
        elif self.filename_qle.text().lower() in {
            f.lower() for f in db_conn.get_all_files(use_basenames=True, excl_ext=True)
        }:
            fcc_queue.put_notification(
                "Provided filename already exists!", lvl=LogLvl.err
            )
            return False
        return True

    def get_data(self) -> CreateFileDialogData:
        return CreateFileDialogData(
            filename=self.filename_qle.text().strip(),
            lng=self.lng_qle.text().strip(),
            src_lng_id=self.src_lng_qle.text().strip(),
            tgt_lng_id=self.tgt_lng_qle.text().strip(),
        )

    def _on_lng_change(self, event: QKeyEvent):
        QLineEdit.keyPressEvent(self.lng_qle, event)
        lng = self.lng_qle.text()[:2].lower()
        self.tgt_lng_qle.setText(lng)

    def create_qle(self, parent=None, text: str = "") -> QLineEdit:
        qle = QLineEdit(parent)
        qle.setFont(config.qfont_button)
        qle.setText(text)
        qle.setObjectName("qdialog")
        return qle


class FieldQLE(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.hasSelectedText():
            self.setCursorPosition(len(self.text()))


class AddCardDialog(QDialog):
    def __init__(self, fh: "FileHandler", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.installEventFilter(self)
        self.fh = fh
        self.fli = 0
        self.flc = self.fh.headers[self.fli]
        self._lookup_re = re.compile(config["sfe"]["lookup_re"])
        self.setWindowTitle("New Card")
        self.setFont(config.qfont_button)
        self.setMinimumWidth(int(0.95 * parent.width()))

        self.form = QFormLayout(self)
        self.form.setContentsMargins(1, 1, 1, 1)
        self.form.setSpacing(2)

        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate)
        self._default_validation_timer_interval = config["sfe"][
            "validation_interval_ms"
        ]
        self._validation_timer_interval = self._default_validation_timer_interval
        self._last_checked_card: dict[str, str] = {}

        self.fields: OrderedDict[str, QLineEdit] = OrderedDict()
        for h in self.fh.headers:
            self.create_field(h)

        self.submit_btn = get_button(self, "Create", self.accept)
        self.submit_btn.setDisabled(True)
        self.form.addWidget(self.submit_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_pos()
        autopasted = self.on_paste()
        if not autopasted and config["sfe"]["hint_autoadd"]:
            self.fields[self.flc].setText(config["sfe"]["hint"])
            self.fields[self.flc].cursorBackward(False, len(config["sfe"]["hint"]))

    def update_pos(self):
        if self.parent():
            pargeo = self.parent().geometry()
            x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
            self.move(x, self.geometry().y())

    def create_field(self, header: str):
        field = FieldQLE(self)
        field.textChanged.connect(self.__on_field_text_changed)
        field.setFont(config.qfont_console)
        field.installEventFilter(self)
        label = QLabel(self)
        label.setFont(config.qfont_console)
        label.setText(header)
        label.setContentsMargins(5, 0, 5, 0)
        self.form.addRow(label, field)
        self.fields[header] = field

    def __on_field_text_changed(self):
        if self.get_card_content() != self._last_checked_card:
            self.submit_btn.setDisabled(True)
            self.submit_btn.setText("Checking...")
            self.validation_timer.start(self._validation_timer_interval)
            self._validation_timer_interval = self._default_validation_timer_interval

    def accept(self):
        self.values = list(self.get_card().values())
        super().accept()

    def validate(self):
        invalid = True
        card = self.get_card_content()
        if any(len(t) == 0 for t in card.values()):
            msg = "Empty"
        elif self.fh.is_duplicate_fullcheck(card):
            msg = "Duplicate"
        else:
            invalid = False
            msg = "Create"
        self.submit_btn.setDisabled(invalid)
        self.submit_btn.setText(msg)
        self._last_checked_card = card

    def eventFilter(self, obj: QObject, event: QKeyEvent) -> bool:
        if event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Paste):
                return self.on_paste()
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.submit_btn.isEnabled():
                    self.accept()
                    return True
        return super().eventFilter(obj, event)

    def on_paste(self) -> bool:
        cur_card = self.get_card()
        pasted = QApplication.clipboard().text().split(config["sfe"]["sep"])
        if not any(cur_card.values()) and len(pasted) == len(self.fields):
            self._validation_timer_interval = 0
            for i, v in enumerate(self.fields.values()):
                v.setText(pasted[i].strip())
            if config["sfe"]["hint_autoadd"]:

                def auto_hint():
                    self._validation_timer_interval = 0
                    field = self.fields[self.flc]
                    field_text = field.text()
                    if not field_text.endswith(
                        config["sfe"]["hint"]
                    ) and not self._lookup_re.search(field_text):
                        field.setText(f"{field_text}{config['sfe']['hint']}")
                        field.cursorBackward(False, int(len(config["sfe"]["hint"]) / 2))

                QTimer.singleShot(10, auto_hint)
            return True
        return False

    def get_card(self) -> dict[str]:
        return {
            k: v.text().strip().removesuffix(config["sfe"]["hint"]).strip()
            for k, v in self.fields.items()
        }

    def get_card_content(self) -> dict[str]:
        return {
            k: self._lookup_re.sub("", v.text())
            .strip()
            .removesuffix(config["sfe"]["hint"])
            .strip()
            for k, v in self.fields.items()
        }


class ConfirmDeleteCardDialog(QDialog):
    def __init__(self, data: list[dict], headers: list, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Card Deletion")
        self.setFont(config.qfont_button)
        self.setMinimumWidth(int(0.95 * parent.width()))
        layout = QFormLayout(self)
        table = QTableWidget()
        table.setRowCount(len(data))
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i, row in enumerate(data):
            for c, (k, v) in enumerate(row.items()):
                if k in headers:
                    table.setItem(i, c, QTableWidgetItem(str(v)))
        layout.addRow(table)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_pos()

    def update_pos(self):
        if self.parent():
            pargeo = self.parent().geometry()
            x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
            self.move(x, self.geometry().y())

    def accept(self):
        super().accept()


class ConfirmDeleteFileDialog(QDialog):
    def __init__(self, fd: FileDescriptor, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm File Deletion")
        self.setFont(config.qfont_button)
        self.setMinimumWidth(int(0.5 * parent.width()))
        label = QLabel()
        label.setFont(config.qfont_button)
        label.setAlignment(Qt.AlignCenter)
        label.setText(fd.filepath)
        layout = QFormLayout(self)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(label)
        layout.addRow(buttons)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_pos()

    def update_pos(self):
        if self.parent():
            pargeo = self.parent().geometry()
            x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
            self.move(x, self.geometry().y())

    def accept(self):
        super().accept()


class StopWatchSetter(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm File Deletion")
        self.setFont(config.qfont_button)
        self.setMinimumWidth(int(0.4 * parent.width()))

        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate)
        self._default_validation_timer_interval = 150
        self._validation_timer_interval = self._default_validation_timer_interval

        self.form = QFormLayout(self)
        self.form.setContentsMargins(1, 1, 1, 1)
        self.form.setSpacing(2)

        self.field = self.create_field("")
        self.field.setPlaceholderText("HH:MM:SS")

        self.submit_btn = get_button(self, "Set Time", self.accept)
        self.submit_btn.setDisabled(True)
        self.submit_btn.setDefault(True)
        self.form.addWidget(self.submit_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self.update_pos()

    def update_pos(self):
        if self.parent():
            pargeo = self.parent().geometry()
            x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
            self.move(x, self.geometry().y())

    def accept(self):
        if self.submit_btn.isEnabled():
            super().accept()

    def get_seconds(self) -> int:
        return parse_to_seconds(self.field.text())

    def __on_field_text_changed(self):
        self.submit_btn.setDisabled(True)
        self.validation_timer.start(self._validation_timer_interval)
        self._validation_timer_interval = self._default_validation_timer_interval

    def validate(self) -> bool:
        try:
            if self.get_seconds() > 0:
                self.submit_btn.setEnabled(True)
                self.submit_btn.setText("Set Time")
            else:
                raise ValueError
        except ValueError:
            self.submit_btn.setDisabled(True)
            self.submit_btn.setText("Invalid Format")

    def create_field(self, header: str) -> FieldQLE:
        field = FieldQLE(self)
        field.textChanged.connect(self.__on_field_text_changed)
        field.setFont(config.qfont_console)
        field.installEventFilter(self)
        label = QLabel(self)
        label.setFont(config.qfont_console)
        label.setText(header)
        label.setContentsMargins(5, 0, 5, 0)
        self.form.addRow(label, field)
        return field


class FocusableLabel(QLabel):
    selectionChanged = pyqtSignal(str)

    def __init__(
        self,
        text: Optional[str] = None,
        parent: QWidget = None,
        global_kbsc_toggle=lambda: None,
    ):
        self._is_editing = False
        self.global_kbsc_toggle = global_kbsc_toggle
        self._prev_sel = ""
        self._sel_timer: Optional[QTimer] = None
        super().__init__(text, parent)
        self.setTextInteractionFlags(
            Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse
        )

    def keyPressEvent(self, event: QKeyEvent):
        if self._is_editing:
            event.accept()  # suppress global shortcuts
            if event.key() == Qt.Key_Escape:
                self.clearFocus()
                self._is_editing = False
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event: QKeyEvent):
        self.setFocusPolicy(Qt.StrongFocus)
        self._is_editing = True
        self.global_kbsc_toggle(False)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QKeyEvent):
        self.setFocusPolicy(Qt.NoFocus)
        self._is_editing = False
        self.global_kbsc_toggle(True)
        super().focusOutEvent(event)

    def keyReleaseEvent(self, event: QEvent):
        if self._sel_timer:
            self._sel_timer.stop()
        self._sel_timer = QTimer.singleShot(300, self._check_selection)
        super().keyReleaseEvent(event)

    def _check_selection(self):
        sel = self.selectedText()
        if sel != self._prev_sel:
            self._prev_sel = sel
            self.selectionChanged.emit(sel)
