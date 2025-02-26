import json
from collections import UserDict
import logging
from PyQt5.QtGui import QFont

log = logging.getLogger("CFG")


class Config(UserDict):
    def __init__(self):
        self.CFG_PATH = "./src/res/config.json"
        self.DEF_CFG_PATH = "./src/res/config-default.json"
        self.THEMES_PATH = "./src/res/themes"
        self.CACHE_PATH = "./src/res/cache.json"
        self.stylesheet = ""
        self.mpl = {
            "font_color": "#ebdbb2",
            "stat_bar_color": "#3c3836",
            "stat_background_color": "#282828",
            "stat_chart_background_color": "#1d2021",
            "stat_chart_text_color": "#fbf1c7",
            "chart_secondary_color": " #979dac",
            "chart_edge_color": "#000000",
            "chart_line_color": "#a0a0a0",
        }

    def load(self):
        self.load_data()
        self.load_cache()
        self.load_theme()
        self.load_qfonts()
        self.load_theme_mpl()

    def reload(self):
        self.data.update(json.load(open(self.CFG_PATH, "r")))

    def save(self):
        json.dump(self.cache, open(self.CACHE_PATH, "w"), indent=4, ensure_ascii=False)
        json.dump(self.data, open(self.CFG_PATH, "w"), indent=4, ensure_ascii=False)
        log.debug("Saved Config and Cache")

    def load_data(self):
        try:
            self.data = json.load(open(self.CFG_PATH, "r"))
        except FileNotFoundError:
            self.data = json.load(open(self.DEF_CFG_PATH, "r"))

    def load_cache(self):
        try:
            self.cache: dict = json.load(open(self.CACHE_PATH, "r"))
        except FileNotFoundError:
            self.cache = {"snapshot": {"file": None, "session": None}, "notes": ""}

    def load_theme(self):
        try:
            with open(f"{self.THEMES_PATH}/{self.data['theme']['name']}.css", "r") as f:
                self.stylesheet = f.read()
        except FileNotFoundError:
            log.error(f"Theme {self.data['theme']['name']}.css not found!")

    def load_theme_mpl(self):
        try:
            lbound = self.stylesheet.find("#mpl")
            if lbound == -1:
                raise KeyError("Matplotlib style is missing. Applied default")
            ubound = self.stylesheet.find("}", lbound)
            spc = self.stylesheet[lbound:ubound].split("\n")[1:-1]
            props = {}
            for prop in spc:
                key, value = prop.split(":")
                key = key.strip().lstrip("-")
                props[key] = value.strip().rstrip(";")
            self.mpl = props
        except Exception as e:
            log.error(e, exc_info=True)

    def load_qfonts(self):
        self.qfont_textbox = QFont(
            self.data["theme"]["font"],
            self.data["theme"]["font_textbox_size"],
        )
        self.qfont_button = QFont(
            self.data["theme"]["font"],
            self.data["theme"]["font_button_size"],
        )
        self.qfont_console = QFont(
            self.data["theme"]["console_font"],
            self.data["theme"]["console_font_size"],
        )
        self.qfont_stats = QFont(
            self.data["theme"]["font"],
            self.data["theme"]["font_stats_size"],
        )
        self.qfont_logs = QFont(
            self.data["theme"]["console_font"],
            8,
        )
        self.qfont_chart = QFont(
            self.data["theme"]["font"],
            self.data["theme"]["font_stats_size"],
        )
        self.qfont_stopwatch = QFont(self.data["theme"]["font"], 50)


def __validate(cfg: Config) -> tuple[bool, set]:
    errs = set()
    int_gt_0 = {
        "interval_days": cfg["mst"]["interval_days"],
        "part_size": cfg["mst"]["part_size"],
        "part_cnt": cfg["mst"]["part_cnt"],
        "efc.threshold": cfg["efc"]["threshold"],
        "efc.cache_expiry_hours": cfg["efc"]["cache_expiry_hours"],
        "cache_history_size": cfg["cache_history_size"],
        "timeout_ms": cfg["popups"]["timeout_ms"],
        "show_animation_ms": cfg["popups"]["show_animation_ms"],
        "hide_animation_ms": cfg["popups"]["hide_animation_ms"],
        "active_interval_ms": cfg["popups"]["active_interval_ms"],
        "idle_interval_ms": cfg["popups"]["idle_interval_ms"],
        "font_textbox_size": cfg["theme"]["font_textbox_size"],
        "console_font_size": cfg["theme"]["console_font_size"],
        "font_button_size": cfg["theme"]["font_button_size"],
        "prelim_avg": cfg["tracker"]["duo"]["prelim_avg"],
    }
    numeric_gt_0 = {}
    int_gte_0 = {
        "init_revs_cnt": cfg["init_revs_cnt"],
        "min_eph_cards": cfg["min_eph_cards"],
        "spacing": cfg["theme"]["spacing"],
    }
    numeric_gte_0 = {
        "init_revs_inth": cfg["init_revs_inth"],
    }
    numeric_any = {
        "days_to_new_rev": cfg["days_to_new_rev"],
        "pace_card_interval": cfg["pace_card_interval"],
    }
    numeric_gt0_lte_1 = {
        "unreviewed_mistakes_percent": cfg["popups"]["triggers"][
            "unreviewed_mistakes_percent"
        ],
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
    for k, v in numeric_gt0_lte_1.items():
        try:
            if not 0 < v <= 1:
                errs.add(f"'{k}' must be int (0,1> but got {v}")
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
