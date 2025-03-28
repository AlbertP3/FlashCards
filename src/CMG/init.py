from cfg import config
from CMG.cli import CLI


class CMGSpawn:

    def __init__(self, mw):
        self.mw = mw
        self.cli = CLI(mw=self.mw)
        self.state = None
        self.command = None
        self._adapt()

    def _adapt(self):
        self.CMD_HISTORY: list = self.mw.fcc.cmd_log.copy()
        self.mw.fcc.cmd_log = [""]
        self.orig_post_method = self.mw.fcc.fcc.post_fcc
        self.orig_execute_method = self.mw.fcc.fcc.execute_command
        self.mw.fcc.fcc.post_fcc = self._patch_post
        self.mw.fcc.fcc.execute_command = self._patch_execute_command

    def _patch_post(self, msg):
        if msg != self.mw.fcc.console_prompt:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.mw.fcc.console_log.append(msg)

    def _patch_execute_command(self, parsed_input: list, followup_prompt: bool = True):
        if parsed_input[0] == "cls":
            pass
        else:
            self.command(parsed_input)

    def _remove_adapter(self, fup: bool = True):
        self.cli.state = None
        self.mw.fcc.console_prompt = config["theme"]["default_ps1"]
        self.mw.fcc.fcc.post_fcc = self.orig_post_method
        self.mw.fcc.fcc.execute_command = self.orig_execute_method
        self.mw.fcc.cmd_log = self.CMD_HISTORY
        self.mw.fcc.console.setText("\n".join(self.mw.fcc.console_log))
        if fup:
            self.mw.fcc.console_log.append(self.mw.fcc.console_prompt)
            self.mw.fcc.console.append(self.mw.fcc.console_prompt)

    def exit(self, msg: str = None, fup: bool = True):
        if msg:
            self.mw.fcc.console_log.append(msg)
        self._remove_adapter(fup)
        del self

    def reverse_current_card(self, parsed_cmd: list):
        """Changes the current card's sides and updates source file"""
        self.cli.reverse_current_card(parsed_cmd)
        self.exit(fup=False)

    def modify_current_card(self, parsed_cmd: list):
        """Interactively modify text in current card. Changes both dataset and the source file"""
        if self.state is None:
            self.command = self.modify_current_card
            self.state = "mcc"
        try:
            msg = self.cli.modify_card(parsed_cmd)
            if self.cli.state == "mcc_exit":
                self.exit(msg, fup=True)
        except KeyboardInterrupt:
            self.exit("Aborted", fup=True)

    def add_card(self, parsed_cmd: list):
        """Add a card to the current dataset"""
        if self.state is None:
            if not self.mw.active_file.tmp:
                self.exit("Can only add cards to temporary files!", fup=False)
                return
            self.command = self.add_card
            self.state = "add"
        try:
            msg = self.cli.add_card(parsed_cmd)
            if self.cli.state == "add_exit":
                self.exit(msg, fup=True)
        except KeyboardInterrupt:
            self.exit("Aborted", fup=True)
