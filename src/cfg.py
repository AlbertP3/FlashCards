import json
from collections import UserDict
import logging

log = logging.getLogger(__name__)


class Config(UserDict):
    def __init__(self):
        self.CFG_PATH = "./src/res/config.json"
        self.DEF_CFG_PATH = "./src/res/config-default.json"
        self.CACHE_PATH = "./src/res/cache.json"
        self.default_off_values = {"off", "no", "none", ""}

    def load(self):
        try:
            self.data = json.load(open(self.CFG_PATH, "r"))
        except FileNotFoundError:
            self.data = json.load(open(self.DEF_CFG_PATH, "r"))
        try:
            self.cache: dict = json.load(open(self.CACHE_PATH, "r"))
        except FileNotFoundError:
            self.cache = {
                "snapshot": {"file": None, "session": None},
            }

    def reload(self):
        self.data.update(json.load(open(self.CFG_PATH, "r")))

    def save(self):
        json.dump(self.cache, open(self.CACHE_PATH, "w"), indent=4, ensure_ascii=False)
        json.dump(self.data, open(self.CFG_PATH, "w"), indent=4, ensure_ascii=False)
        log.debug("Saved Config and Cache")

    def translate(self, key, val_on=None, val_off=None, off_values: set = None):
        if self.data[key] in (off_values or self.default_off_values):
            return val_off
        else:
            return val_on or self.data[key]


def __validate(cfg: dict) -> tuple[bool, set]:
    errs = set()
    int_gt_0 = {
        "mistakes_review_interval_days": cfg["mistakes_review_interval_days"],
        "mistakes_buffer": cfg["mistakes_buffer"],
        "efc_threshold": cfg["efc_threshold"],
        "efc_cache_expiry_hours": cfg["efc_cache_expiry_hours"],
        "cache_history_size": cfg["cache_history_size"],
        "timespent_len": cfg["timespent_len"],
        "timeout_ms": cfg["popups"]["timeout_ms"],
        "show_animation_ms": cfg["popups"]["show_animation_ms"],
        "hide_animation_ms": cfg["popups"]["hide_animation_ms"],
        "check_interval_ms": cfg["popups"]["check_interval_ms"],
    }
    numeric_gt_0 = {}
    int_gte_0 = {
        "init_revs_cnt": cfg["init_revs_cnt"],
        "min_eph_cards": cfg["min_eph_cards"],
    }
    numeric_gte_0 = {
        "init_revs_inth": cfg["init_revs_inth"],
        "unreviewed_mistakes_percent": cfg["popups"]["triggers"][
            "unreviewed_mistakes_percent"
        ],
    }
    numeric_any = {
        "days_to_new_rev": cfg["days_to_new_rev"],
        "pace_card_interval": cfg["pace_card_interval"],
    }
    for k, v in int_gt_0.items():
        try:
            if v < 1:
                errs.add(f"'{k}' must be greater than 0 but got {v}")
            elif not isinstance(v, int):
                raise TypeError
        except TypeError:
            errs.add(f"'{k}' must be an integer but got '{type(v)}'")
    for k, v in numeric_gt_0.items():
        try:
            if v <= 0:
                errs.add(f"'{k}' must be greater than 0 but got {v}")
        except TypeError:
            errs.add(f"'{k}' must be a numeric but got '{type(v)}'")
    for k, v in int_gte_0.items():
        try:
            if v < 0:
                errs.add(f"'{k}' must be >= 0 but got {v}")
            elif not isinstance(v, int):
                raise TypeError
        except TypeError:
            errs.add(f"'{k}' must be an integer but got '{type(v)}'")
    for k, v in numeric_any.items():
        if not isinstance(v, (int, float, complex)):
            errs.add(f"'{k}' must be a numeric but got '{type(v)}'")
    for k, v in numeric_gte_0.items():
        try:
            if v < 0:
                errs.add(f"'{k}' must be >= 0 but got {v}")
            elif not isinstance(v, (int, float, complex)):
                raise TypeError
        except TypeError:
            errs.add(f"'{k}' must be an integer but got '{type(v)}'")

    if errs:
        return False, errs
    else:
        return True, set()


def validate(cfg: dict) -> tuple[bool, set]:
    try:
        return __validate(cfg)
    except Exception as e:
        return False, {f"{type(e).__name__}: {e}"}


config = Config()
config.load()
