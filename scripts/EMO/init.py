from utils import Config
from EMO.cli import CLI



class emo_spawn:
    # EFC Model Enhancer

    def __init__(self, stream_out):
        self.config = Config()
        self.sout = stream_out
        self.cli = CLI(sout=self.sout)
        self.HISTORY:list = self.sout.mw.CONSOLE_LOG.copy()
        self.CMD_HISTORY:list = self.sout.mw.CMDS_LOG.copy()
        self.sout.mw.CMDS_LOG = ['']
        self.cli.cls()
        self.sout.mw.side_window_titles['fcc'] = 'EFC Model Optimizer'
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles['fcc'])
        self.adapt_to_fcc()
        self.cli.STEP_RUN_EMO = True
        self.run([' '])


    def adapt_to_fcc(self):
        self.prev_window_title = self.sout.mw.side_window_titles['fcc']
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self._patch_post_fcc
        self.sout.execute_command = self._patch_execute_command


    def _patch_post_fcc(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY+='\n'+msg


    def _patch_execute_command(self, parsed_input:list, followup_prompt:bool=True):
        if parsed_input[0] == 'cls':
            self.cli.cls()
        else:
            self.run(parsed_input)
        self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)


    def remove_adapter_fcc(self):
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles['fcc'] = self.prev_window_title
        self.sout.mw.setWindowTitle(self.prev_window_title)
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.CONSOLE_LOG = self.HISTORY
        self.sout.mw.console.setText('\n'.join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CONSOLE_LOG.append(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY


    def _exit(self):
        self.sout.cls()
        self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
        self.remove_adapter_fcc()
        del self


    def run(self, parsed_cmd:list):
        if self.cli.STEP_RUN_EMO:
            self.cli.run_emo(parsed_cmd)
        elif self.cli.STEP_MODEL_SELECTION:
            if parsed_cmd[0] == '': 
                self._exit()
            else:
                self.cli.model_selection(parsed_cmd)
        elif self.cli.STEP_APPROVE_CHANGES:
            self.cli.approve_changes(parsed_cmd)
            if not self.cli.STEP_MODEL_SELECTION:
                # meaning: changes were approved
                self._exit()
                self.sout.console.append('New EFC model was applied successfuly')
        else:
            self._exit()

