import pandas as pd
from utils import *
from cfg import config
from CMG.file_handler import FileHandler


class CLI:

    def __init__(self, sout):
        self.config = config
        self.sout = sout
        self.state = None

    def cls(self, *args, **kwargs):
        self.sout.console.setText("")
        self.sout.mw.CONSOLE_LOG = []

    def send_output(self, text: str):
        self.sout.console.append(text)
        self.sout.mw.CONSOLE_LOG.append(text)

    def set_output_prompt(self, t: str):
        self.sout.mw.CONSOLE_PROMPT = t

    def get_card_prompt(self, side: int):
        prefix = "First" if side == 0 else "Second"
        return f"{prefix} side: "

    def reverse_current_card(self, parsed_cmd: list):
        side = self.sout.mw.side
        ci = self.sout.mw.current_index
        path = self.sout.mw.active_file.filepath
        (
            self.sout.mw.active_file.data.iloc[ci, side],
            self.sout.mw.active_file.data.iloc[ci, 1 - side],
        ) = (
            self.sout.mw.active_file.data.iloc[ci, 1 - side],
            self.sout.mw.active_file.data.iloc[ci, side],
        )
        msg = "Reversed current card"
        if not self.sout.mw.active_file.tmp:
            i = FileHandler.unshuffle_index(
                ci,
                self.config["pd_random_seed"],
                self.sout.mw.active_file.data.shape[0],
            )
            if any(path.endswith(ext) for ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}):
                s_name = parsed_cmd[1] if len(parsed_cmd) >= 2 else None
                fh = FileHandler(path=path, sheet_name=s_name)
                s, m = fh.reverse_card(
                    i, self.sout.mw.active_file.data.iloc[ci, side], side
                )
                msg += f" and updated the source file [{i+2}]" if s else "\n" + m
            elif path.endswith(".csv"):
                FileHandler.unshuffle_dataframe(
                    self.sout.mw.active_file.data, seed=self.config["pd_random_seed"]
                ).to_csv(path, index=False)
                msg += f" and updated the source file [{i+3}]"
            else:
                msg = "Aborted - invalid filetype"
        self.send_output(msg)

    def modify_card(self, parsed_cmd: list):
        if self.state is None:
            self.mcc_sheet_name = parsed_cmd[1] if len(parsed_cmd) >= 2 else None
            self.mod_card = [None, None]
            self.print_orig_card(side=0)
            self.state = "mcc_first"
        elif self.state == "mcc_first":
            self.set_mod_card_from_console(side=0)
            self.print_orig_card(side=1)
            self.state = "mcc_second"
        elif self.state == "mcc_second":
            self.set_mod_card_from_console(side=1)
            msg = self.mcc_apply_changes(parsed_cmd)
            self.state = "mcc_exit"
            return msg

    def set_mod_card_from_console(self, side: int):
        c = self.sout.console.toPlainText().split("\n")
        new_text = c[-1][len(self.get_card_prompt(side)) :].strip()
        if not new_text:
            raise KeyboardInterrupt
        else:
            self.mod_card[side] = new_text

    def print_orig_card(self, side: int):
        text = self.sout.mw.active_file.data.iloc[self.sout.mw.current_index, side]
        new_prompt = self.get_card_prompt(side)
        self.set_output_prompt(new_prompt)
        self.send_output(f"{new_prompt} {text}")

    def mcc_apply_changes(self, parsed_cmd: list) -> str:
        ci = self.sout.mw.current_index
        old_card = self.sout.mw.active_file.data.iloc[ci, :].values.tolist()
        if old_card == self.mod_card:
            return "Aborted - no changes to commit"
        self.sout.mw.active_file.data.iloc[ci, :] = self.mod_card
        self.sout.mw.display_text(
            self.sout.mw.active_file.data.iloc[ci, self.sout.mw.side]
        )
        path = self.sout.mw.active_file.filepath
        msg = "Modified current card"
        if not self.sout.mw.active_file.tmp:
            i = FileHandler.unshuffle_index(
                ci,
                self.config["pd_random_seed"],
                self.sout.mw.active_file.data.shape[0],
            )
            if any(path.endswith(ext) for ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}):
                fh = FileHandler(path=path, sheet_name=self.mcc_sheet_name)
                s, m = fh.modify_card(i, self.mod_card, old_card)
                msg += f" and updated the source file [{i+2}]" if s else "\n" + m
            elif path.endswith(".csv"):
                FileHandler.unshuffle_dataframe(
                    self.sout.mw.active_file.data,
                    seed=self.config["pd_random_seed"],
                ).to_csv(path, index=False)
                msg += f" and updated the source file [{i+1}]"
            else:
                msg = "Aborted - invalid filetype"
        return msg

    def add_card(self, parsed_cmd: list):
        if self.state is None:
            self.new_card = [None, None]
            p = "Phrase: "
            self.set_output_prompt(p)
            self.send_output(p)
            self.state = "add_phrase"
        elif self.state == "add_phrase":
            self.new_card[0] = self.sout.mw.get_input()
            if not self.new_card[0]:
                self.state = "add_exit"
                return "Aborted"
            p = "Transl: "
            self.set_output_prompt(p)
            self.send_output(p)
            self.state = "add_transl"
        elif self.state == "add_transl":
            self.new_card[1] = self.sout.mw.get_input()
            self.state = "add_exit"
            msg = self.apply_add_card()
            return msg

    def apply_add_card(self):
        if "" in self.new_card:
            return "Aborted"
        if self.config["card_default_side"] == 1:
            self.new_card.reverse()
        self.sout.mw.active_file.data = pd.concat(
            [
                self.sout.mw.active_file.data,
                pd.DataFrame(
                    [self.new_card], columns=self.sout.mw.active_file.data.columns
                ),
            ],
            ignore_index=True,
            sort=False,
        )
        self.sout.mw.total_words = self.sout.mw.active_file.data.shape[0]
        self.sout.mw.update_words_button()
        return "Added a new card"
