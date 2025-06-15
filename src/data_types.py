import re
from dataclasses import dataclass


@dataclass
class HIDE_TIPS_POLICIES:
    always = "always"
    never = "never"
    reg_rev = "regular-rev"
    new_card = "new-card"
    foreign_side = "foreign-side"

    @classmethod
    def get_states(cls) -> set:
        return {
            cls.reg_rev,
        }

    @classmethod
    def get_flux(cls) -> set:
        return {cls.new_card, cls.foreign_side}

    @classmethod
    def get_common(cls) -> set:
        return {cls.always, cls.never, cls.new_card, cls.foreign_side}


# Define the regex pattern for languages that do not use spaces
non_space_lng_re = re.compile(
    r"(?<=({0}))\s+(?=({0}))".format(
        r"[\u4E00-\u9FFF]"  # Chinese characters
        r"|[\u3040-\u309F]"  # Japanese Hiragana
        r"|[\u30A0-\u30FF]"  # Japanese Katakana
        r"|[\uAC00-\uD7AF]"  # Korean Hangul Syllables
        r"|[\u0E00-\u0E7F]"  # Thai characters
        r"|[\u0E80-\u0EFF]"  # Lao characters
        r"|[\u1000-\u109F]"  # Burmese characters
    ),
    flags=re.IGNORECASE,
)


@dataclass
class CreateFileDialogData:
    filename: str
    lng: str
    tgt_lng_id: str
    src_lng_id: str

sfe_hint_formats = {
    " ()": r"(?<=\\()[^),]+(?=[),])",
    " <>": r"(?<=\\<)[^),]+(?=[>,])",
    " []": r"(?<=\\[)[^),]+(?=[],])",
    " {}": r"(?<=\\{)[^),]+(?=[},])",
}

_T = {
    "kbsc": {
        "mod": "Mod Key",
        "next": "Next",
        "prev": "Prev",
        "negative": "Negative",
        "reverse": "Reverse",
        "del_cur_card": "Delete card",
        "load_again": "Load Again",
        "tracker": "Tracker",
        "mcr": "Modify card result",
        "config": "Settings",
        "fcc": "Console",
        "efc": "EFC",
        "next_efc": "Next EFC",
        "load": "Load",
        "mistakes": "Mistakes",
        "stats": "Statistics",
        "save": "Save",
        "sod": "Dictionary (CLI)",
        "hint": "Show hint",
        "last_seen": "Go to last seen",
        "logs": "Logs",
        "sfe": "Source File Editor",
        "sfe_search": "Source File Editor: search",
        "sfe_add": "Source File Editor: add card",
        "sfe_save": "Source File Editor: save",
    },
}


def translate(group: str, key: str) -> str:
    try:
        return _T[group][key]
    except KeyError:
        return key
