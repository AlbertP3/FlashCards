from utils import Config
from CMG.cli import CLI



class cmg_spawn:
    # Cards Manager

    def __init__(self, stream_out):
        self.config = Config()
        self.sout = stream_out
        self.cli = CLI(sout=self.sout)
        self.state = None
        

    def _adapt(self, command, state):
        self.HISTORY:list = self.sout.mw.CONSOLE_LOG.copy()
        self.CMD_HISTORY:list = self.sout.mw.CMDS_LOG.copy()
        self.sout.mw.CMDS_LOG = ['']
        self.prev_window_title = self.sout.mw.side_window_titles['fcc']
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self._patch_post
        self.sout.execute_command = command
        self.sout.mw.side_window_titles['fcc'] = 'Cards Manager'
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles['fcc'])
        self.cli.cls()
        self.state = state


    def _patch_post(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY+='\n'+msg


    def _patch_execute_command(self, parsed_input:list, followup_prompt:bool=True):
        if parsed_input[0] == 'cls':
            self.cli.cls()
        else:
            self.run(parsed_input)
        self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)


    def _remove_adapter(self):
        self.sout.mw.CONSOLE_PROMPT = self.sout.mw.DEFAULT_PS1
        self.sout.mw.setWindowTitle(self.prev_window_title)
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles['fcc'] = self.prev_window_title
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.CONSOLE_LOG = self.HISTORY
        self.sout.mw.console.setText('\n'.join(self.sout.mw.CONSOLE_LOG))
        self.sout.mw.CONSOLE_LOG.append(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY
        self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)


    def _exit(self, msg:str=None):
        if msg:
            self.HISTORY.append(msg)
        self._remove_adapter()
        del self


    def reverse_current_card(self, parsed_cmd:list):
        '''Changes the current cards sides and updates source file'''
        self.cli.reverse_current_card(parsed_cmd)
        

    def modify_current_card(self, parsed_cmd:list):
        '''Interactively modify text in current card. Changes both dataset and the source file'''
        if self.state is None:
            self._adapt(self.modify_current_card, state='mcc')
        try:
            msg = self.cli.modify_card(parsed_cmd)
            if self.cli.state == 'mcc_exit':
                self._exit(msg)
        except KeyboardInterrupt:
            self._exit('Aborted')

    