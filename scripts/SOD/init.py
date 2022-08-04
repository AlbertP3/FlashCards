from utils import *
from SOD.cli import CLI
import requests



class sod_spawn:

    def __init__(self, stream_out):
        self.config = Config.get_instance()
        self.sout = stream_out
        self.cli = CLI(output=self.sout,
                        wb_path=self.config['sod_filepath'], 
                        ws_sheet_name=self.config['sod_sheetname'])
        self.sout.clear_history()
        self.sout.SOD_MODE = True
        self.cli.cls()
        self.sout.CONSOLE_PROMPT = self.cli.PHRASE_PROMPT
        self.sout.setWindowTitle('Search Online Dictionaries')


    def run(self, cmd:list):
        if cmd == [''] and not self.cli.MODIFY_RES_EDIT_MODE \
            and not self.cli.QUEUE_SELECTION_MODE:
            # exit from modes
            if self.cli.SELECT_TRANSLATIONS_MODE \
                or self.cli.MODIFY_RES_EDIT_MODE \
                or self.cli.MANUAL_MODE:
                self.cli.reset_flags()
                self.cli.cls(self.cli.SAVE_ABORTED)
                self.sout.CONSOLE_PROMPT = self.cli.PHRASE_PROMPT
            elif self.cli.QUEUE_MODE:
                self.cli.setup_queue_unpacking()
            else:
                # Exit SOD
                self.sout.SOD_MODE = False
                self.sout.clear_history()
                self.sout.CONSOLE_PROMPT = self.sout.DEFAULT_PS1
                self.cli.close_wb()
                self.sout.setWindowTitle(self.sout.window_title)
                del self
        else:
            try:
                self.manage_modes(cmd)
            except requests.exceptions.ConnectionError:
                self.sout.post_fcc('No Internet Connection!')
                self.cli.create_queue_backup()


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
