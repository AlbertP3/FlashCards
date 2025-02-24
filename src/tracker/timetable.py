import logging
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from datetime import date, datetime
from collections import OrderedDict
from cfg import config
from utils import Caliper
from tracker.dal import dal
from tracker.helpers import merge_records_by_date, to_time, safe_div
from tracker.structs import StrRecordOrderedDict
from widgets import get_scrollbar

log = logging.getLogger("TRK")


class TimeTablePrintout:

    def __init__(self):
        self.upd = -1
        self._create_text_edit()

    def _create_text_edit(self):
        self.caliper = Caliper(config.qfont_button)
        self.qTextEdit = QTextEdit()
        self.qTextEdit.setFont(config.qfont_button)
        self.qTextEdit.setAcceptRichText(False)
        self.qTextEdit.setVerticalScrollBar(get_scrollbar())
        self.qTextEdit.contextMenuEvent = lambda *args, **kwargs: None
        self.qTextEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.qTextEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.qTextEdit.setReadOnly(True)

    @property
    def lines_lim(self) -> int:
        return int(config["geo"][1] // self.caliper.sch)

    def get(self) -> QTextEdit:
        return self.qTextEdit

    def refresh(self):
        if self.upd < dal.upd:
            data = dal.get_data()
            self.start_date = next(iter(data))
            data = merge_records_by_date(
                data, config["tracker"]["disp_datefmt"]
            )
            printout = self.get_timespent_printout(data)
            self.qTextEdit.setText(printout)
            self.upd = dal.upd
            log.debug("Refreshed TimeTable Tab")

    def get_timespent_printout(self, data: StrRecordOrderedDict) -> str:
        try:
            printout = "\n".join(self.get_table(data))
        except Exception as e:
            log.error(e, exc_info=True)
            printout = f"{type(e).__name__} occurred. See log file for more details."
        return printout

    def get_table(self, data: StrRecordOrderedDict) -> list[str]:
        self.len_datefmt = len(
            datetime.now().strftime(config["tracker"]["disp_datefmt"])
        )
        self.cols_lens = OrderedDict()
        self.multiple_cols = (
            sum(v["active"] for v in config["tracker"]["stat_cols"].values()) > 1
        )
        for k, v in config["tracker"]["stat_cols"].items():
            self.cols_lens[k] = len(v["name"]) + 2

        header, split = self.__get_header_and_split()
        out = list()
        out.append(header)
        out.append(split)
        out.extend(self.__get_rows(data))
        out.append(split)
        out.append(self.__get_summary(data))
        return out

    def __get_header_and_split(self) -> tuple[str, str]:
        header = f"{'Date':^{self.len_datefmt}} "
        split = "─" * (self.len_datefmt + 1)
        for v in (v for v in config["tracker"]["stat_cols"].values() if v["active"]):
            header += f"│  {v['name']}  "
            split += "┼" + "─" * (len(v["name"]) + 4)
        if self.multiple_cols:
            header += "│ Total "
            split += "┼───────"
        if config["tracker"]["incl_col_new"]:
            header += "│ %New "
            split += "┼──────"
        return header, split

    def __get_rows(self, data: StrRecordOrderedDict) -> list[str]:
        out = list()
        for v in list(data.items())[-self.lines_lim + 4 :]:
            r = f"{v[0]:>{self.len_datefmt}} "
            if config["tracker"]["stat_cols"]["fcs"]["active"]:
                r += f"│ {to_time(v[1].fcs.hours):>{self.cols_lens['fcs']}} "
            if config["tracker"]["stat_cols"]["duo"]["active"]:
                r += f"│ {to_time(v[1].duo.hours):>{self.cols_lens['duo']}} "
            if config["tracker"]["stat_cols"]["wrt"]["active"]:
                r += f"│ {to_time(v[1].wrt.hours):>{self.cols_lens['wrt']}} "
            if config["tracker"]["stat_cols"]["rdg"]["active"]:
                r += f"│ {to_time(v[1].rdg.hours):>{self.cols_lens['rdg']}} "
            if config["tracker"]["stat_cols"]["lst"]["active"]:
                r += f"│ {to_time(v[1].lst.hours):>{self.cols_lens['lst']}} "
            if config["tracker"]["stat_cols"]["spk"]["active"]:
                r += f"│ {to_time(v[1].spk.hours):>{self.cols_lens['spk']}} "
            if config["tracker"]["stat_cols"]["ent"]["active"]:
                r += f"│ {to_time(v[1].ent.hours):>{self.cols_lens['ent']}} "
            if self.multiple_cols:
                r += f"│ {to_time(v[1].total_hours):>5} "
            if config["tracker"]["incl_col_new"]:
                r += f"│ {safe_div(v[1].total_hours_new, v[1].total_hours):>4.0%}"
            out.append(r)
        return out

    def __get_summary(self, data: StrRecordOrderedDict) -> str:
        duo_ts, fcs_ts, new_ts = 0, 0, 0
        wrt_ts, rdg_ts, lst_ts, spk_ts, ent_ts = 0, 0, 0, 0, 0
        for i in data.values():
            duo_ts += i.duo.hours
            fcs_ts += i.fcs.hours
            wrt_ts += i.wrt.hours
            rdg_ts += i.rdg.hours
            lst_ts += i.lst.hours
            spk_ts += i.spk.hours
            ent_ts += i.ent.hours
            new_ts += i.total_hours_new
        new_ts = safe_div(new_ts, duo_ts + fcs_ts + wrt_ts)
        yrs, mts = divmod(
            (date.today() - self.start_date).days,
            365.25,
        )
        tt = f"Y{yrs:.0f}M{mts/30.437:.0f}"
        summary = f"{tt:>{self.len_datefmt}} "
        if config["tracker"]["stat_cols"]["fcs"]["active"]:
            summary += f"│ {round(fcs_ts):>{self.cols_lens['fcs']}} "
        if config["tracker"]["stat_cols"]["duo"]["active"]:
            summary += f"│ {round(duo_ts):>{self.cols_lens['duo']}} "
        if config["tracker"]["stat_cols"]["wrt"]["active"]:
            summary += f"│ {round(wrt_ts):>{self.cols_lens['wrt']}} "
        if config["tracker"]["stat_cols"]["rdg"]["active"]:
            summary += f"│ {round(rdg_ts):>{self.cols_lens['rdg']}} "
        if config["tracker"]["stat_cols"]["lst"]["active"]:
            summary += f"│ {round(lst_ts):>{self.cols_lens['lst']}} "
        if config["tracker"]["stat_cols"]["spk"]["active"]:
            summary += f"│ {round(spk_ts):>{self.cols_lens['spk']}} "
        if config["tracker"]["stat_cols"]["ent"]["active"]:
            summary += f"│ {round(ent_ts):>{self.cols_lens['ent']}} "
        if self.multiple_cols:
            summary += (
                f"│ {round(duo_ts+fcs_ts+wrt_ts+rdg_ts+lst_ts+spk_ts+ent_ts):>5} "
            )
        if config["tracker"]["incl_col_new"]:
            summary += f"│ {new_ts:>4.0%}"
        return summary
