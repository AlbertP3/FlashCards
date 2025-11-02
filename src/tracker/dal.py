import os
import logging
from time import time
from collections import OrderedDict
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from csv import DictReader, DictWriter
from PyQt5.QtCore import QTime
from cfg import config
from int import fcc_queue, LogLvl
from tracker.structs import RecordOrderedDict, Record, SubRecord, IMM_CATS
from logtools import audit_log
from data_types import adlt

log = logging.getLogger("DAL")


@dataclass
class DALSpecs:
    fcs_path: str = "./src/res/db.csv"
    duo_path: str = "./src/res/duo.csv"
    imm_path: str = "./src/res/imm.csv"
    duo_cols: tuple = ("date", "lessons", "minutes", "lng")
    fcs_cols: tuple = (
        "TIMESTAMP",
        "SIGNATURE",
        "LNG",
        "TOTAL",
        "POSITIVES",
        "SEC_SPENT",
        "KIND",
        "IS_FIRST",
    )
    imm_cols: tuple = ("date", "seconds", "title", "category", "lng")
    imm_datefmt: str = r"%Y-%m-%dT%H:%M:%S"
    duo_datefmt: str = r"%Y-%m-%d"
    fcs_datefmt = r"%Y-%m-%dT%H:%M:%S"
    sep: str = ";"


class DataAccessLayer:

    def __init__(self):
        self.upd = 0
        self.spc = DALSpecs()
        self.validate_setup()
        self.content = OrderedDict()
        self.reset_monitor()
        self.stopwatch_elapsed = QTime(0, 0, 0)
        self.stopwatch_running = False
        self.stopwatch_timer = None
        self.__imm_rows: int = 0

    def validate_setup(self):
        if not os.path.exists(self.spc.duo_path):
            with open(self.spc.duo_path, "w") as file:
                d = DictWriter(
                    file, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep
                )
                d.writeheader()
            log.debug(f"Created Duo database: {self.spc.duo_path}")
        if not os.path.exists(self.spc.imm_path):
            with open(self.spc.imm_path, "w") as file:
                d = DictWriter(
                    file, fieldnames=self.spc.imm_cols, delimiter=self.spc.sep
                )
                d.writeheader()
            log.debug(f"Created Imm database: {self.spc.imm_path}")

    def reset_monitor(self):
        self.monitor = {
            self.spc.fcs_path: 0,
            self.spc.duo_path: 0,
            self.spc.imm_path: 0,
        }

    def should_reload(self) -> bool:
        """Check mtimes of monitored files"""
        should_run = False
        for path, modtime in self.monitor.items():
            current_mod_time = os.path.getmtime(path)
            if current_mod_time != modtime:
                self.monitor[path] = current_mod_time
                should_run = True
        return should_run

    def add_duo_record_final(self, lng: str, lessons: int, timespent: int):
        """
        Adds a final record (weekly interval).
        Removes all preliminary records newer than the previous Progress Report.
        """
        wk_alloc = [0] * 7
        pred_lessons, pred_timespent = 0, 0
        found = False
        new_report_date = self.get_duo_last_report_date()
        prev_report_date = new_report_date - timedelta(days=7)
        tgt_dstr = new_report_date.strftime(self.spc.duo_datefmt)
        record = {
            "date": tgt_dstr,
            "lessons": lessons,
            "minutes": timespent,
            "lng": lng,
        }
        rows: list[dict] = []
        with open(self.spc.duo_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep)
            for row in reader:
                if row["lng"] == lng:
                    row_date = datetime.strptime(
                        row["date"], self.spc.duo_datefmt
                    ).date()
                    if row_date <= prev_report_date and row["minutes"].isnumeric():
                        rows.append(row)
                    elif row_date == new_report_date:
                        found = True
                    else:
                        wk_alloc[row_date.weekday()] += float(row["minutes"])
                        pred_lessons += int(row["lessons"])
                        pred_timespent += float(row["minutes"])
                else:
                    rows.append(row)
        rows.append(record)
        with open(self.spc.duo_path, "w") as f:
            writer = DictWriter(f, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep)
            writer.writeheader()
            writer.writerows(rows)
        if sum(wk_alloc) > 0:
            config["tracker"]["duo"]["wk_alloc"] = [
                round(x + y, 3)
                for x, y in zip(config["tracker"]["duo"]["wk_alloc"], wk_alloc)
            ]
            config["tracker"]["duo"]["cnt"] += 1
        if int(pred_timespent - timespent) != 0 and pred_timespent > 0:
            log.debug(f"Predicted {pred_timespent:.0f} minutes but got {timespent}")
        if pred_lessons != lessons and pred_lessons > 0:
            log.debug(f"Predicted {pred_lessons} lessons but got {lessons}")
        fcc_queue.put_notification("Added Duo final record", LogLvl.important)
        audit_log(
            op=adlt.op.merge if found else adlt.op.add,
            data=record | {"final": True},
            filepath=self.spc.duo_path,
            author=adlt.author.trk,
            row=len(rows) - 1,
        )
        self.upd = time()

    def add_duo_record_preliminary(
        self, lng: str, lessons: int, timespent: float = 0, offset: int = 0
    ):
        """
        Adds a preliminary record (daily interval) for today.
        Increments the corresonding record if exists.
        If timespent is missing then it will be estimated based on an average.
        """
        tgt_dstr = (date.today() - timedelta(days=offset)).strftime(r"%Y-%m-%d")
        rows: list[dict] = []
        found = False
        with open(self.spc.duo_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep)
            for row in reader:
                if row["lng"] == lng:
                    if row["date"] == tgt_dstr:
                        row.update(
                            {
                                "date": tgt_dstr,
                                "lessons": int(row["lessons"]) + lessons,
                                "minutes": round(float(row["minutes"]) + timespent, 2),
                            }
                        )
                        found = True
                rows.append(row)
        if not found:
            rows.append(
                {
                    "date": tgt_dstr,
                    "lessons": lessons,
                    "minutes": round(float(timespent), 2),
                    "lng": lng,
                }
            )
        with open(self.spc.duo_path, "w") as f:
            writer = DictWriter(f, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep)
            writer.writeheader()
            writer.writerows(rows)
        fcc_queue.put_notification(
            f"Added Duo preliminary record #{rows[-1]['lessons']}",
            LogLvl.important,
        )
        audit_log(
            op=adlt.op.upd if found else adlt.op.add,
            data=rows[-1] | {"final": False},
            filepath=self.spc.duo_path,
            author=adlt.author.trk,
            row=len(rows) - 1,
        )
        self.upd = time()

    def add_imm_record(self, lng: str, total_seconds: int, title: str, category: str):
        record = {
            "date": datetime.today().strftime(self.spc.imm_datefmt),
            "seconds": total_seconds,
            "title": title,
            "category": category,
            "lng": lng,
        }
        with open(self.spc.imm_path, "a") as f:
            DictWriter(f, self.spc.imm_cols, delimiter=self.spc.sep).writerow(record)
        self.__imm_rows += 1
        fcc_queue.put_notification(f"Added Immersion record", LogLvl.important)
        audit_log(
            op=adlt.op.add,
            data=record,
            filepath=self.spc.imm_path,
            author=adlt.author.trk,
            row=self.__imm_rows,
        )
        self.upd = time()

    def get_data(self) -> RecordOrderedDict:
        """Reads data from active sources. Uses cache."""
        if self.should_reload():
            self.content.clear()
            if config["tracker"]["stat_cols"]["fcs"]["active"]:
                self._load_fcs_data(self.content)
            if config["tracker"]["stat_cols"]["duo"]["active"]:
                self._load_duo_data(self.content)
            if self.get_active_imm_categories():
                self._load_imm_data(self.content)
            self.upd = time()
            self.content = OrderedDict(sorted(self.content.items()))
            log.debug("Loaded Tracker data")
        return self.content

    def _load_duo_data(self, content: RecordOrderedDict) -> RecordOrderedDict:
        """
        Updates inplace <content> with data from Duo file.
        Transforms weekly data to daily interval according to wk_alloc
        Handles the preliminary record
        """
        wk_alloc = self.get_wk_alloc()
        with open(self.spc.duo_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.duo_cols, delimiter=self.spc.sep)
            for row in reader:
                if row["lng"] in config["languages"]:
                    ld = datetime.strptime(row["date"], r"%Y-%m-%d").date()
                    if row["minutes"].isdigit():  # final record (weekly)
                        for day in range(1, 8):
                            wshare = wk_alloc[config["tracker"]["duo"]["wdi"] - day]
                            if wshare == 0:
                                continue
                            hrs = int(row["minutes"]) * wshare / 60
                            new_rec = Record(
                                duo=SubRecord(
                                    hours=hrs,
                                    lessons=round(int(row["lessons"]) * wshare, 0),
                                    hours_new=hrs,
                                )
                            )
                            k = ld - timedelta(days=day)
                            try:
                                content[k] += new_rec
                            except KeyError:
                                content[k] = new_rec
                    else:  # preliminary record (daily)
                        hrs = float(row["minutes"]) / 60
                        new_rec = Record(
                            duo=SubRecord(
                                hours=hrs,
                                lessons=round(int(row["lessons"]), 0),
                                hours_new=hrs,
                            )
                        )
                        try:
                            content[ld] += new_rec
                        except KeyError:
                            content[ld] = new_rec
        return content

    def get_duo_last_report_date(self) -> date:
        lrd = date.today()
        while lrd.weekday() != config["tracker"]["duo"]["wdi"]:
            lrd -= timedelta(days=1)
        return lrd

    def get_wk_alloc(self) -> list:
        if config["tracker"]["duo"]["cnt"] < 1:
            wk_alloc = [0.142857143] * 7
        else:
            total = sum(config["tracker"]["duo"]["wk_alloc"])
            wk_alloc = [x / total for x in config["tracker"]["duo"]["wk_alloc"]]
        return wk_alloc

    def _load_fcs_data(self, content: RecordOrderedDict) -> RecordOrderedDict:
        """Updates inplace <content> with data from fcs file"""
        with open(self.spc.fcs_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.fcs_cols, delimiter=self.spc.sep)
            for row in reader:
                if row["LNG"] in config["languages"]:
                    ld = datetime.strptime(
                        row["TIMESTAMP"], self.spc.fcs_datefmt
                    ).date()
                    hrs = int(row["SEC_SPENT"]) / 3600
                    pos = int(row["POSITIVES"])
                    total = int(row["TOTAL"])
                    if row["IS_FIRST"] == "1":
                        hrs_new = hrs
                    else:
                        hrs_new = 0
                    new_rec = Record(
                        fcs=SubRecord(
                            hours=hrs,
                            lessons=1,
                            hours_new=hrs_new,
                            positives=pos,
                            total=total,
                        )
                    )
                    try:
                        content[ld] += new_rec
                    except KeyError:
                        content[ld] = new_rec
        return content

    def _load_imm_data(self, content: RecordOrderedDict) -> RecordOrderedDict:
        """Updates inplace <content> with data from imm file"""
        seen_titles = set()
        act_imm_cats = self.get_active_imm_categories()
        self.__imm_rows = 0
        with open(self.spc.imm_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.imm_cols, delimiter=self.spc.sep)
            for row in reader:
                self.__imm_rows += 1
                if row["category"] not in act_imm_cats:
                    continue
                elif row["title"] in seen_titles:
                    imm_hours_new = 0
                else:
                    imm_hours_new = int(row["seconds"]) / 3600
                    seen_titles.add(row["title"])
                ld = datetime.strptime(row["date"], self.spc.imm_datefmt).date()
                imm_rec = SubRecord(
                    lessons=1,
                    hours=int(row["seconds"]) / 3600,
                    hours_new=imm_hours_new,
                )
                if row["category"] == "wrt":
                    new_rec = Record(wrt=imm_rec)
                elif row["category"] == "rdg":
                    new_rec = Record(rdg=imm_rec)
                elif row["category"] == "lst":
                    new_rec = Record(lst=imm_rec)
                elif row["category"] == "spk":
                    new_rec = Record(spk=imm_rec)
                elif row["category"] == "ent":
                    new_rec = Record(ent=imm_rec)
                else:
                    raise ValueError(f"Unknown category: {row['category']}")
                try:
                    content[ld] += new_rec
                except KeyError:
                    content[ld] = new_rec
        return content

    def get_active_imm_categories(self) -> set:
        return {
            k
            for k, v in config["tracker"]["stat_cols"].items()
            if (v["active"] and k in IMM_CATS)
        }

    def get_imm_category_mapping(self) -> dict:
        history = dict()
        with open(self.spc.imm_path, "r") as f:
            next(f)  # skip header
            reader = DictReader(f, fieldnames=self.spc.imm_cols, delimiter=self.spc.sep)
            for row in reader:
                history.setdefault(row["category"], set()).add(row["title"])
        return history


dal = DataAccessLayer()
