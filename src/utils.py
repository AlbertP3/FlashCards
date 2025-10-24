from PyQt5.QtGui import QFont, QFontMetricsF
from PyQt5.QtCore import QRunnable, pyqtSlot, pyqtSignal, QObject, Qt
from collections import deque
from functools import cache, wraps
from datetime import timedelta
import os
import platform
import re
import inspect
from time import perf_counter
import logging
from typing import Union, Callable, Optional
from cfg import config


log = logging.getLogger("UTL")


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def singular(fn: Callable):
    fns = dict()

    @wraps(fn)
    def decorator(*args, **kwargs):
        nonlocal fns
        if not fns.get(fn.__qualname__):
            # If PyQt passed an unexpected boolean as last positional arg, drop it
            if (
                args
                and isinstance(args[-1], bool)
                and fn.__code__.co_argcount < len(args)
            ):
                args = args[:-1]
            fns[fn.__qualname__] = True
            result = fn(*args, **kwargs)
            fns.pop(fn.__qualname__)
            return result

    return decorator


NSRE = re.compile(r"(\d+)")


def nat_sort_key(s: str) -> list:
    """Generate a key for natural sorting of strings"""
    return [(int(text) if text.isdigit() else text.lower()) for text in NSRE.split(s)]


def get_filename_from_path(path, include_extension=False):
    filename = os.path.basename(path)
    if not include_extension:
        filename = filename.split(".")[0]
    return filename


def get_sign(num, plus_sign="+", neg_sign="-"):
    if num > 0:
        return plus_sign
    elif num < 0:
        return neg_sign
    else:
        return ""


def find_case_insensitive(text: str, collection: list[str]) -> str:
    """
    Returns a matching string from a collection. Ignores case.
    Raises KeyError if not found
    """
    t = text.lower()
    for i in collection:
        if t == i.lower():
            return i
    raise KeyError


def format_timedelta(tmd: timedelta):
    if tmd.days >= 365:
        interval, time_value = "year", round(tmd.days / 365.25, 1)
    elif tmd.days >= 31:
        interval, time_value = "month", round(tmd.days / 30.437, 1)
    elif tmd.days >= 1:
        interval, time_value = "day", round(tmd.total_seconds() / 86_400, 0)
    elif tmd.total_seconds() >= 3600:
        interval, time_value = "hour", round(tmd.total_seconds() / 3600, 0)
    elif tmd.total_seconds() >= 60:
        interval, time_value = "minute", round(tmd.total_seconds() / 60, 0)
    else:
        interval, time_value = "second", round(tmd.total_seconds(), 0)

    suffix = "" if int(time_value) == 1 else "s"
    prec = 0 if int(time_value) == time_value else "1"
    return f"{time_value:.{prec}f} {interval}{suffix}"


SECONDS_CONVERTERS = {
    "minute": (60, 1),
    "hour": (3600, 60),
    "day": (86400, 3600),
    "week": (604800, 86400),
    "month": (18408297.6, 604800),
    "year": (220899571.2, 18408297.6),
}


def format_seconds_to(
    total_seconds: Union[int, float],
    interval: str,
    rem: int = 2,
    interval_name: Optional[str] = None,
    null_format: Optional[str] = None,
    pref_len=0,
    sep=".",
) -> str:
    _int, _prev_int = SECONDS_CONVERTERS[interval]
    tot_int, _rem = divmod(total_seconds, _int)
    rem_int = int(_rem // _prev_int)

    if null_format is not None and tot_int + rem_int == 0:
        res = null_format
        pfi = 0
    elif rem:
        res = f"{tot_int:.0f}{sep}{rem_int:0{rem}d}"
        pfi = tot_int
    else:
        res = f"{total_seconds / _int:.0f}"
        pfi = int(total_seconds / _int + 0.49)

    if interval_name:
        postfix = ("s", "")[pfi == 1]
        res = f"{res} {interval_name}{postfix}"

    if pref_len != 0:
        res = res[:pref_len].rjust(pref_len, " ")
        if res.endswith(sep):
            res = res[:-1] + " "

    return res


def flatten_dict(d: dict, root: str = "BASE", lim_chars: Optional[int] = None) -> list:
    res = list([root, k, str(v)] for k, v in d.items() if not isinstance(v, dict))
    for k, v in d.items():
        if isinstance(v, dict):
            res.extend(flatten_dict(v, root=k))
    if lim_chars:
        res = [[str(x)[:lim_chars] for x in i] for i in res]
    return res


class Caliper:
    """Works on pixels!"""

    def __init__(
        self, qFont: QFont, suf: str = "", fill: str = "\u0020", mg: float = 1.0
    ):
        self.doc_margin = mg
        self.fmetrics = QFontMetricsF(qFont)
        self.suffix = suf or config["theme"]["default_suffix"]
        self.scw = self.fmetrics.maxWidth()
        self.sch = self.fmetrics.height()
        self.ls = self.fmetrics.lineSpacing()
        self.suflen = self.strwidth(self.suffix)
        self.filler = fill
        self.fillerlen = self.strwidth(fill)

    @cache
    def pixlen(self, char: str) -> float:
        return self.fmetrics.horizontalAdvance(char) * self.doc_margin

    def strwidth(self, text: str) -> float:
        return self.fmetrics.horizontalAdvance(text) * self.doc_margin

    def abbreviate(self, text: str, pixlim: float) -> str:
        """Trims text to the given pixel-length"""
        excess = self.strwidth(text) - pixlim
        if excess <= 0:
            return text
        else:
            try:
                i = 0
                while excess > 0:
                    i -= 1
                    excess -= self.pixlen(text[i])
            except IndexError:
                return text
            else:
                return text[:i]

    def make_cell(self, text: str, pixlim: float, align: str = "left") -> str:
        txtwt = self.strwidth(text)
        if txtwt > pixlim:
            out_len = txtwt + self.suflen
            i = 0
            while out_len > pixlim:
                i -= 1
                out_len -= self.pixlen(text[i])
            out = f"{text[:i]}{self.suffix}"
            pixlim -= out_len
        else:
            out = text
            pixlim -= txtwt

        if align == "center":
            d, r = divmod(pixlim, 2)
            rpad = self.filler * int(round((d + r) / self.fillerlen, 2))
            lpad = self.filler * int(round(d / self.fillerlen, 2))
        else:
            pad = self.filler * int(round(pixlim / self.fillerlen, 2))
            lpad = pad if align == "right" else ""
            rpad = pad if align == "left" else ""

        return f"{lpad}{''.join(out)}{rpad}"

    def make_table(
        self,
        data: list[list[str]],
        pixlim: Union[float, list],
        headers: Optional[list] = None,
        align: Union[str, list] = "left",
        sep: str = " | ",
        keep_last_border: bool = True,
    ):
        if isinstance(pixlim, (float, int)):
            part = pixlim / len(data[0])
            pixlim = [part for _ in range(len(data[0]))]
        sepw = (self.strwidth(sep) * (len(data[0])) - int(keep_last_border)) / len(
            data[0]
        )
        for i, p in enumerate(pixlim):
            pixlim[i] = p - sepw
        if isinstance(align, str):
            align = [align for _ in range(len(data[0]))]
        if headers:
            data = [headers] + data
        out = list()
        for row in data:
            new_row = ""
            for i, text in enumerate(row):
                new_row += (
                    self.make_cell(
                        text,
                        pixlim=pixlim[i],
                        align=align[i],
                    )
                    + sep
                )
            if not keep_last_border:
                new_row = new_row[: -len(sep)]
            out.append(new_row)
        return "\n".join(out)


def is_valid_filename(filename: str) -> bool:
    system = platform.system()

    if filename == "":
        return False

    if len(filename) > 255:
        return False

    if re.search(r"""[<>:"/'\\|?!*().]""", filename):
        return False

    if system == "Windows":
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]
        if filename.upper() in reserved_names:
            return False

    return True


def get_caller(frame: int = 1) -> str:
    return inspect.stack()[frame].function


def translate(text: str, on_empty: bool = False) -> bool:
    """Parse string to boolean"""
    if len(text) == 0:
        return on_empty
    else:
        return text.lower() in {"true", "on", "1", "yes", "y"}


def perftm(buffer_size: int = 1):
    buffer = deque()
    cnt = 0

    def decorator(func):
        def timed(*args, **kwargs):
            nonlocal cnt
            t1 = perf_counter()
            result = func(*args, **kwargs)
            t2 = perf_counter()
            buffer.append(t2 - t1)
            cnt += 1
            if cnt >= buffer_size:
                exe_time = sum(buffer) / cnt
                log.debug(
                    f"{func.__name__} took avg {(exe_time)*1000:0.3f}ms over {cnt} calls",
                    stacklevel=2,
                )
                cnt = 0
                buffer.clear()
            return result

        return timed

    return decorator


hms_pattern = re.compile(r"^(?:(\d+):)(?:(\d+):)(\d+)$")
ms_pattern = re.compile(r"^(?:(\d+):)(\d+)$")
m_pattern = re.compile(r"^(\d+)$")


def parse_to_seconds(text: str) -> int:
    if ms_pattern.match(text):
        minutes, seconds = text.split(":")
        total_seconds = int(minutes) * 60 + int(seconds)
    elif hms_pattern.match(text):
        hours, minutes, seconds = text.split(":")
        total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    elif m_pattern.match(text):
        total_seconds = int(text) * 60
    else:
        raise ValueError("Invalid time format. Please use HH:MM:SS, MM:SS, or MM")
    return total_seconds


def clear_layout(layout):
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if item.widget() is not None:
            widget_to_del = item.widget()
            widget_to_del.setParent(None)
            layout.removeWidget(widget_to_del)
        else:
            layout_to_del = layout.itemAt(i)
            clear_layout(layout_to_del)
