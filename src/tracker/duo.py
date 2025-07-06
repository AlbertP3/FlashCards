import logging
from datetime import date
from time import time
from PyQt5.QtWidgets import (
    QGridLayout,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QFormLayout,
    QTextEdit,
)
from PyQt5.QtCore import Qt
from cfg import config
from widgets import CheckableComboBox, get_button
from utils import format_seconds_to, Caliper
from DBAC import db_conn
from tracker.dal import dal
from tracker.helpers import parse_to_seconds, safe_div, merge_records_by_date, get_chart
from tracker.structs import RecordOrderedDict, Column

log = logging.getLogger("TRK")


class DuoLayout(QWidget):
    def __init__(self):
        super().__init__()
        self.upd = -1
        self.upd_date = date.today()
        self.caliper = Caliper(config.qfont_chart)
        self.setFont(config.qfont_button)
        self.layout = QGridLayout()
        self.create_form()
        self.create_charts()
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 2)

    @property
    def lines_lim(self) -> int:
        return int(0.9 * config["geo"][1] // self.caliper.sch)

    @property
    def pix_lim(self) -> int:
        return int(config["geo"][0] / 1.5)

    def get(self) -> QGridLayout:
        return self.layout

    def refresh(self):
        if self.upd < dal.upd or self.upd_date < date.today():
            data = dal.get_data()

            try:
                lrd = dal.get_duo_last_report_date()
                t, l = 0, 0
                for r in [v for k, v in data.items() if k <= lrd and v.duo.lessons > 0][
                    -config["tracker"]["duo"]["prelim_avg"] :
                ]:
                    t += r.duo.hours * 60
                    l += r.duo.lessons
                self.prelim_avg = safe_div(t, l)
            except Exception as e:
                self.prelim_avg = 0
                log.error(e, exc_info=True)
            self.time_spent_qle.setPlaceholderText(
                format_seconds_to(self.prelim_avg * 60, "minute", sep=":")
            )

            try:
                self.lessons_today = data[date.today()].duo.lessons
            except KeyError:
                self.lessons_today = 0

            self.cells = [
                [
                    Column(
                        [
                            self.get_chart_weekly_activity(
                                data, self.lines_lim // 2 - 1
                            ),
                            [" "],
                            [" "],
                            self.get_chart_last_7_days(data, self.lines_lim // 2 - 1),
                        ]
                    )
                ]
            ]
            self.fill_charts()
            self.upd = dal.upd
            self.upd_date = date.today()

    def create_form(self):
        self.form_layout = QFormLayout()
        self.form_layout.setVerticalSpacing(10)
        self.form_layout.setLabelAlignment(Qt.AlignLeft)

        self.lng_cbx = self.get_cbx(
            config["languages"][0],
            db_conn.get_available_languages(),
            multi_choice=False,
        )
        self.form_layout.addRow("Language", self.lng_cbx)

        self.time_spent_qle = self.get_qle("0:00")
        self.form_layout.addRow("Minutes", self.time_spent_qle)

        self.lessons_qle = self.get_qle("1")
        self.form_layout.addRow("Lessons", self.lessons_qle)

        self.offset_qle = self.get_qle("0")
        self.form_layout.addRow("Offset", self.offset_qle)

        self.final_cbx = self.get_cbx("False", ["False", "True"], multi_choice=False)
        self.form_layout.addRow("Final", self.final_cbx)

        self.submit_btn = get_button(self, "Add", self.on_submit, dtip=self.get_tooltip)
        self.form_layout.addRow(self.submit_btn)

        for i in range(self.form_layout.rowCount()):
            label = self.form_layout.itemAt(i, 0)
            if label:
                label.widget().setFixedWidth(100)

        self.layout.addLayout(self.form_layout, 0, 0, 1, 1)

    def get_qle(self, placeholder: str = "") -> QLineEdit:
        qle = QLineEdit()
        qle.setFont(config.qfont_console)
        qle.setAlignment(Qt.AlignCenter)
        qle.setPlaceholderText(placeholder)
        return qle

    def get_qte(self) -> QTextEdit:
        qte = QTextEdit()
        qte.setFont(config.qfont_chart)
        qte.setContentsMargins(0, 0, 0, 0)
        qte.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        qte.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        qte.setReadOnly(True)
        return qte

    def get_cbx(self, value, content: list, multi_choice: bool = True):
        cb = CheckableComboBox(
            self, allow_multichoice=multi_choice, width=50, hide_on_checked=True
        )
        if isinstance(value, dict):
            value = [k for k, v in value.items() if v is True]
        for i in content:
            try:
                cb.addItem(i, is_checked=i in value)
            except TypeError:
                cb.addItem(i, is_checked=i == str(value))
        return cb

    def on_submit(self):
        if self.final_cbx.currentDataList()[0] == "True":
            self.__submit_final()
        else:
            self.__submit_preliminary()
        self.__submit_after()

    def __submit_final(self):
        lng = self.lng_cbx.currentDataList()[0]
        les = int(self.lessons_qle.text())
        ts = int(parse_to_seconds(self.time_spent_qle.text()) / 60)
        dal.add_duo_record_final(lng=lng, lessons=les, timespent=ts)
        self.final_cbx.setChecked(index=0)

    def __submit_preliminary(self):
        lng = self.lng_cbx.currentDataList()[0]
        les = int(self.lessons_qle.text() or self.lessons_qle.placeholderText())
        if raw_ts := self.time_spent_qle.text():
            ts = round(parse_to_seconds(raw_ts) / 60, 2)
        else:
            ts = les * self.prelim_avg
        offset = int(self.offset_qle.text() or self.offset_qle.placeholderText())
        dal.add_duo_record_preliminary(
            lng=lng, lessons=les, timespent=ts, offset=offset
        )

    def __submit_after(self):
        self.lessons_qle.clear()
        self.time_spent_qle.clear()
        self.offset_qle.clear()
        self.upd = -1
        self.refresh()

    def get_tooltip(self) -> str:
        elapsed_sec = int(time() - dal.monitor[dal.spc.duo_path])
        if elapsed_sec < 3600:
            fmt, rem, sep = "minute", 0, ":"
        elif elapsed_sec < 86400:
            fmt, rem, sep = "hour", 2, ":"
        else:
            fmt, rem, sep = "day", 0, "."
        last = format_seconds_to(
            elapsed_sec,
            interval=fmt,
            rem=rem,
            sep=sep,
            interval_name=fmt,
        )
        if self.upd_date < date.today():
            lessons_today = 0
        else:
            lessons_today = self.lessons_today
        return "Lessons today: {}\nLast: {} ago".format(str(lessons_today), last)

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
