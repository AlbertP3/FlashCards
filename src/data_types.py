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
