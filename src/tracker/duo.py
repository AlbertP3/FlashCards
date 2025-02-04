import logging
from datetime import date
from PyQt5.QtWidgets import (
    QGridLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QFormLayout,
    QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from cfg import config
from widgets import CheckableComboBox
from utils import format_seconds_to, Caliper
from DBAC.api import DbOperator
from tracker.dal import dal
from tracker.helpers import parse_to_seconds, safe_div, merge_records_by_date, get_chart
from tracker.structs import RecordOrderedDict, Column

log = logging.getLogger("GUI")


class DuoLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.upd = -1
        self.qfont = QFont(config["theme"]["font"], config["dim"]["console_font_size"])
        self.qfont_chart = QFont(
            config["theme"]["font"], config["dim"]["font_stats_size"]
        )
        self.caliper = Caliper(self.qfont_chart)
        self.setStyleSheet(config["theme"]["textbox_stylesheet"])
        self.setFont(self.qfont)
        self.layout = QGridLayout()
        self.create_form()
        self.create_charts()
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 2)

    @property
    def lines_lim(self) -> int:
        return int(0.95 * config.get_geo("timer")[1] // self.caliper.sch)

    @property
    def pix_lim(self) -> int:
        return int(self.chart_qte.width())

    def get(self) -> QGridLayout:
        return self.layout

    def refresh(self):
        if self.upd < dal.upd:
            data = dal.get_data()
            try:
                t, l = 0, 0
                for r in list(data.values())[-config["tracker"]["duo"]["prelim_avg"] :]:
                    t += r.duo.hours * 60
                    l += r.duo.lessons
                self.prelim_avg = safe_div(t, l)
            except Exception as e:
                self.prelim_avg = 0
                log.error(e, exc_info=True)
            self.time_spent_qle.setPlaceholderText(
                format_seconds_to(self.prelim_avg * 60, "minute", sep=":")
            )
            self.cells = [
                [
                    Column(
                        [
                            self.get_chart_weekly_activity(
                                data, self.lines_lim // 2 - 1
                            ),
                            [" "],
                            self.get_chart_last_7_days(data, self.lines_lim // 2 - 1),
                        ]
                    )
                ]
            ]
            self.fill_charts()
            self.upd = dal.upd
            log.debug("Updated Duo Tab")

    def create_form(self):
        self.form_layout = QFormLayout()
        self.form_layout.setVerticalSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)

        self.lng_cbx = self.get_cbx(
            config["languages"][0],
            DbOperator().get_available_languages(),
            multi_choice=False,
        )
        self.form_layout.addRow("Language", self.lng_cbx)

        self.lessons_qle = self.get_qle("1")
        self.form_layout.addRow("Lessons", self.lessons_qle)

        self.time_spent_qle = self.get_qle("0:00")
        self.form_layout.addRow("Minutes", self.time_spent_qle)

        self.offset_qle = self.get_qle("0")
        self.form_layout.addRow("Offset", self.offset_qle)

        self.final_cbx = self.get_qcb()
        self.form_layout.addRow("Final", self.final_cbx)

        self.submit_btn = self.get_btn("Add", self.on_submit)
        self.form_layout.addRow(self.submit_btn)

        for i in range(self.form_layout.rowCount()):
            label = self.form_layout.itemAt(i, 0)
            if label:
                label.widget().setFixedWidth(100)

        self.layout.addLayout(self.form_layout, 0, 0, 1, 1)

    def get_qle(self, placeholder: str = "") -> QLineEdit:
        qle = QLineEdit()
        qle.setFont(self.qfont)
        qle.setStyleSheet(config["theme"]["textbox_stylesheet"])
        qle.setAlignment(Qt.AlignCenter)
        qle.setPlaceholderText(placeholder)
        return qle

    def get_qte(self) -> QTextEdit:
        qte = QTextEdit()
        qte.setFont(self.qfont_chart)
        qte.setStyleSheet(config["theme"]["textbox_stylesheet"])
        qte.setContentsMargins(0, 0, 0, 0)
        qte.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        qte.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        qte.setReadOnly(True)
        return qte

    def get_cbx(self, value, content: list, multi_choice: bool = True):
        cb = CheckableComboBox(
            self,
            allow_multichoice=multi_choice,
            width=50,
        )
        cb.setStyleSheet(config["theme"]["button_stylesheet"])
        cb.setFont(self.qfont)
        if isinstance(value, dict):
            value = [k for k, v in value.items() if v is True]
        for i in content:
            try:
                cb.addItem(i, is_checked=i in value)
            except TypeError:
                cb.addItem(i, is_checked=i == str(value))
        return cb

    def get_qcb(self) -> QCheckBox:
        qcb = QCheckBox()
        qcb.setFont(self.qfont)
        qcb.setStyleSheet(config["theme"]["button_stylesheet"])
        qcb.setFocusPolicy(Qt.NoFocus)
        return qcb

    def get_btn(self, text, function=None) -> QPushButton:
        button = QPushButton()
        button.setFixedHeight(config["dim"]["buttons_height"])
        button.setFont(self.qfont)
        button.setText(text)
        button.setStyleSheet(config["theme"]["button_stylesheet"])
        if function is not None:
            button.clicked.connect(function)
        return button

    def on_submit(self):
        lng = self.lng_cbx.currentDataList()[0]
        les = int(self.lessons_qle.text() or self.lessons_qle.placeholderText())
        ts = self.time_spent_qle.text() or self.time_spent_qle.placeholderText()

        if self.final_cbx.isChecked():
            ts = int(ts)
            dal.add_duo_record_final(lng=lng, lessons=les, timespent=ts)
        else:
            ts = round(parse_to_seconds(ts) / 60, 2)
            offset = int(self.offset_qle.text() or self.offset_qle.placeholderText())
            dal.add_duo_record_preliminary(
                lng=lng, lessons=les, timespent=ts, offset=offset
            )
        self.lessons_qle.clear()
        self.time_spent_qle.clear()
        self.offset_qle.clear()
        self.final_cbx.setChecked(False)
        self.upd = -1
        self.refresh()

    def create_charts(self):
        self.chart_layout = QVBoxLayout()
        self.chart_qte = self.get_qte()
        self.chart_layout.addWidget(self.chart_qte)
        self.layout.addLayout(self.chart_layout, 0, 1, 1, 1)

    def fill_charts(self):
        printout = str()
        pad = int((self.pix_lim / self.caliper.scw - 43) / 2 + 0.5)
        for row in self.cells:
            for col in range(max(len(c) for c in row)):
                printout += " " * pad + " ".join(c[col] for c in row) + "\n"
        self.chart_qte.setText(printout[:-1])

    def get_chart_weekly_activity(
        self, data: RecordOrderedDict, height: int = 15
    ) -> list[str]:
        wdi = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
        data = [
            (k, v.total_hours) for k, v in merge_records_by_date(data, "%a").items()
        ]
        for missing in set(wdi.keys()).difference(i[0] for i in data):
            data.append((missing, 0))
        total_hours = sum(i[1] for i in data)
        out = sorted(data, key=lambda x: wdi[x[0]])
        return get_chart(
            out,
            height,
            scaling=total_hours,
            num_fmt=".0%",
            scale_fmt="3.0%",
            incl_scale=False,
            title="Weekly Time Allocation",
            hpad=0.7,
            col_len=5,
        )

    def get_chart_last_7_days(
        self, data: RecordOrderedDict, height: int = 15
    ) -> list[str]:
        today = date.today()
        twd = today.weekday()
        wdi = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        wdi = wdi[twd + 1 :] + wdi[: twd + 1]
        rel = [0] * 7
        for k, v in data.items():
            diff = (today - k).days
            if diff < 7:
                rel[-diff - 1] += v.total_hours
        out = [(wdi[i], 60 * rel[i]) for i in range(7)]
        return get_chart(
            out,
            height,
            title="Last Week (Minutes)",
            hpad=0.7,
            incl_scale=False,
            col_len=5,
        )
