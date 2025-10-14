import re
from collections import OrderedDict
from tracker.structs import StrRecordOrderedDict, Record


def merge_records_by_date(content: OrderedDict, dfmt: str) -> StrRecordOrderedDict:
    merged_records = OrderedDict()
    for d, record in content.items():
        k = d.strftime(dfmt)
        merged_records[k] = merged_records.get(k, Record()) + record
    return merged_records


def strftime(time_in_hours: float, default: str = " ", incl_minutes: bool = True) -> str:
    if time_in_hours == 0:
        return default
    elif incl_minutes:
        hours = int(time_in_hours)
        minutes = int(round((time_in_hours - hours) * 60, 2))
        return f"{hours}:{minutes:02d}"
    else:
        hours = int(round(time_in_hours))
        if hours == 0:
            return default
        else:
            return str(hours)


def safe_div(x, y, default=0) -> float:
    try:
        return x / y
    except ZeroDivisionError:
        return default


def get_chart(
    data: list[tuple],
    height: int = 15,
    min_: int = 0,
    hpad: int = 0.8,
    scaling: float = 1,
    num_fmt: str = ".0f",
    scale_fmt: str = "2.0f",
    incl_scale: bool = True,
    title: str = None,
    col_len: int = None,
) -> list[str]:
    out = list()
    stubs = set()
    height -= 2 if title else 1
    col_len = col_len or len(data[0][0])
    col_sep = " "
    try:
        scale = hpad * height / (max(i[1] for i in data) / scaling)
    except ZeroDivisionError:
        scale = 1
    cols = list()

    for s in data:
        cval = s[1] / scaling
        cheight = max(int(round(cval * scale, 0)), 1)
        if cval > 0:
            cols.append(
                [
                    *["│" + " " * (col_len - 2) + "│"] * cheight,
                    "┌" + "─" * (col_len - 2) + "┐",
                    f"{cval:^{col_len}{num_fmt}}",
                    *[" " * col_len] * (height - cheight - 2),
                ]
            )
        else:
            stubs.add(len(cols))
            cols.append([" " * col_len] * height)

    for row in range(height - 1, min_, -1):
        prefix = f"{row/scale:>{scale_fmt}} " if incl_scale else ""
        line = f"{prefix}│ " + col_sep.join(col[row] for col in cols)
        out.append(line)
        row -= 1

    offset = line.find("│")
    bottom_line = f"{' '*offset}└" + ("─┴" + "─" * (col_len - 2) + "┴") * len(cols)
    if stubs:
        b = list(bottom_line)
        for s in stubs:
            i = offset + s * (col_len + 1)
            b[i + 2] = "─"
            b[i + col_len + 1] = "─"
        bottom_line = "".join(b)
    out.append(bottom_line)
    out.append("  " + " " * offset + " ".join(f"{d[0]:^{col_len}}" for d in data))
    if title:
        out.insert(0, f" {title:^{len(out[-1])}}")
    return out
