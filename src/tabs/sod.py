from tabs.base import BaseConsole
from SOD.init import SODspawn
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI


class SodTab(BaseConsole):

    def __init__(self, mw: "MainWindowGUI"):
        super().__init__()
        self.id = "sod"
        self.mw = mw
        self.build()
        self.editable_output = ""
        self.sod = SODspawn(tab=self)
        self.mw.add_tab(self._tab, self.id, "Dictionary")

    def open(self):
        self.mw.switch_tab(self.id)
        if self.sod.is_state_clear():
            self.sod.cli.init_set_languages()
            self.sod.cli.cls(keep_cmd=True, keep_content=True)
        self.console.setFocus()

    def post(self, text=""):
        self.console.append(text)
        self.console_log.append(text)

    def run_cmd(self):
        cmd = self.console.toPlainText().split("\n")[-1][len(self.console_prompt) :]
        self.add_cmd_to_log(cmd)
        self.sod.execute_command(cmd.split(" "))
        self.move_cursor_to_end()

    def cls(self):
        self.sod.execute_command(["cls"])
