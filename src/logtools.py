import json
import logging
import numpy as np
from typing import Optional, Literal, Any, Union
from pandas import Timestamp


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
    op: Literal["ADD", "UPDATE", "DELETE", "REVERSE", "MOVE", "RENAME", "MERGE"],
    data: Any,
    filepath: str,
    author: Literal["FCS", "SFE", "DBQ", "TRK"],
    row: Union[int, str],
    col: str = ":",
    status: Literal["SAVE", "STAGE", "ACTIVE_ONLY"] = "SAVE",
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
    with open("audit.jsonl", "r") as f:
        for r in f:
            r = json.loads(r)
            try:
                if r["path"] == old_filepath:
                    r["path"] = new_filepath
                    if r["data"].get("SIGNATURE") == old_signature:
                        r["data"]["SIGNATURE"] = new_signature
            except KeyError:
                pass
            records.append(json.dupms(r))

    with open("audit.jsonl", "w") as f:
        f.writelines(records)


def audit_log_prune():
    records = []
    rcnt = 0
    with open("audit.jsonl", "r") as f:
        for r in f:
            rcnt += 1
            try:
                if json.loads(r).get("path"):
                    records.append(r)
            except Exception:
                pass
    with open("audit.jsonl", "w") as f:
        f.writelines(records)

    return rcnt, len(records)
