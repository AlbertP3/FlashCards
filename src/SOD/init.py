from utils import Config
from SOD.cli import CLI



class sod_spawn:

    def __init__(self, stream_out):
        self.config = Config()
        self.sout = stream_out
        self.sout.editable_output = ''
        self.adapt()
        self.cli = CLI(output=self.sout)
        self.sout.mw.CONSOLE_PROMPT = self.cli.prompt.PHRASE
        self.cli.send_output(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.side_window_titles['fcc'] = 'Search Online Dictionaries'
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles['fcc'])

    def adapt(self):
        self.HISTORY:list = self.sout.mw.CONSOLE_LOG.copy()
        self.CMD_HISTORY:list = self.sout.mw.CMDS_LOG.copy()
        self.sout.mw.CMDS_LOG = [""]
        self.sout.mw.CONSOLE_LOG = []
        self.prev_window_title = self.sout.mw.side_window_titles['fcc']
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self.monkey_patch_post
        self.sout.execute_command = self.monkey_patch_execute_command
        self.sout.console.setText('')
    
    def monkey_patch_post(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY.append(msg)

    def monkey_patch_execute_command(self, parsed_input:list, followup_prompt:bool=True):
        if parsed_input[0] == 'cls':
            self.cli.reset_state()
            self.cli.cls()
            self.cli.set_output_prompt(self.cli.prompt.PHRASE)
        else:
            self.run(parsed_input)
        self.cli.send_output(self.sout.mw.CONSOLE_PROMPT + self.sout.editable_output)
        self.sout.editable_output = ''

    def remove_adapter(self):
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles['fcc'] = self.prev_window_title
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.CONSOLE_LOG = self.HISTORY
        self.sout.mw.console.setText('\n'.join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY

    def run(self, cmd:list):
        if cmd == [''] and not self.cli.state.MODIFY_RES_EDIT_MODE \
            and not self.cli.state.QUEUE_SELECTION_MODE:
            # exit from modes
            if self.cli.state.SELECT_TRANSLATIONS_MODE \
                or self.cli.state.MODIFY_RES_EDIT_MODE \
                or self.cli.state.MANUAL_MODE:
                self.cli.reset_state()
                self.cli.cls(self.cli.msg.SAVE_ABORTED)
                self.sout.mw.CONSOLE_PROMPT = self.cli.prompt.PHRASE
            elif self.cli.state.QUEUE_MODE:
                self.cli.setup_queue_unpacking()
            else: # Exit SOD
                self.sout.cls()
                self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
                self.cli.close_wb()
                self.sout.mw.setWindowTitle(self.prev_window_title)
                self.remove_adapter()
                del self
        else:
            self.manage_modes(cmd)


    def manage_modes(self, cmd:list):
        if cmd[0] == 'cls':
            self.cli.cls()
        elif self.cli.state.SELECT_TRANSLATIONS_MODE or self.cli.state.RES_EDIT_SELECTION_MODE \
                or self.cli.state.MODIFY_RES_EDIT_MODE:
            self.cli.select_translations(cmd)
        elif self.cli.state.MANUAL_MODE:
            self.cli.insert_manual(cmd)
        elif self.cli.state.QUEUE_MODE:
            self.cli.manage_queue(cmd)
        elif self.cli.state.QUEUE_SELECTION_MODE:
            self.cli.unpack_translations_from_queue(cmd)
        else:
            self.cli.execute_command(cmd)
