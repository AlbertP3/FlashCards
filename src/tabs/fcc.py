from fcc import FCC
from utils import fcc_queue
from tabs.base import BaseConsole


class FccTab(BaseConsole):

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.mw.tab_names["fcc"] = "Console"
        self.build()
        self.fcc = FCC(self.mw, sout=self.console)
        self.mw.add_shortcut("fcc", self.open, "main")
        self.mw.add_shortcut("run_command", self.run_cmd, "fcc")
        self.mw.add_tab(self._tab, "fcc")

    def open(self):
        self.mw.switch_tab("fcc")
        self.__load_content()
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.console.setFocus()
        self.move_cursor_to_end()

    def __load_content(self):
        if self.console_log:
            self.console_log[:-1] = [
                i for i in self.console_log[:-1] if i != self.console_prompt
            ]
            if self.console_log[-1].startswith(self.console_prompt):
                self.console_log[-1] = self.console_prompt
                self.tmp_cmd = self.console.toPlainText().split("\n")[-1][
                    len(self.console_prompt) :
                ]
            else:
                self.console_log.append(self.console_prompt)
        else:
            self.console_log = [self.console_prompt]
        # Dump fcc_queue while preserving the prompt content
        cmd = self.console_log.pop()
        self.console.setText("\n".join(self.console_log))
        for msg in fcc_queue.dump_logs():
            self.fcc.post_fcc(
                f"[{msg.timestamp.strftime('%H:%M:%S')}] {msg.message}"
            )
        self.console.append(cmd + self.tmp_cmd)
        self.console_log.append(cmd)

    def run_cmd(self):
        cmd = self.console.toPlainText().split("\n")[-1][len(self.console_prompt) :]
        self.add_cmd_to_log(cmd)
        self.fcc.execute_command(cmd.split(" "))
        self.move_cursor_to_end()
