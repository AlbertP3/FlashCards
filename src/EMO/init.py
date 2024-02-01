import logging
from utils import Config
from EMO.cli import CLI


log = logging.getLogger("EFC")


class emo_spawn:
    # EFC Model Enhancer

    def __init__(self, stream_out):
        self.config = Config()
        self.sout = stream_out
        self.sout.mw.side_window_titles["fcc"] = "EFC Model Optimizer"
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles["fcc"])
        self.cli = CLI(sout=self.sout)
        self.adapt()
        self.cli.step.configure_lngs.disp = True
        self.run([""])

    def adapt(self):
        self.HISTORY: list = self.sout.mw.CONSOLE_LOG.copy()
        self.CMD_HISTORY: list = self.sout.mw.CMDS_LOG.copy()
        self.sout.mw.CMDS_LOG = [""]
        self.prev_window_title = self.sout.mw.side_window_titles["fcc"]
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self.monkey_patch_post
        self.sout.execute_command = self.monkey_patch_execute_command
        self.sout.console.setText("")

    def monkey_patch_post(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY += "\n" + msg

    def monkey_patch_execute_command(
        self, parsed_input: list, followup_prompt: bool = True
    ):
        if parsed_input[0] == "cls":
            self.cli.cls()
        else:
            self.run(parsed_input)
        self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)

    def remove_adapter(self):
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles["fcc"] = self.prev_window_title
        self.sout.mw.setWindowTitle(self.prev_window_title)
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.CONSOLE_LOG = self.HISTORY
        self.sout.mw.console.setText("\n".join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CONSOLE_LOG.append(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY

    def _exit(self):
        self.sout.cls()
        self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
        self.remove_adapter()
        self.cli.step.done.disp = False
        if self.cli.err_msg:
            self.sout.post_fcc(self.cli.err_msg)
        del self

    def run(self, parsed_cmd: list):
        try:
            if self.cli.step.configure_lngs:
                self.cli.configure_emo_lngs(parsed_cmd)
            if self.cli.step.configure_approach:
                self.cli.configure_emo_approach(parsed_cmd)
            if self.cli.step.run_emo.disp:
                self.cli.run_emo(parsed_cmd)
            if self.cli.step.model_selection:
                self.cli.model_selection(parsed_cmd)
            if self.cli.step.examples:
                self.cli.show_examples(parsed_cmd)
            if self.cli.step.examples.accepted:
                self.sout.mw.load_pickled_model()
                self.cli.step.done.disp = True
            if self.cli.step.done:
                self._exit()
        except Exception as e:
            log.error(e, exc_info=True)
            self._exit()
