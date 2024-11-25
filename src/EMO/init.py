import logging
from utils import fcc_queue
from cfg import config
from EMO.cli import CLI, Steps


log = logging.getLogger("EMO")


class EMOSpawn:
    # EFC Model Optimizer

    def __init__(self, stream_out):
        self.config = config
        self.sout = stream_out
        self.sout.mw.side_window_titles["fcc"] = "EFC Model Optimizer"
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles["fcc"])
        self.cli = CLI(sout=self.sout)
        self.adapt()
        self.init_emo()

    def init_emo(self):
        try:
            self.cli.set_emo_lngs(self.config["EMO"]["languages"])
            self.cli.set_emo_approach(self.config["EMO"]["approach"])
            self.cli.run_emo()
            self.cli.show_model_stats()
            self.cli.send_output(self.sout.mw.CONSOLE_PROMPT)
        except Exception as e:
            self.remove_adapter()
            self.sout.mw.notify_on_error(e.__traceback__, e)

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
        self.sout.cls()
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles["fcc"] = self.prev_window_title
        self.sout.mw.setWindowTitle(self.prev_window_title)
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
        self.sout.mw.CONSOLE_LOG = self.HISTORY
        self.sout.mw.console.setText("\n".join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CONSOLE_LOG.append(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY
        self.sout.mw.db.refresh()
        for msg in fcc_queue.dump():
            self.sout.mw.fcc_inst.post_fcc(
                f"[{msg.timestamp.strftime('%H:%M:%S')}] {msg.message}"
            )

    def run(self, parsed_cmd: list):
        try:
            if self.cli.step == Steps.model_display:
                self.cli.show_model_stats()
            elif self.cli.step == Steps.model_selection:
                self.cli.model_selection(parsed_cmd)
            elif self.cli.step == Steps.examples_display:
                self.cli.show_examples()
            elif self.cli.step == Steps.decide_model:
                self.cli.decide_model(parsed_cmd)
            elif self.cli.step == Steps.decide_exit:
                if parsed_cmd and parsed_cmd[0].lower() in {"yes", "y", "1", ""}:
                    fcc_queue.put("Model Selection cancelled")
                    self.remove_adapter()
                else:
                    self.cli.show_model_stats()
            # Immediately handle 'done' actions after status change
            if self.cli.step == Steps.done:
                if self.cli.accepted:
                    self.sout.mw.load_pickled_model()
                    self.sout.mw._efc_last_calc_time = 0
                    self.remove_adapter()
                else:
                    self.cli.prepare_exit()
        except Exception as e:
            self.remove_adapter()
            self.sout.mw.notify_on_error(e.__traceback__, e)
