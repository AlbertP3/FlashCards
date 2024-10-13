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
