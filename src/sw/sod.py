from sw.base import BaseConsole
from SOD.init import SODspawn


class SodTab(BaseConsole):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.build()
        self.mw.tab_names["sod"] = "Dictionary"
        self.sod = SODspawn(stream_out=self)
        self.mw.add_shortcut("sod", self.open, "main")
        self.mw.add_shortcut("run_command", self.run_cmd, "sod")
        self.mw.add_tab(self._tab, "sod")

    def open(self):
        self.mw.switch_tab("sod")
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
