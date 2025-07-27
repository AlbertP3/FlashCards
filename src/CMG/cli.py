import pandas as pd
from utils import *
from cfg import config
from CMG.file_handler import FileHandler


class CLI:

    def __init__(self, mw):
        self.mw = mw
        self.state = None

    def cls(self, *args, **kwargs):
        self.mw.fcc.console.setText("")
        self.mw.fcc.console_log = []

    def send_output(self, text: str):
        self.mw.fcc.console.append(text)
        self.mw.fcc.console_log.extend(text.split("\n"))

    def set_output_prompt(self, t: str):
        self.mw.fcc.console_prompt = t

    def get_card_prompt(self, side: int):
        prefix = "Original: " if side == 0 else "Translation: "
        return prefix

    def reverse_current_card(self, parsed_cmd: list):
        side = self.mw.side
        ci = self.mw.current_index
        path = self.mw.active_file.filepath
        (
            self.mw.active_file.data.iloc[ci, side],
            self.mw.active_file.data.iloc[ci, 1 - side],
        ) = (
            self.mw.active_file.data.iloc[ci, 1 - side],
            self.mw.active_file.data.iloc[ci, side],
        )
        msg = "Reversed current card"
        if not self.mw.active_file.tmp:
            i = FileHandler.unshuffle_index(
                ci,
                config["pd_random_seed"],
                self.mw.active_file.data.shape[0],
            )
            if any(path.endswith(ext) for ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}):
                s_name = parsed_cmd[1] if len(parsed_cmd) >= 2 else None
                fh = FileHandler(path=path, sheet_name=s_name)
                s, m = fh.reverse_card(i, self.mw.active_file.data.iloc[ci, side], side)
                msg += f" and updated the source file [{i+2}]" if s else "\n" + m
            elif path.endswith(".csv"):
                FileHandler.unshuffle_dataframe(
                    self.mw.active_file.data, seed=config["pd_random_seed"]
                ).to_csv(
                    path,
                    index=False,
                    header=True,
                    columns=self.mw.active_file.headers,
                    encoding="utf-8",
                )
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
        c = self.mw.fcc.console.toPlainText().split("\n")
        new_text = c[-1][len(self.get_card_prompt(side)) :].strip()
        if not new_text:
            raise KeyboardInterrupt
        else:
            self.mod_card[side] = new_text
            self.mw.fcc.console_log[-1] = c[-1]

    def print_orig_card(self, side: int):
        text = self.mw.active_file.data.iloc[self.mw.current_index, side]
        new_prompt = self.get_card_prompt(side)
        self.set_output_prompt(new_prompt)
        self.send_output(f"{new_prompt}{text}")

    def mcc_apply_changes(self, parsed_cmd: list) -> str:
        ci = self.mw.current_index
        old_card = self.mw.active_file.data.iloc[ci, :2].values.tolist()
        if old_card == self.mod_card:
            return "Aborted - no changes to commit"
        self.mw.active_file.data.iloc[ci, :2] = self.mod_card
        self.mw.display_text(self.mw.active_file.data.iloc[ci, self.mw.side])
        path = self.mw.active_file.filepath
        msg = "Modified current card"
        if not self.mw.active_file.tmp:
            i = FileHandler.unshuffle_index(
                ci,
                config["pd_random_seed"],
                self.mw.active_file.data.shape[0],
            )
            if any(path.endswith(ext) for ext in {".xlsx", ".xlsm", ".xltx", ".xltm"}):
                fh = FileHandler(path=path, sheet_name=self.mcc_sheet_name)
                s, m = fh.modify_card(i, self.mod_card, old_card)
                msg += f" and updated the source file [{i+2}]" if s else "\n" + m
            elif path.endswith(".csv"):
                FileHandler.unshuffle_dataframe(
                    self.mw.active_file.data,
                    seed=config["pd_random_seed"],
                ).to_csv(
                    path,
                    index=False,
                    columns=self.mw.active_file.headers,
                    header=True,
                    encoding="utf-8",
                )
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
            self.new_card[0] = self.mw.fcc.get_input()
            if not self.new_card[0]:
                self.state = "add_exit"
                return "Aborted"
            p = "Transl: "
            self.set_output_prompt(p)
            self.send_output(p)
            self.state = "add_transl"
        elif self.state == "add_transl":
            self.new_card[1] = self.mw.fcc.get_input()
            self.state = "add_exit"
            msg = self.apply_add_card()
            return msg

    def apply_add_card(self):
        if "" in self.new_card:
            return "Aborted"
        if config["card_default_side"] == 1:
            self.new_card.reverse()
        new_idx = len(self.mw.active_file.data)
        self.mw.active_file.data.loc[new_idx] = [*self.new_card, new_idx]
        self.mw.total_words = self.mw.active_file.data.shape[0]
        self.mw.update_words_button()
        return "Added a new card"
