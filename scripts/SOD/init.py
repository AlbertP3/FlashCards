from utils import Config
from SOD.cli import CLI



class sod_spawn:

    def __init__(self, adapter:str, stream_out):
        self.config = Config()
        self.adapters = dict(fcc=self.adapt_to_fcc,
                             tui=self.adapt_to_terminal) 

        self.sout = stream_out
        self.adapters[adapter]()
        self.cli = CLI(output=self.sout,
                        wb_path=self.config['sod_filepath'], 
                        ws_sheet_name=self.config['sod_sheetname'])
        self.cli.cls()
        self.sout.mw.CONSOLE_PROMPT = self.cli.PHRASE_PROMPT
        self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)
        self.sout.mw.side_window_titles['fcc'] = 'Search Online Dictionaries'
        self.sout.mw.setWindowTitle(self.sout.mw.side_window_titles['fcc'])


# ======================= ADAPTER: FCC =======================
    def adapt_to_fcc(self):
        self.HISTORY:str = self.sout.mw.console.toPlainText()
        self.CMD_HISTORY:list = self.sout.mw.CMDS_LOG
        self.sout.mw.CMDS_LOG = ['']
        self.prev_window_title = self.sout.mw.side_window_titles['fcc']
        self.orig_post_method = self.sout.post_fcc
        self.orig_execute_method = self.sout.execute_command
        self.sout.post_fcc = self.monkey_patch_post_fcc
        self.sout.execute_command = self.monkey_patch_execute_command_fcc
        self.remove_adapter = self.remove_adapter_fcc
    
    def monkey_patch_post_fcc(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)
            self.HISTORY+='\n'+msg

    def monkey_patch_execute_command_fcc(self, parsed_input:list, followup_prompt:bool=True):
        if parsed_input[0] == 'cls':
            self.cli.cls()
        else:
            self.run(parsed_input)
        if followup_prompt: self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)

    def remove_adapter_fcc(self):
        self.sout.post_fcc = self.orig_post_method
        self.sout.mw.side_window_titles['fcc'] = self.prev_window_title
        self.sout.execute_command = self.orig_execute_method
        self.sout.mw.console.setText(self.HISTORY)
        self.sout.mw.CMDS_LOG = self.CMD_HISTORY


# ======================= ADAPTER: TERMINAL - WORK IN PROGRESS =======================
    def adapt_to_terminal(self):
        self.post_fcc = self.monkey_patch_post_terminal

    def monkey_patch_post_terminal(self, msg):
        if msg != self.sout.mw.CONSOLE_PROMPT:
            self.cli.cls(msg, keep_content=True, keep_cmd=True)

    def monkey_patch_execute_command_terminal(self, parsed_input:list, followup_prompt:bool=True):
        # TODO
        if parsed_input[0] not in self.sout.DOCS.keys():
            self.run(parsed_input)
        else:
            self.sout.console.setText('Command not allowed in SOD mode!')
        if followup_prompt: self.sout.console.append(self.sout.mw.CONSOLE_PROMPT)
    
    def monkey_patch_cls_terminal(self, msg, keep_content=True, keep_cmd=True):
        ...

    def remove_adapter_terminal(self):
        ...


# ======================= SOD MAIN LOOP ======================= 
    def run(self, cmd:list):
        if cmd == [''] and not self.cli.MODIFY_RES_EDIT_MODE \
            and not self.cli.QUEUE_SELECTION_MODE:
            # exit from modes
            if self.cli.SELECT_TRANSLATIONS_MODE \
                or self.cli.MODIFY_RES_EDIT_MODE \
                or self.cli.MANUAL_MODE:
                self.cli.reset_flags()
                self.cli.cls(self.cli.SAVE_ABORTED)
                self.sout.mw.CONSOLE_PROMPT = self.cli.PHRASE_PROMPT
            elif self.cli.QUEUE_MODE:
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
        elif self.cli.SELECT_TRANSLATIONS_MODE or self.cli.RES_EDIT_SELECTION_MODE \
                or self.cli.MODIFY_RES_EDIT_MODE:
            self.cli.select_translations(cmd)
        elif self.cli.MANUAL_MODE:
            self.cli.insert_manual(cmd)
        elif self.cli.QUEUE_MODE:
            self.cli.manage_queue(cmd)
        elif self.cli.QUEUE_SELECTION_MODE:
            self.cli.unpack_translations_from_queue(cmd)
        else:
            self.cli.execute_command(cmd)
