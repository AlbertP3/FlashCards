import json
import numpy as np
from collections import UserDict
import logging
from time import perf_counter
from PyQt5.QtGui import QFont

log = logging.getLogger("CFG")


class JsonEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, np.int_):
            return int(o)
        elif isinstance(o, np.float_):
            return float(o)
        else:
            return json.JSONEncoder.default(self, o)


class Config(UserDict):
    def __init__(self):
        self.session_start = perf_counter()
        self.CFG_PATH = "./src/res/config.json"
        self.DEF_CFG_PATH = "./src/res/config-default.json"
        self.THEMES_PATH = "./src/res/themes"
        self.CACHE_PATH = "./src/res/cache.json"

    def get_session_time_pp(self) -> str:
        """Miliseconds elapsed from session start"""
        return f"{1000*(perf_counter() - self.session_start):.0f}ms"

    def load(self):
        self.load_data()
        self.load_cache()
        self.load_theme()
        self.load_qfonts()
        self.load_tag_mpl()

    def reload(self):
        self.data.update(json.load(open(self.CFG_PATH, "r")))

    def save(self):
        json.dump(
            self.cache,
            open(self.CACHE_PATH, "w"),
            indent=4,
            ensure_ascii=False,
            cls=JsonEncoder,
        )
        json.dump(
            self.data,
            open(self.CFG_PATH, "w"),
            indent=4,
            ensure_ascii=False,
            cls=JsonEncoder,
        )
        log.debug("Saved Config and Cache")

    def load_data(self):
        try:
            self.data = json.load(open(self.CFG_PATH, "r"))
        except FileNotFoundError:
            log.warning("Configuration not found. Creating new...")
            self.data = json.load(open(self.DEF_CFG_PATH, "r"))

    def load_cache(self):
        try:
            self.cache: dict = json.load(open(self.CACHE_PATH, "r"))
        except FileNotFoundError:
            log.warning("Cache not found. Creating new...")
            self.__set_default_cache()
        except Exception as e:
            log.error("Failed to load cache", exc_info=True)
            self.__set_default_cache()

    def __set_default_cache(self):
        self.cache = {
            "snapshot": {"file": None, "session": None},
            "notes": "",
            "load_est": dict(),
        }

    def load_theme(self):
        try:
            with open(f"{self.THEMES_PATH}/{self.data['theme']['name']}.css", "r") as f:
                self.stylesheet = f.read()
        except FileNotFoundError:
            log.warning(f"Theme {self.data['theme']['name']}.css not found!")
            self.stylesheet = ""

    def load_tag_mpl(self):
        self.mpl = self._load_theme_tag(
            tag="#mpl",
            default={
                "font_color": "#ebdbb2",
                "stat_bar_color": "#3c3836",
                "stat_background_color": "#282828",
                "stat_chart_background_color": "#1d2021",
                "stat_chart_text_color": "#fbf1c7",
                "chart_secondary_color": "#979dac",
                "chart_edge_color": "#000000",
                "chart_line_color": "#a0a0a0",
            },
        )

    def _load_theme_tag(self, tag: str, default: dict) -> dict:
        try:
            lbound = self.stylesheet.find(tag)
            if lbound == -1:
                raise KeyError(f"'{tag}' tag is missing. Applied default")
            ubound = self.stylesheet.find("}", lbound)
            spc = self.stylesheet[lbound:ubound].split("\n")[1:-1]
            props = {}
            for prop in spc:
                key, value = prop.split(":")
                key = key.strip().lstrip("-")
                props[key] = value.strip().rstrip(";")
            return props
        except Exception as e:
            log.warning(e, stack_info=True)
            return default

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


config = Config()
config.load()
