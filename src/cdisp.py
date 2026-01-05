import pandas as pd
from abc import ABC, abstractmethod
from PyQt5.QtWidgets import QLabel, QWidget, QMenu, QVBoxLayout, QGraphicsBlurEffect
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtCore import Qt, QTimer
from typing import Optional as Opt, Callable
from cfg import config
from widgets import FocusableLabel


class CardDisplayBase(ABC):

    @property
    def widget(self) -> QWidget: ...

    @abstractmethod
    def attach_ctx(self) -> QMenu: ...

    @abstractmethod
    def open_ctx(self) -> None: ...

    @abstractmethod
    def set_ShowEvent(self, fn: Callable) -> None: ...

    @abstractmethod
    def set_MouseReleaseEvent(self, fn: Callable) -> None: ...

    @abstractmethod
    @abstractmethod
    def set_SelectionChanged(self, fn: Callable): ...

    @abstractmethod
    def set_card(self, card: pd.Series, i: int, new: bool = True) -> None: ...

    @abstractmethod
    def upd_card(self, card: pd.Series, i: int) -> None: ...

    @abstractmethod
    def chg_side(self, i: int) -> None: ...

    @abstractmethod
    def set_font(self, family: str, point_size: int) -> None: ...

    @abstractmethod
    def set_focus(self) -> None: ...

    @abstractmethod
    def set_enabled(self, b: bool) -> None: ...

    @abstractmethod
    def get_selected_text(self) -> str: ...

    @abstractmethod
    def get_sel_side(self) -> int: ...

    @abstractmethod
    def get_text(self) -> str: ...

    @abstractmethod
    def apply_blur(self) -> None: ...

    @abstractmethod
    def remove_blur(self) -> None: ...

    def fmt_qlabel(self, qlabel: QLabel) -> None:
        qlabel.setFont(config.qfont_textbox)
        qlabel.setWordWrap(True)
        qlabel.setAlignment(Qt.AlignCenter)
        qlabel.setCursor(Qt.IBeamCursor)

    def get_blur(self) -> QGraphicsBlurEffect:
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(35)
        return blur

    def _wrapped_qlabel_MouseReleaseEvent(self, obj: QLabel, _fn: Callable):
        def wrapped(event):
            _fn()
            QLabel.mouseReleaseEvent(obj, event)

        return wrapped


class CardDisplayKey(CardDisplayBase):

    def __init__(self, parent: QWidget = None):
        self._font_point_size = 0
        self.is_blurred = False
        self._cur_side = 0
        self._card = pd.Series(["-", "-"])
        self._disp = FocusableLabel(parent)
        self.fmt_qlabel(self._disp)
        self._is_editing = False
        self.global_kbsc_toggle = lambda: None
        self._prev_sel = ""
        self._sel_timer: Opt[QTimer] = None
        self._disp.setTextInteractionFlags(
            Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse
        )

    @property
    def widget(self) -> QWidget:
        return self._disp

    def set_global_kbsc_toggle(self, fn: Callable) -> None:
        self._disp.global_kbsc_toggle = fn

    def set_SelectionChanged(self, fn: Callable):
        self._disp.selectionChanged.connect(fn)

    def set_ShowEvent(self, fn: Callable) -> None:
        def showEvent(event):
            QLabel.showEvent(self._disp, event)
            fn()

        self._disp.showEvent = showEvent

    def set_MouseReleaseEvent(self, fn: Callable) -> None:
        self._disp.mouseReleaseEvent = self._wrapped_qlabel_MouseReleaseEvent(
            self._disp, fn
        )

    def set_enabled(self, b: bool) -> None:
        self._disp.setEnabled(b)

    def get_selected_text(self) -> str:
        return self._disp.selectedText()

    def get_text(self) -> str:
        return self._disp.text()

    def attach_ctx(self) -> QMenu:
        self._ctx = QMenu(self._disp)
        self._disp.setContextMenuPolicy(Qt.CustomContextMenu)
        self._disp.customContextMenuRequested.connect(self.open_ctx)
        return self._ctx

    def open_ctx(self) -> None:
        self._ctx.exec_(QCursor.pos())

    def set_card(self, card: pd.Series, i: int, new: bool = True) -> None:
        self._card = card
        self._disp.setText(self._card.iloc[i])
        self._cur_side = i

    def upd_card(self, card: pd.Series, i: int) -> None:
        self._card = card
        self._disp.setText(self._card.iloc[i])

    def chg_side(self, i: int) -> None:
        self._disp.setText(self._card.iloc[i])
        self._cur_side = i

    def get_sel_side(self) -> int:
        return self._cur_side

    def set_font(self, family: str, point_size: int) -> None:
        if point_size != self._font_point_size:
            self._disp.setFont(QFont(family, point_size))

    def set_focus(self) -> None:
        self._disp.setFocus()

    def apply_blur(self):
        self._disp.setGraphicsEffect(self.get_blur())
        self.is_blurred = True
        self._disp.setEnabled(False)

    def remove_blur(self):
        self._disp.setGraphicsEffect(None)
        self.is_blurred = False
        self._disp.setEnabled(True)


class CardDisplaySimple(CardDisplayBase):
    def __init__(self, parent: Opt[QWidget] = None):
        self._font_point_size = 0
        self._cur_side = 0
        self.is_blurred = False
        self._card = pd.Series(["-", "-"])
        self._disp = QLabel(parent=parent)
        self.fmt_qlabel(self._disp)
        self._disp.setTextInteractionFlags(Qt.TextSelectableByMouse)

    @property
    def widget(self) -> QWidget:
        return self._disp

    def set_ShowEvent(self, fn: Callable) -> None:
        def showEvent(event):
            QLabel.showEvent(self._disp, event)
            fn()

        self._disp.showEvent = showEvent

    def set_MouseReleaseEvent(self, fn: Callable) -> None:
        self._disp.mouseReleaseEvent = self._wrapped_qlabel_MouseReleaseEvent(
            self._disp, fn
        )

    def set_enabled(self, b: bool) -> None:
        self._disp.setEnabled(b)

    def set_SelectionChanged(self, fn: Callable):
        return

    def get_selected_text(self) -> str:
        return self._disp.selectedText()

    def get_text(self) -> str:
        return self._disp.text()

    def attach_ctx(self) -> QMenu:
        self._ctx = QMenu(self._disp)
        self._disp.setContextMenuPolicy(Qt.CustomContextMenu)
        self._disp.customContextMenuRequested.connect(self.open_ctx)
        return self._ctx

    def open_ctx(self) -> None:
        self._ctx.exec_(QCursor.pos())

    def set_card(self, card: pd.Series, i: int, new: bool = True) -> None:
        self._card = card
        self._disp.setText(self._card.iloc[i])
        self._cur_side = i

    def upd_card(self, card: pd.Series, i: int) -> None:
        self._card = card
        self._disp.setText(self._card.iloc[i])

    def chg_side(self, i: int) -> None:
        self._disp.setText(self._card.iloc[i])
        self._cur_side = i

    def get_sel_side(self) -> int:
        return self._cur_side

    def set_font(self, family: str, point_size: int) -> None:
        if point_size != self._font_point_size:
            self._disp.setFont(QFont(family, point_size))

    def set_focus(self) -> None:
        self._disp.setFocus()

    def apply_blur(self):
        self._disp.setGraphicsEffect(self.get_blur())
        self.is_blurred = True
        self._disp.setEnabled(False)

    def remove_blur(self):
        self._disp.setGraphicsEffect(None)
        self.is_blurred = False
        self._disp.setEnabled(True)


class CardDisplayDual(CardDisplayBase):
    def __init__(self, parent: Opt[QWidget] = None):
        self.is_blurred = False
        self._def_side = 0
        self._font_point_size = 0
        self._focused_i = 0
        self._card = pd.Series(["-", "-"])
        self._widget = QWidget(parent)
        layout = QVBoxLayout(self.widget)
        self.__create_labels()
        layout.addWidget(self._front_label)
        layout.addWidget(self._back_label)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        self._widget.setLayout(layout)

    @property
    def widget(self) -> QWidget:
        return self._widget

    def __create_labels(self):
        self._front_label = QLabel()
        self._back_label = QLabel()
        self._front_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._back_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.fmt_qlabel(self._front_label)
        self.fmt_qlabel(self._back_label)

    def attach_ctx(self) -> QMenu:
        self._ctx = QMenu(self._front_label)
        self._front_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._front_label.customContextMenuRequested.connect(self.open_ctx)
        self._back_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._back_label.customContextMenuRequested.connect(self.open_ctx)
        return self._ctx

    def open_ctx(self) -> None:
        self._ctx.exec_(QCursor.pos())

    def set_ShowEvent(self, fn: Callable) -> None:
        def showEvent(event):
            QLabel.showEvent(self._front_label, event)
            fn()

        self._front_label.showEvent = showEvent
        self._back_label.showEvent = showEvent

    def set_MouseReleaseEvent(self, fn: Callable) -> None:
        self._front_label.mouseReleaseEvent = self._wrapped_qlabel_MouseReleaseEvent(
            self._front_label, fn
        )
        self._back_label.mouseReleaseEvent = self._wrapped_qlabel_MouseReleaseEvent(
            self._back_label, fn
        )

    def set_SelectionChanged(self, fn: Callable):
        return

    def set_card(self, card: pd.Series, i: int, new: bool = True) -> None:
        self._card = card
        self._def_side = i
        self._front_label.setText(self._card.iloc[0])
        self._back_label.setText(self._card.iloc[1])
        eff = self.get_blur() if new else None
        if i == 0:
            self._back_label.setGraphicsEffect(eff)
            self._focused_i = 0
        else:
            self._front_label.setGraphicsEffect(eff)
            self._focused_i = 1

    def upd_card(self, card: pd.Series, i: int) -> None:
        self._card = card
        self._front_label.setText(self._card.iloc[0])
        self._back_label.setText(self._card.iloc[1])

    def chg_side(self, i: int) -> None:
        if i == 0:
            self._front_label.setGraphicsEffect(None)
            self._front_label.setFocus()
            self._focused_i = 0
        else:
            self._back_label.setGraphicsEffect(None)
            self._back_label.setFocus()
            self._focused_i = 1

    def set_font(self, family: str, point_size: int) -> None:
        if point_size != self._font_point_size:
            font = QFont(family, point_size)
            self._front_label.setFont(font)
            self._back_label.setFont(font)

    def set_focus(self) -> None:
        self._front_label.setFocus()

    def set_enabled(self, b: bool) -> None:
        self._front_label.setEnabled(b)
        self._back_label.setEnabled(b)

    def get_sel_side(self) -> int:
        if self._focused_i == 0 or self._front_label.hasFocus():
            return 0
        else:
            return 1

    def get_selected_text(self) -> str:
        return self._front_label.selectedText() or self._back_label.selectedText()

    def get_text(self) -> str:
        if self._focused_i == 0 or self._front_label.hasFocus():
            return self._front_label.text()
        else:
            return self._back_label.text()

    def apply_blur(self):
        self._widget.setGraphicsEffect(self.get_blur())
        self.is_blurred = True
        self._widget.setEnabled(False)

    def remove_blur(self):
        eff_0 = self._front_label.graphicsEffect()
        eff_1 = self._back_label.graphicsEffect()
        self._widget.setGraphicsEffect(None)
        self._front_label.setGraphicsEffect(eff_0)
        self._back_label.setGraphicsEffect(eff_1)
        self.is_blurred = False
        self._widget.setEnabled(True)
