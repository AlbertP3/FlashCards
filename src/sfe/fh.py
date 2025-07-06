import re
from abc import abstractmethod
import pandas as pd
import logging
from PyQt5.QtCore import pyqtSignal, QObject
from DBAC import db_conn, FileDescriptor
from cfg import config
from utils import fcc_queue, LogLvl

log = logging.getLogger("SFE")


class FileHandler(QObject):
    mod_signal = pyqtSignal(bool)

    def __init__(self, fd: FileDescriptor):
        super().__init__()
        self.lookup_re = re.compile(config["sfe"]["lookup_re"])
        self.headers: list = ["", ""]
        self.src_data: pd.DataFrame = pd.DataFrame()
        self.data_view: pd.DataFrame = pd.DataFrame()
        self.filepath: str = fd.filepath
        self.__is_saved = True
        self.query: str = ""
        self.is_iln = bool(config["ILN"].get(self.filepath, False))

    def audit_log(self, op, data, row, col):
        status = "SAVED" if config["sfe"]["autosave"] else "STAGED"
        log.info(f"{op} {data} {status} TO {self.filepath} AT [{row},{col}]")

    @property
    def is_saved(self) -> bool:
        return self.__is_saved

    @is_saved.setter
    def is_saved(self, x: bool):
        self.__is_saved = x
        self.mod_signal.emit(x)

    @property
    def total_visible_rows(self) -> int:
        return len(self.data_view)

    @property
    def total_src_rows(self) -> int:
        return len(self.src_data)

    @property
    def iln(self) -> int:
        if self.is_iln:
            return self.total_src_rows - config["ILN"][self.filepath]
        else:
            return 0

    @property
    def total_columns(self) -> int:
        return len(self.headers)

    @abstractmethod
    def load_data(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save(self) -> None:
        raise NotImplementedError

    def mod_tracker(fn):
        def function(self, *args, **kwargs):
            fn(self, *args, **kwargs)
            self.is_saved = False
            if config["sfe"]["autosave"]:
                self.save()

        return function

    @mod_tracker
    def update_cell(self, row: int, col: int, value: str) -> None:
        self.src_data.iat[row, col] = value
        self.audit_log("UPDATE", [value], row, col)

    @mod_tracker
    def create_row(self, value: list[str]) -> None:
        self.src_data.loc[len(self.src_data)] = value
        self.audit_log("ADD", value, len(self.src_data) - 1, ":")

    @mod_tracker
    def delete_rows(self, rows: list[int]) -> None:
        sel_rows = self.src_data.loc[rows]
        self.src_data.drop(rows, inplace=True)
        self.src_data.reset_index(drop=True, inplace=True)
        try:
            iln = config["ILN"][self.filepath]
            for i in rows:
                if i < iln:
                    config["ILN"][self.filepath] -= 1
        except KeyError:
            pass
        for idx, row in sel_rows.iterrows():
            self.audit_log("DELETE", row.to_list(), idx, ":")

    def is_duplicate(self, card: dict) -> bool:
        return (self.src_data[list(card)] == pd.Series(card)).all(1).any()

    def lookup(self, query: str, col: int) -> str:
        mask1 = self.src_data[self.headers[col]].str.contains(
            query, regex=False, na=False
        )
        mask2 = self.src_data.loc[mask1, self.headers[col]].str.contains(
            config["sfe"]["lookup_re"], regex=True, na=False
        )
        df = self.src_data.loc[mask1].loc[mask2]
        if df.empty:
            return ""
        phrase = ", ".join(self.lookup_re.findall(df.iat[0, col]))
        # if len(df) > 1:
        #     phrase += " (?)"
        return phrase

    def filter(self, query: str = "") -> None:
        if config["sfe"]["re"]:
            try:
                re.compile(query)
                use_re = True
            except re.error:
                use_re = False
        else:
            use_re = False

        if len(query) > len(self.query):
            src = self.data_view
        else:
            src = self.src_data

        mask = (
            src[self.headers]
            .apply(
                lambda col: col.str.contains(query, case=False, regex=use_re, na=False)
            )
            .any(axis=1)
        )

        self.data_view = src[mask]
        self.query = query

    def remove_filter(self):
        self.query = ""
        self.data_view = self.src_data


class CSVFileHandler(FileHandler):

    def __init__(self, fd: FileDescriptor):
        super().__init__(fd)

    def load_data(self):
        try:
            self.src_data = pd.read_csv(
                self.filepath,
                encoding="utf-8",
                dtype=str,
                index_col=False,
            )
            self.headers = list(self.src_data.columns)
            self.data_view = self.src_data
            self.is_saved = True
            log.info(f"Loaded {type(self).__name__} for: {self.filepath}")
        except Exception as e:
            log.error(e, stack_info=True)

    def save(self) -> None:
        self.src_data.to_csv(
            self.filepath,
            columns=self.headers,
            encoding="utf-8",
            index=False,
        )
        self.is_saved = True


class VoidFileHandler(FileHandler):
    def __init__(self, fd: FileDescriptor):
        super().__init__(fd)

    def load_data(self) -> None:
        return

    def save(self) -> None:
        return


def get_filehandler(filepath: str) -> FileHandler:
    try:
        fd = db_conn.files[filepath]
        if fd.ext == ".csv":
            fh = CSVFileHandler(fd)
            config["sfe"]["last_file"] = fd.filepath
        else:
            raise AttributeError(f"Unsupported file extension: {fd.ext}")
    except Exception as e:
        fh = VoidFileHandler(FileDescriptor(filepath=filepath, ext=".void"))
        log.warning(e, stack_info=True)
        fcc_queue.put_notification(
            f"{type(e).__name__} occurred while loading SFE", lvl=LogLvl.err
        )
    return fh
