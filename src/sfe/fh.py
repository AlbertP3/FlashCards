import re
from abc import abstractmethod
import pandas as pd
import logging
from PyQt5.QtCore import QObject
from DBAC import FileDescriptor
from cfg import config
from int import fcc_queue, LogLvl, sbus
from logtools import audit_log
from data_types import SfeMods, adlt

log = logging.getLogger("SFE")


class FileHandler(QObject):

    def __init__(self, fd: FileDescriptor):
        super().__init__()
        self.lookup_re = re.compile(config["sfe"]["lookup_re"])
        self.headers: list = ["", ""]
        self.src_data: pd.DataFrame = pd.DataFrame()
        self.data_view: pd.DataFrame = pd.DataFrame()
        self.fd = fd
        self.is_saved = True
        self.query: str = ""
        self.is_iln = bool(config["ILN"].get(self.fd.filepath, False))

    def audit_log(self, op, data, row, col):
        status = adlt.stat.saved if config["sfe"]["autosave"] else adlt.stat.staged
        audit_log(
            op=op,
            data=data,
            row=row,
            col=col,
            filepath=self.fd.filepath,
            author=adlt.author.sfe,
            status=status,
            stacklevel=3,
        )

    @property
    def filepath(self) -> str:
        return self.fd.filepath

    @property
    def total_visible_rows(self) -> int:
        return len(self.data_view)

    @property
    def total_src_rows(self) -> int:
        return len(self.src_data)

    @property
    def iln(self) -> int:
        if self.is_iln:
            return self.total_src_rows - config["ILN"][self.fd.filepath]
        else:
            return self.total_src_rows

    @property
    def total_columns(self) -> int:
        return len(self.headers)

    @abstractmethod
    def load_data(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save(self) -> None:
        raise NotImplementedError

    def mod_tracker(mod: int):
        def decorator(fn):
            def wrapper(self, *args, **kwargs):
                fn(self, *args, **kwargs)
                if config["sfe"]["autosave"]:
                    self.save()
                else:
                    self.is_saved = False
                sbus.sfe_mod.emit(mod)

            return wrapper

        return decorator

    @mod_tracker(mod=SfeMods.UPDATE)
    def update_cell(self, row: int, col: int, value: str) -> None:
        self.src_data.iat[row, col] = value
        self.audit_log(adlt.op.upd, [value], row, col)

    @mod_tracker(mod=SfeMods.UPDATE)
    def reverse_row(self, idx: int):
        self.src_data.iloc[idx] = self.src_data.iloc[idx][::-1].values
        self.audit_log(adlt.op.rev, self.src_data.iloc[idx].to_list(), idx, ":")

    @mod_tracker(mod=SfeMods.MOVE)
    def move_row(self, idx: int, offset: int):
        r0 = self.src_data.iloc[idx].copy()
        r1 = self.src_data.iloc[idx + offset].copy()
        self.src_data.iloc[idx] = r1
        self.src_data.iloc[idx + offset] = r0
        self.audit_log(adlt.op.mv, self.src_data.iloc[idx].to_list(), idx, col=":")
        self.audit_log(
            adlt.op.mv, self.src_data.iloc[idx + offset].to_list(), idx + offset, col=":"
        )

    @mod_tracker(mod=SfeMods.CREATE)
    def create_row(self, value: list[str]) -> None:
        idx = len(self.src_data)
        self.src_data.loc[idx] = value
        self.refresh_view()
        self.audit_log(adlt.op.add, value, idx, ":")

    @mod_tracker(mod=SfeMods.DELETE)
    def delete_rows(self, rows: list[int]) -> None:
        sel_rows = self.src_data.loc[rows]
        self.src_data.drop(rows, inplace=True)
        self.src_data.reset_index(drop=True, inplace=True)
        self.refresh_view()
        try:
            iln = config["ILN"][self.fd.filepath]
            for i in rows:
                if i < iln:
                    config["ILN"][self.fd.filepath] -= 1
        except KeyError:
            pass
        for idx, row in sel_rows.iterrows():
            self.audit_log(adlt.op.rem, row.to_list(), idx, ":")

    def is_duplicate_precheck(self, card: dict) -> bool:
        return (self.src_data[list(card)] == pd.Series(card)).all(1).any()

    def is_duplicate_fullcheck(self, card: dict) -> bool:
        """Check if a card already exists in the src data. Ignores hints."""
        cleaned_src = self.src_data[list[card]].apply(
            lambda col: col.str.replace(config["sfe"]["lookup_re"], "", regex=True)
            .str.removesuffix(config["sfe"]["hint"])
            .str.strip()
        )
        return (cleaned_src == pd.Series(card)).all(1).any()

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

        if query.startswith(self.query):
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

    def refresh_view(self):
        q = self.query
        self.remove_filter()
        if q:
            self.filter(q)


class CSVFileHandler(FileHandler):

    def __init__(self, fd: FileDescriptor):
        super().__init__(fd)

    def load_data(self):
        try:
            self.src_data = pd.read_csv(
                self.fd.filepath,
                encoding="utf-8",
                dtype=str,
                index_col=False,
            )
            self.headers = list(self.src_data.columns)
            self.data_view = self.src_data
            self.is_saved = True
            log.info(f"Loaded {type(self).__name__} for: {self.fd.filepath}")
        except Exception as e:
            log.error(e, stack_info=True)

    def save(self) -> None:
        self.src_data.to_csv(
            self.fd.filepath,
            columns=self.headers,
            encoding="utf-8",
            index=False,
        )
        self.is_saved = True


class TmpFileHandler(FileHandler):
    def __init__(self, fd: FileDescriptor):
        super().__init__(fd)

    def load_data(self) -> None:
        try:
            self.headers = list(self.fd.headers)
            self.src_data = (
                self.fd.data.copy(deep=True)
                .sort_values(by="__oid", inplace=False)
                .reset_index(drop=True, inplace=False)[self.headers]
            )
            self.data_view = self.src_data
            self.is_saved = True
            log.info(f"Loaded {type(self).__name__} for: {self.fd.signature}")
        except Exception as e:
            log.error(e, stack_info=True)

    def save(self) -> None:
        self.is_saved = True


class VoidFileHandler(FileHandler):
    def __init__(self, fd: FileDescriptor):
        super().__init__(fd)

    def load_data(self) -> None:
        self.headers = ["N/A", "N/A"]
        self.src_data = pd.DataFrame([["", ""]], columns=self.headers)
        self.data_view = self.src_data

    def save(self) -> None:
        return

    def lookup(self, query: str, col: int) -> str:
        return ""


def get_filehandler(fd: FileDescriptor) -> FileHandler:
    try:
        if fd.ext == ".csv":
            fh = CSVFileHandler(fd)
            config["sfe"]["last_file"] = fd.filepath
        elif fd.tmp == True:
            fh = TmpFileHandler(fd)
        else:
            raise AttributeError(f"Unsupported file extension: {fd.ext}")
    except Exception as e:
        fh = VoidFileHandler(FileDescriptor(filepath="void", ext=".void"))
        log.warning(e, stack_info=True)
        fcc_queue.put_notification(
            f"{type(e).__name__} occurred while loading SFE", lvl=LogLvl.err
        )
    return fh
