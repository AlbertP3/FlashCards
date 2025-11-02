import json
import logging
import numpy as np
from typing import Optional, Any, Union
from pandas import Timestamp
from data_types import adlt


class JsonEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, np.int_):
            return int(o)
        elif isinstance(o, np.float_):
            return float(o)
        elif isinstance(o, Timestamp):
            return o.strftime(r"%Y-%m-%dT%H:%M:%S")
        else:
            return json.JSONEncoder.default(self, o)


class JSONLinesFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "ts": self.formatTime(record),
            "path": record.path,
            "row": record.row,
            "col": record.col,
            "op": record.op,
            "status": record.status,
            "author": record.author,
            "data": record.data,
        }
        return json.dumps(log_record, ensure_ascii=False, cls=JsonEncoder)


__audit_log = logging.getLogger("AUD")
__handler = logging.FileHandler("./audit.jsonl")
__handler.setFormatter(JSONLinesFormatter())
__audit_log.addHandler(__handler)


def audit_log(
    op: str,
    filepath: str,
    author: str,
    row: Union[int, str],
    col: str = ":",
    data: Any = {},
    status: str = adlt.stat.saved,
    stacklevel: Optional[int] = 2,
):
    __audit_log.info(
        f"{op} {data} {status} TO {filepath} AT [{row},{col}]",
        stacklevel=stacklevel,
        extra={
            "op": op,
            "row": row,
            "col": str(col),
            "status": status,
            "path": filepath,
            "author": author,
            "data": data,
        },
    )


def audit_log_rename(
    old_filepath: str, new_filepath: str, old_signature: str, new_signature: str
):
    records = []
    with open("audit.jsonl", "r", encoding="utf-8") as f:
        for r in f:
            r = json.loads(r)
            try:
                if r["path"] == old_filepath:
                    r["path"] = new_filepath
                    try:
                        if r["data"]["SIGNATURE"] == old_signature:
                            r["data"]["SIGNATURE"] = new_signature
                    except (KeyError, AttributeError, TypeError):
                        pass
            except KeyError:
                pass
            records.append(json.dumps(r, ensure_ascii=False))

    with open("audit.jsonl", "w", encoding="utf-8") as f:
        f.write("\n".join(records) + "\n")


def audit_log_prune():
    records = []
    rcnt = 0
    with open("audit.jsonl", "r") as f:
        for r in f:
            rcnt += 1
            try:
                _r: dict = json.loads(r)
                if _r["status"] == adlt.stat.active_only:
                    continue
                elif _r.get("path"):
                    records.append(r)
            except Exception:
                pass
    with open("audit.jsonl", "w") as f:
        f.writelines(records)

    return rcnt, len(records)
