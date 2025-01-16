from cfg import config
from CMG.cli import CLI


class CMGSpawn:

    def __init__(self, stream_out):
        self.config = config
        self.sout = stream_out
        self.cli = CLI(sout=self.sout)
        self.state = None
        self.command = None
        self._adapt()

    def _adapt(self):
        self.CMD_HISTORY: list = self.sout.mw.CMDS_LOG.copy()
        self.sout.mw.CMDS_LOG = [""]
        self.prev_window_title = self.sout.mw.side_window_titles["fcc"]
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self._patch_post
        self.sout.execute_command = self._patch_execute_command
        self.sout.mw.side_window_titles["fcc"] = "Cards Manager"
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles["fcc"])

    def _patch_post(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.CONSOLE_LOG.append(msg)

    def _patch_execute_command(self, parsed_input: list, followup_prompt: bool = True):
        if parsed_input[0] == "cls":
            pass
        else:
            self.command(parsed_input)

    def _remove_adapter(self, fup: bool = True):
        self.cli.state = None
        self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
        self.sout.mw.setWindowTitle(self.prev_window_title)
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles["fcc"] = self.prev_window_title
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.console.setText("\n".join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY
        if fup:
            self.sout.mw.CONSOLE_LOG.append(self.sout.mw.CONSOLE_PROMPT)
            self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)

    def exit(self, msg: str = None):
        if msg:
            self.sout.mw.CONSOLE_LOG.append(msg)
        self._remove_adapter(bool(msg))
        del self

    def reverse_current_card(self, parsed_cmd: list):
        """Changes the current card's sides and updates source file"""
        self.cli.reverse_current_card(parsed_cmd)
        self.exit()

    def modify_current_card(self, parsed_cmd: list):
        """Interactively modify text in current card. Changes both dataset and the source file"""
        if self.state is None:
            self.command = self.modify_current_card
            self.state = "mcc"
        try:
            msg = self.cli.modify_card(parsed_cmd)
            if self.cli.state == "mcc_exit":
                self.exit(msg)
        except KeyboardInterrupt:
            self.exit("Aborted")

    def add_card(self, parsed_cmd: list):
        """Add a card to the current dataset"""
        if self.state is None:
            if not self.sout.mw.active_file.tmp:
                self.sout.post_fcc("Can only add cards to temporary files!")
                return
            self.command = self.add_card
            self.state = "add"
        try:
            msg = self.cli.add_card(parsed_cmd)
            if self.cli.state == "add_exit":
                self.exit(msg)
        except KeyboardInterrupt:
            self.exit("Aborted")
