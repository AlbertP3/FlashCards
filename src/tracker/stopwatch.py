import logging
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCompleter,
    QDialog,
)
from PyQt5.QtCore import Qt, QTime, QTimer, QStringListModel
from widgets import CheckableComboBox, get_button, StopWatchSetter
from DBAC import db_conn
from typing import TYPE_CHECKING
from cfg import config
from tracker.structs import IMM_CATS
from tracker.dal import dal

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("TRK")


class StopwatchTab(QWidget):
    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.mw = mw
        self.upd = -1
        self.cat_map = dal.get_imm_category_mapping()
        self.__res = 1
        self.__cur_category = config["tracker"]["default_category"]
        self.init_ui()

    def refresh(self):
        if self.upd < dal.upd:
            self.cat_map = dal.get_imm_category_mapping()
            self.update_completer(self.__cur_category)
            self.upd = dal.upd

    def get(self) -> QVBoxLayout:
        return self.layout

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(1)
        self.timer_label = QLabel(dal.stopwatch_elapsed.toString("hh:mm:ss"))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(config.qfont_stopwatch)
        self.timer_label.setObjectName("stopwatch")
        self.layout.addWidget(self.timer_label)

        controls_layout = QHBoxLayout()

        self.timeset_btn = get_button(self, "Set", self.show_timeset)
        min_height = self.timeset_btn.height()

        self.category_cbx = self.get_cbx(
            config["tracker"]["default_category"], IMM_CATS, multi_choice=False
        )
        self.category_cbx.setMinimumHeight(min_height)
        self.category_cbx.model().dataChanged.connect(
            lambda: QTimer.singleShot(1, self.on_category_change)
        )
        controls_layout.addWidget(self.category_cbx)

        self.lng_cbx = self.get_cbx(
            config["languages"][0],
            db_conn.get_available_languages(),
            multi_choice=False,
        )
        self.lng_cbx.setMinimumHeight(min_height)
        controls_layout.addWidget(self.lng_cbx)

        controls_layout.addWidget(self.timeset_btn)

        self.title_qle = self.get_qle(placeholder="Title")
        self.title_qle.setMinimumHeight(min_height)
        self.title_completer = self.get_completer([])
        self.title_qle.setCompleter(self.title_completer)
        self.update_completer(self.__cur_category)
        controls_layout.addWidget(self.title_qle)

        self.pause_btn = get_button(self, "Start", self.toggle_timer)
        controls_layout.addWidget(self.pause_btn)

        self.commit_btn = get_button(self, "Commit", self.commit_action)
        controls_layout.addWidget(self.commit_btn)

        self.cancel_btn = get_button(self, "Cancel", self.reset_timer)
        controls_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(controls_layout)
        self.setLayout(self.layout)

        if dal.stopwatch_running:
            self.pause_btn.setText("Pause")
            dal.stopwatch_timer.timeout.disconnect()
            dal.stopwatch_timer.timeout.connect(self.update_timer)
        else:
            dal.stopwatch_timer = QTimer(self)
            dal.stopwatch_timer.timeout.connect(self.update_timer)

    def get_current_titles(self, category: str) -> list:
        return [v for v in self.cat_map.get(category, [])]

    def on_category_change(self):
        new_category = self.category_cbx.currentDataList()[0]
        if self.__cur_category != new_category:
            self.update_completer(new_category)
    
    def update_completer(self, category: str):
        self.title_completer.setModel(QStringListModel(self.get_current_titles(category)))
        config["tracker"]["default_category"] = category
        self.__cur_category = category

    def toggle_timer(self):
        if dal.stopwatch_running:
            dal.stopwatch_timer.stop()
            self.pause_btn.setText("Resume")
        else:
            dal.stopwatch_timer.start(self.__res * 1000)
            self.pause_btn.setText("Pause")
        dal.stopwatch_running = not dal.stopwatch_running

    def update_timer(self):
        dal.stopwatch_elapsed = dal.stopwatch_elapsed.addSecs(self.__res)
        self.timer_label.setText(dal.stopwatch_elapsed.toString("hh:mm:ss"))

    def reset_timer(self):
        dal.stopwatch_timer.stop()
        dal.stopwatch_elapsed = QTime(0, 0, 0)
        self.timer_label.setText("00:00:00")
        self.pause_btn.setText("Start")
        dal.stopwatch_running = False

    def commit_action(self):
        lng = self.lng_cbx.currentDataList()[0]
        cat = self.category_cbx.currentDataList()[0]
        title = self.title_qle.text()
        ts = self.get_seconds_elapsed()
        dal.add_imm_record(lng=lng, total_seconds=ts, title=title, category=cat)
        self.title_qle.clear()
        self.reset_timer()
        self.refresh()

    def get_seconds_elapsed(self) -> int:
        return (
            dal.stopwatch_elapsed.hour() * 3600
            + dal.stopwatch_elapsed.minute() * 60
            + dal.stopwatch_elapsed.second()
        )

    def get_cbx(self, value, content: list, multi_choice: bool = True):
        cb = CheckableComboBox(
            self,
            allow_multichoice=multi_choice,
            width=100,
        )
        cb.setFont(config.qfont_button)
        if isinstance(value, dict):
            value = [k for k, v in value.items() if v is True]
        for i in content:
            try:
                cb.addItem(i, is_checked=i in value)
            except TypeError:
                cb.addItem(i, is_checked=i == str(value))
        return cb

    def get_qle(self, text: str = "", placeholder: str = "") -> QLineEdit:
        qle = QLineEdit(self)
        qle.setFont(config.qfont_button)
        qle.setMaximumWidth(250)
        qle.setAlignment(Qt.AlignCenter)
        qle.setText(text)
        qle.setPlaceholderText(placeholder)
        return qle

    def get_completer(self, model: QStringListModel):
        completer = QCompleter(model, self)
        completer.setCaseSensitivity(False)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.InlineCompletion)
        return completer

    def show_timeset(self):
        dlg = StopWatchSetter(parent=self.mw)
        if dlg.exec_() == QDialog.Accepted:
            seconds = dlg.get_seconds()
            dal.stopwatch_elapsed = dal.stopwatch_elapsed.fromMSecsSinceStartOfDay(
                1000 * seconds
            )
            self.timer_label.setText(dal.stopwatch_elapsed.toString("hh:mm:ss"))
