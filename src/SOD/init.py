import os
import logging
from utils import fcc_queue, LogLvl
from cfg import config
from SOD.cli import CLI

log = logging.getLogger("SOD")


class SODspawn:

    def __init__(self, stream_out):
        self.sout = stream_out
        self.sout.editable_output = ""
        self.cli = CLI(output=self.sout)
        self.sout.console_prompt = self.cli.prompt.PHRASE
        self.cli.send_output(self.sout.console_prompt)

    def post(self, msg):
        if msg != self.sout.console_prompt:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.sout.console_log.append(msg)

    def execute_command(
        self, parsed_input: list, followup_prompt: bool = True
    ):
        if parsed_input[0] == "cls":
            self.cli.reset_state()
            self.cli.init_set_languages()
            self.cli.cls()
            self.cli.set_output_prompt(self.cli.prompt.PHRASE)
        else:
            self.run(parsed_input)
        self.cli.send_output(self.sout.console_prompt + self.sout.editable_output)
        self.sout.editable_output = ""

    def run(self, cmd: list):
        if (
            cmd == [""]
            and not self.cli.state.MODIFY_RES_EDIT_MODE
            and not self.cli.state.QUEUE_SELECTION_MODE
        ):
            # exit from modes
            if (
                self.cli.state.SELECT_TRANSLATIONS_MODE
                or self.cli.state.MODIFY_RES_EDIT_MODE
                or self.cli.state.MANUAL_MODE
            ):
                self.cli.reset_state()
                self.cli.init_set_languages()
                self.cli.cls(self.cli.msg.SAVE_ABORTED)
                self.sout.console_prompt = self.cli.prompt.PHRASE
            elif self.cli.state.QUEUE_MODE:
                self.cli.setup_queue_unpacking()
            else:  # Exit SOD - not available in dedicated tab
                self.cli.init_set_languages()
                self.cli.cls()
        else:
            self.manage_modes(cmd)

    def refresh_db(self):
        if (
            os.path.getmtime(self.cli.fh.path) - config["SOD"]["debounce"]
            > self.cli.fh.last_write_time
        ):
            self.cli.refresh_file_handler()
            self.cli.cls(self.cli.msg.DB_REFRESH, keep_content=True, keep_cmd=True)
            fcc_queue.put_notification("Refreshed SOD database", lvl=LogLvl.info)

    def manage_modes(self, cmd: list):
        if cmd[0] == "cls":
            self.cli.init_set_languages()
            self.cli.cls()
        elif (
            self.cli.state.SELECT_TRANSLATIONS_MODE
            or self.cli.state.RES_EDIT_SELECTION_MODE
            or self.cli.state.MODIFY_RES_EDIT_MODE
        ):
            self.cli.select_translations(cmd)
        elif self.cli.state.MANUAL_MODE:
            self.cli.insert_manual(cmd)
        elif self.cli.state.QUEUE_MODE:
            self.cli.manage_queue(cmd)
        elif self.cli.state.QUEUE_SELECTION_MODE:
            self.cli.unpack_translations_from_queue(cmd)
        else:
            self.cli.execute_command(cmd)

    def can_do_lookup(self) -> bool:
        """Check if current mode allows for executing Lookup"""
        return not (self.cli.state.QUEUE_MODE or self.cli.state.QUEUE_SELECTION_MODE)

    def is_state_clear(self) -> bool:
        """Verify if the current state equals the initial"""
        return not (
            self.cli.state.SELECT_TRANSLATIONS_MODE
            or self.cli.state.RES_EDIT_SELECTION_MODE
            or self.cli.state.MODIFY_RES_EDIT_MODE
            or self.cli.state.MANUAL_MODE
            or self.cli.state.QUEUE_MODE
            or self.cli.state.QUEUE_SELECTION_MODE
        )
