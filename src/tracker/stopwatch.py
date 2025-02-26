import logging
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCompleter,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTime, QTimer, QStringListModel
from widgets import CheckableComboBox
from DBAC import db_conn
from cfg import config
from tracker.structs import IMM_CATS
from tracker.dal import dal

log = logging.getLogger("TRK")


class StopwatchTab(QWidget):
    def __init__(self):
        super().__init__()
        self.upd = -1
        self.cat_map = dal.get_imm_category_mapping()
        self.__res = 1
        self.init_ui()

    def refresh(self):
        if self.upd < dal.upd:
            self.cat_map = dal.get_imm_category_mapping()
            self.upd = dal.upd
            log.debug("Refreshed StopWatch Tab")

    def get(self) -> QVBoxLayout:
        return self.layout

    def init_ui(self):
        self.layout = QVBoxLayout()
        self.timer_label = QLabel(dal.stopwatch_elapsed.toString("hh:mm:ss"))
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(config.qfont_stopwatch)
        self.timer_label.setObjectName("stopwatch")
        self.layout.addWidget(self.timer_label)

        controls_layout = QHBoxLayout()
        self.category_cbx = self.get_cbx(
            config["tracker"]["default_category"], IMM_CATS, multi_choice=False
        )
        self.category_cbx.currentIndexChanged.connect(self.on_category_change)
        controls_layout.addWidget(self.category_cbx)

        self.lng_cbx = self.get_cbx(
            config["languages"][0],
            db_conn.get_available_languages(),
            multi_choice=False,
        )
        controls_layout.addWidget(self.lng_cbx)

        self.title_qle = self.get_qle(placeholder="Title")
        self.title_completer = self.get_completer([])
        self.title_qle.setCompleter(self.title_completer)
        self.on_category_change()
        controls_layout.addWidget(self.title_qle)

        self.pause_btn = self.get_btn("Start")
        self.pause_btn.clicked.connect(self.toggle_timer)
        controls_layout.addWidget(self.pause_btn)

        self.commit_btn = self.get_btn("Commit")
        self.commit_btn.clicked.connect(self.commit_action)
        controls_layout.addWidget(self.commit_btn)

        self.cancel_btn = self.get_btn("Cancel")
        self.cancel_btn.clicked.connect(self.reset_timer)
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

    def get_current_titles(self) -> list:
        return [v for v in self.cat_map.get(self.category_cbx.currentDataList()[0], [])]

    def on_category_change(self):
        self.title_completer.setModel(QStringListModel(self.get_current_titles()))

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
        self.reset_timer()

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

    def get_btn(self, text, function=None) -> QPushButton:
        button = QPushButton()
        button.setFont(config.qfont_button)
        button.setText(text)
        if function is not None:
            button.clicked.connect(function)
        return button

    def get_qle(self, text: str = "", placeholder: str = "") -> QLineEdit:
        qle = QLineEdit()
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
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.popup().setFont(config.qfont_button)
        return completer
