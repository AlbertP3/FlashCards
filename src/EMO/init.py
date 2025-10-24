import logging
from int import fcc_queue
from utils import translate
from cfg import config
from EMO.cli import CLI, Steps
from DBAC import db_conn
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI


log = logging.getLogger("EMO")


class EMOSpawn:
    # EFC Model Optimizer

    def __init__(self, mw: "MainWindowGUI"):
        self.mw = mw
        self.mw.setWindowTitle("EFC Model Optimizer")
        self.cli = CLI(fcc=self.mw.fcc)
        self.adapt()
        self.init_emo()

    def init_emo(self):
        try:
            self.cli.set_emo_lngs(config["EMO"]["languages"])
            self.cli.set_emo_approach(config["EMO"]["approach"])
            self.cli.run_emo()
            self.cli.show_model_stats()
            self.cli.send_output(self.mw.fcc.console_prompt)
        except Exception as e:
            self.remove_adapter()
            self.mw.notify_on_error(e.__traceback__, e)

    def adapt(self):
        self.HISTORY: list = self.mw.fcc.console_log.copy()
        self.CMD_HISTORY: list = self.mw.fcc.cmd_log.copy()
        self.mw.fcc.cmd_log = [""]
        self.orig_post_method = self.mw.fcc.fcc.post_fcc
        self.orig_execute_method = self.mw.fcc.fcc.execute_command
        self.mw.fcc.fcc.post_fcc = self.monkey_patch_post
        self.mw.fcc.fcc.execute_command = self.monkey_patch_execute_command
        self.mw.fcc.console.setText("")

    def monkey_patch_post(self, msg):
        if msg != self.mw.fcc.console_prompt:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY += "\n" + msg

    def monkey_patch_execute_command(
        self, parsed_input: list, followup_prompt: bool = True
    ):
        if parsed_input[0] == "cls":
            self.cli.cls()
        else:
            self.run(parsed_input)
        self.mw.fcc.console.append(self.mw.fcc.console_prompt)

    def remove_adapter(self):
        self.mw.fcc.cls()
        self.mw.fcc.fcc.post_fcc = self.orig_post_method
        self.mw.setWindowTitle(self.mw.tab_map["fcc"]["title"])
        self.mw.fcc.fcc.execute_command = self.orig_execute_method
        self.mw.fcc.console_prompt = config["theme"]["default_ps1"]
        self.mw.fcc.console_log = self.HISTORY
        self.mw.fcc.console.setText("\n".join(self.mw.fcc.console_log))
        self.mw.fcc.console_log.append(self.mw.fcc.console_prompt)
        self.mw.fcc.cmd_log = self.CMD_HISTORY
        db_conn.refresh()
        for msg in fcc_queue.dump_logs():
            self.mw.fcc.fcc.post_fcc(
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
                if parsed_cmd and translate(parsed_cmd[0], on_empty=True):
                    fcc_queue.put_log("Model Selection cancelled")
                    self.remove_adapter()
                else:
                    self.cli.show_model_stats()
            # Immediately handle 'done' actions after status change
            if self.cli.step == Steps.done:
                if self.cli.accepted:
                    self.mw.efc.load_pickled_model()
                    self.mw.efc._efc_last_calc_time = 0
                    self.remove_adapter()
                else:
                    self.cli.prepare_exit()
        except Exception as e:
            self.remove_adapter()
            self.mw.notify_on_error(e.__traceback__, e)
