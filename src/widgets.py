from PyQt5.QtWidgets import (
    QComboBox,
    QStyledItemDelegate,
    qApp,
    QWidget,
    QGridLayout,
    QPushButton,
    QLabel,
    QVBoxLayout,
)
from PyQt5.QtCore import (
    Qt,
    QPropertyAnimation,
    QTimer,
    QRect,
    pyqtSignal,
    QEvent,
)
from PyQt5.QtGui import QPalette, QFontMetrics, QStandardItem, QFont
from typing import Callable
from cfg import config


class CheckableComboBox(QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(config["dim"]["sw_cfg_box_height"])
            return size

    def __init__(self, layout, allow_multichoice: bool = True, width: float = 0):
        self.allow_multichoice = allow_multichoice
        self._width = width or self.lineEdit().width()
        super().__init__(layout)

        # Make the combo editable to set a custom text, but readonly
        self.setMinimumWidth(1)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Make the lineedit the same color as QPushButton
        palette = qApp.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)

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
                return True
        return False

    def showPopup(self):
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

    def addItems(self, texts, datalist=None):
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

    def wheelEvent(self, *args, **kwargs):
        """Disable scrolling"""
        return


class ScrollableOptionsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = config
        self.font = self.config["theme"]["font"]
        self.font_button_size = self.config["theme"]["font_button_size"]
        self.button_height = self.config["dim"]["buttons_height"]
        self.button_stylesheet = self.config["theme"]["button_stylesheet"]
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

    def __list_pos_gen(self):
        """increments iterator every 2 calls"""
        i = 0
        while True:
            yield int(i)
            i += 0.5


class NotificationPopup(QWidget):
    clicked = pyqtSignal()

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
        self.label.setFont(QFont(config["theme"]["font"], 12))
        self.setFixedSize(
            int(self.parent().width() // 1.8), config["dim"]["notification_height"]
        )
        layout.addWidget(self.label)
        self.setStyleSheet(config["theme"]["button_stylesheet"])
        self.__configure_animations()
        self.__func = lambda: None
        self.is_visible = False

    def __configure_animations(self):
        self.enter_animation = QPropertyAnimation(self, b"windowOpacity")
        self.enter_animation.setDuration(config["popups"]["show_animation_ms"])
        self.enter_animation.setStartValue(0.8)
        self.enter_animation.setEndValue(1)
        self.exit_animation = QPropertyAnimation(self, b"windowOpacity")
        self.exit_animation.setDuration(config["popups"]["hide_animation_ms"])
        self.exit_animation.setStartValue(1)
        self.exit_animation.setEndValue(0.8)

    def show_notification(
        self,
        message: str,
        func: Callable = None,
        persist: bool = False,
        *args,
        **kwargs,
    ):
        self.label.setText(message)
        if callable(func):
            self.__func = lambda: func(*args, **kwargs)
        else:
            self.__func = lambda: None
        x, y = self._get_x_y()
        self.setGeometry(QRect(x, y, self.width(), self.height()))
        self.show()
        self.enter_animation.start()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        if not persist:
            self.timer.timeout.connect(self.hide_notification)
            self.timer.start(config["popups"]["timeout_ms"])
        self.is_visible = True

    def _get_x_y(self) -> tuple[int, int]:
        pargeo = self.parent().geometry()
        x = int(pargeo.x() + 0.5 * self.parent().width() - 0.5 * self.width())
        return x, pargeo.y()

    def update_position(self):
        self.move(*self._get_x_y())

    def hide_notification(self):
        """
        Run animation before closing the popup.
        Keep notification when window is not active
        """
        if self.parent().isActiveWindow():
            self.exit_animation.start()
            self.exit_animation.finished.connect(self.close_notification)
        else:
            if self.timer.isActive():
                self.timer.stop()
            self.timer.start(config["popups"]["timeout_ms"])

    def close_notification(self):
        """Immediately hide the popup"""
        self.exit_animation.stop()
        self.enter_animation.stop()
        self.close()
        self.timer.stop()
        self.is_visible = False

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
