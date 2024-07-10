import timer
import re
from copy import deepcopy
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from utils import * 
from data_types import HIDE_TIPS_POLICIES
from fcc import fcc
from efc import EFC
from stats import stats
from widgets import CheckableComboBox, ScrollableOptionsWidget
from typing import Callable
from random import shuffle


class fcc_gui():

    def __init__(self):
        self.DEFAULT_PS1 = self.config['THEME']['default_ps1']
        self.init_font()
        self.__create_tabs()
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'main')
        self.newline = "\n"  # TODO remove in python3.12
        self.rt_re = re.compile('[^\u0000-\uFFFF]')


    def __create_tabs(self):
        self.active_tab_ident = None
        self.console = None
        self.tabs = dict()

        self.create_tab(
            ident="fcc",
            window_title="Console",
            console_prompt=self.DEFAULT_PS1,
            get_x_sidewindow=self.__get_fcc_sidewindow,
            run_x_command=self.run_fcc_command
        )

        self.create_tab(
            ident="sod",
            window_title="Search Online Dictionaries",
            console_prompt=self.DEFAULT_PS1,
            get_x_sidewindow=self.__get_fcc_sidewindow,
            run_x_command=self.run_fcc_command
        )
        self.activate_tab("sod")
        self.console.setGeometry(0, 0, *self.config["GEOMETRY"]["sod"])
        self.tabs["sod"]["fcc_instance"].sod([])

        self.activate_tab("fcc")


    def create_tab(
        self,
        ident: str,
        window_title: str,
        console_prompt: str,
        get_x_sidewindow: Callable,
        run_x_command: Callable,
    ):
        self.tabs[ident] = {
            "window_title": window_title,
            "console": self.create_console(),
            "console_prompt": console_prompt,
            "console_log": list(),
            "cmds_log": [""],
            "tmp_cmd": "",
            "cmds_cursor": 0,
            "get_x_sidewindow": get_x_sidewindow,
            "run_x_command": run_x_command,
            "fcc_instance": fcc(self)
        }
        self.side_window_titles[ident] = window_title
        self.create_ks_mapping(ident)
        self.add_shortcut('run_command', run_x_command, ident)


    def activate_tab(self, ident: str):
        if self.active_tab_ident == ident:
            return
        elif self.active_tab_ident:
            self._deactivate_tab()
        self.CONSOLE_PROMPT = self.tabs[ident]["console_prompt"]
        self.CONSOLE_LOG = self.tabs[ident]["console_log"]
        self.CMDS_LOG = self.tabs[ident]["cmds_log"]
        self.CMDS_CURSOR = self.tabs[ident]["cmds_cursor"]
        self.console = self.tabs[ident]["console"]
        self.fcc_inst = self.tabs[ident]["fcc_instance"]
        self.fcc_inst.update_console_id(self.tabs[ident]["console"])
        self.tmp_cmd = self.tabs[ident]["tmp_cmd"]
        self.get_terminal_sidewindow = self.tabs[ident]["get_x_sidewindow"]
        self.run_command = self.tabs[ident]["run_x_command"]
        self.active_tab_ident = ident

    def _deactivate_tab(self):
        try:
            self.tabs[self.active_tab_ident]["console_prompt"] = self.CONSOLE_PROMPT
            self.tabs[self.active_tab_ident]["console_log"] = self.CONSOLE_LOG.copy()
            self.tabs[self.active_tab_ident]["cmds_log"] = self.CMDS_LOG.copy()
            self.tabs[self.active_tab_ident]["cmds_cursor"] = self.CMDS_CURSOR
            self.tabs[self.active_tab_ident]["tmp_cmd"] = self.tmp_cmd
            self.active_tab_ident = None
        except KeyError:
            pass

    def __get_fcc_sidewindow(self):
        """Shared method for initializing the terminal"""
        self.arrange_fcc_window()
        self.open_side_window(self.fcc_layout, self.active_tab_ident)
        self.console.setFocus()
        self.move_cursor_to_end()

    def get_fcc_sidewindow(self):
        """Open FCC terminal directly"""
        self.activate_tab("fcc")
        self.get_terminal_sidewindow()

    def get_sod_sidewindow(self):
        """Open SOD terminal directly"""
        self.activate_tab("sod")
        self.get_terminal_sidewindow()

    def init_font(self):
        self.CONSOLE_FONT = QtGui.QFont(
            self.config['THEME']['console_font'], 
            self.config['THEME']['console_font_size']
        )
        self.caliper = Caliper(QtGui.QFontMetricsF(self.CONSOLE_FONT))

    @property
    def curpos(self) -> int:
        return self.console.textCursor().position()
    
    @property
    def promptend(self) -> int:
        return (
            self.rt_re.sub("  ", self.console.toPlainText()).rfind(
                f"{self.newline}{self.CONSOLE_PROMPT}"
            )
            + len(self.CONSOLE_PROMPT)
            + 1
        )

    def get_input(self) -> str:
        return self.console.toPlainText()[self.promptend:]
    

    def arrange_fcc_window(self):
        self.fcc_layout = widget.QGridLayout()
        if self.CONSOLE_LOG:
            self.CONSOLE_LOG[:-1] = [i for i in self.CONSOLE_LOG[:-1] if i != self.CONSOLE_PROMPT]
            if self.CONSOLE_LOG[-1].startswith(self.CONSOLE_PROMPT): 
                self.CONSOLE_LOG[-1] = self.CONSOLE_PROMPT
                self.tmp_cmd = self.console.toPlainText().split('\n')[-1][len(self.CONSOLE_PROMPT):]
            else:
                self.CONSOLE_LOG.append(self.CONSOLE_PROMPT)
        else:
            self.CONSOLE_LOG = [self.CONSOLE_PROMPT]

        # Dump fcc_queue while preserving the prompt content
        if self.active_tab_ident == "fcc":
            cmd = self.CONSOLE_LOG.pop()
            self.console.setText('\n'.join(self.CONSOLE_LOG))
            for msg in fcc_queue.dump():
               self.fcc_inst.post_fcc(msg)
            self.console.append(cmd + self.tmp_cmd)
            self.CONSOLE_LOG.append(cmd)
        self.fcc_layout.addWidget(self.console, 0, 0)

        
    def create_console(self) -> widget.QTextEdit:
        console = widget.QTextEdit(self)
        console.keyPressEvent = self.cli_shortcuts
        console.setFont(self.CONSOLE_FONT)
        console.setAcceptRichText(False)
        console.setStyleSheet(self.textbox_stylesheet)
        console.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return console


    def cli_shortcuts(self, event:QtGui.QKeyEvent):
        event_key = event.key()
        if (event.modifiers() & Qt.ControlModifier) and event_key == Qt.Key_L:
            self.fcc_inst.execute_command(['cls'], followup_prompt=False)
        elif event_key == Qt.Key_Home:
            cur = self.console.textCursor()
            cur.setPosition(self.promptend)
            self.console.setTextCursor(cur)
        elif event_key == Qt.Key_Return:
            self.nav_mapping[self.side_window_id]['run_command']()
        elif event_key == Qt.Key_Up:
            if self.CMDS_CURSOR == 0: 
                self.tmp_cmd = self.console.toPlainText()[self.promptend:]
            self.CMDS_CURSOR -= 1 if -self.CMDS_CURSOR < len(self.CMDS_LOG) else 0
            self.update_console_cmds_nav()
        elif event_key == Qt.Key_Down:
            if self.CMDS_CURSOR != 0:
                self.CMDS_CURSOR += 1
                self.update_console_cmds_nav()
        elif event_key in {Qt.Key_Left, Qt.Key_Backspace}:
            if self.curpos > self.promptend:
                widget.QTextEdit.keyPressEvent(self.console, event)
        elif event.matches(QtGui.QKeySequence.Paste):
            self.console.textCursor().insertText(
                widget.QApplication.clipboard().text().replace("\n", " ").strip()
            )
        else: 
            widget.QTextEdit.keyPressEvent(self.console, event) 


    def update_console_cmds_nav(self):
        console_content = self.console.toPlainText().split('\n')
        mod_content = console_content[:-1]
        if self.tmp_cmd and self.CMDS_CURSOR==0:
            c = self.tmp_cmd
            self.tmp_cmd = ''
        else:
            c = self.CMDS_LOG[self.CMDS_CURSOR]
        mod_content.append(f'{self.CONSOLE_PROMPT}{c}')
        self.console.setText('\n'.join(mod_content))
        self.move_cursor_to_end()


    def add_cmd_to_log(self, cmd:str):
        if cmd:
            if self.CMDS_LOG[-1] != cmd:
                self.CMDS_LOG.append(cmd)
            if not self.CONSOLE_LOG[-1].endswith(cmd):
                self.CONSOLE_LOG[-1]+=cmd
        self.CMDS_CURSOR = 0
        

    def run_fcc_command(self):
        cmd = self.console.toPlainText().split("\n")[-1][len(self.CONSOLE_PROMPT):]
        self.add_cmd_to_log(cmd)
        self.fcc_inst.execute_command(cmd.split(" "))
        self.move_cursor_to_end()
    

    def move_cursor_to_end(self):
        self.console.moveCursor(QtGui.QTextCursor.End)
    


class efc_gui(EFC):

    def __init__(self):
        EFC.__init__(self)
        self.side_window_titles['efc'] = 'EFC'
        self.cur_efc_index = 0
        # add button to main window
        self.efc_button = self.create_button(self.config["ICONS"]["efc"], self.get_efc_sidewindow)
        self.layout_third_row.addWidget(self.efc_button, 2, 2)
        self.init_shortcuts_efc()
        

    def init_shortcuts_efc(self):
        self.add_shortcut('efc', self.get_efc_sidewindow, 'main')
        self.add_shortcut('next_efc', self.load_next_efc, 'main')
        self.add_shortcut('run_command', self.load_selected_efc, 'efc')
        self.add_shortcut('negative', lambda: self.nagivate_efc_list(1), 'efc')
        self.add_shortcut('reverse', lambda: self.nagivate_efc_list(-1), 'efc')
        self.add_shortcut('load', self.get_load_sidewindow, 'efc')
        self.add_shortcut('progress', self.get_progress_sidewindow, 'efc')
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'efc')
        self.add_shortcut('config', self.get_config_sidewindow, 'efc')
        self.add_shortcut('stats', self.get_stats_sidewindow, 'efc')
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'efc')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'efc')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'efc')


    def get_efc_sidewindow(self):
        self.arrange_efc_window()
        self.open_side_window(self.efc_layout, 'efc')
        

    def arrange_efc_window(self):
        # Style
        self.textbox_stylesheet = self.config['THEME']['textbox_style_sheet']
        self.button_style_sheet = self.config['THEME']['button_style_sheet']
        self.BUTTON_FONT = QtGui.QFont(self.config['THEME']['font'], self.config['THEME']['font_button_size'])
        self.textbox_width = 275
        self.textbox_height = 200
        self.buttons_height = 45

        # Elements
        self.efc_layout = widget.QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(self.create_load_efc_button(), 1, 0, 1, 1)

        # Fill List Widget
        [self.recommendation_list.addItem(str(r)) for r in self.get_recommendations()]
        self.files_count = self.recommendation_list.count()
        if self.files_count: 
            self.cur_efc_index = min(self.files_count-1, self.cur_efc_index)
            self.recommendation_list.setCurrentRow(self.cur_efc_index)


    def create_recommendations_list(self):
        self.recommendation_list = widget.QListWidget(self)
        self.recommendation_list.setFixedWidth(self.textbox_width)
        self.recommendation_list.setFont(self.BUTTON_FONT)
        self.recommendation_list.setStyleSheet(self.textbox_stylesheet)
        return self.recommendation_list


    def create_load_efc_button(self):
        efc_button = widget.QPushButton(self)
        efc_button.setFixedHeight(self.buttons_height)
        efc_button.setFixedWidth(self.textbox_width)
        efc_button.setFont(self.BUTTON_FONT)
        efc_button.setText('Load')
        efc_button.setStyleSheet(self.button_style_sheet)
        efc_button.clicked.connect(self.load_selected_efc)
        return efc_button


    def nagivate_efc_list(self, move:int):
        new_index = self.cur_efc_index + move
        if new_index < 0: self.cur_efc_index = self.files_count-1
        elif new_index >= self.files_count: self.cur_efc_index = 0
        else: self.cur_efc_index = new_index 
        self.recommendation_list.setCurrentRow(self.cur_efc_index)

    def load_next_efc(self):

        if self.config["next_efc"]["require_recorded"] and not self.is_recorded:
            fcc_queue.put("Review current revision before proceeding")
            return

        fd = None
        recs = self.get_recommendations()

        if not recs:
            fcc_queue.put("There are no EFC recommendations")
            return

        if self.config["next_efc"]["reversed"]:
            recs = reversed(recs)
        if self.config["next_efc"]["random"]:
            shuffle(recs)
        
        for rec in recs:
            try:
                tmp_fd = [fd for fd in self.db.files.values() if fd.basename == rec][0]
                if self.config["next_efc"]["skip_mistakes"] and tmp_fd.kind==self.db.KINDS.mst:
                    continue
                else:
                    fd = tmp_fd
                    break
            except IndexError:
                if not self.config["next_efc"]["skip_new"]:
                    fd = self.db.files[self.paths_to_suggested_lngs[recs[0]]]
                    break
        
        if fd:
            self.initiate_flashcards(fd)
            self.del_side_window()
        else:
            fcc_queue.put("There are no EFC recommendations")

    def load_selected_efc(self):
        if fd := self.get_fd_from_selected_file():
            self.initiate_flashcards(fd)
            self.del_side_window()



class load_gui:

    def __init__(self):
        self.side_window_titles['load'] = 'Load'
        self.cur_load_index = 0
        # add button to main window
        self.load_button = self.create_button(self.config["ICONS"]["load"], self.get_load_sidewindow)
        self.layout_third_row.addWidget(self.load_button, 2, 0)
        self.init_shortcuts_load()


    def init_shortcuts_load(self):
        self.add_shortcut('load', self.get_load_sidewindow, 'main')
        self.add_shortcut('run_command', self.load_selected_file, 'load')
        self.add_shortcut('negative', lambda: self.nagivate_load_list(1), 'load')
        self.add_shortcut('reverse', lambda: self.nagivate_load_list(-1), 'load')
        self.add_shortcut('efc', self.get_efc_sidewindow, 'load')
        self.add_shortcut('progress', self.get_progress_sidewindow, 'load')
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'load')
        self.add_shortcut('config', self.get_config_sidewindow, 'load')
        self.add_shortcut('stats', self.get_stats_sidewindow, 'load')
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'load')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'load')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'load')
    

    def get_load_sidewindow(self):
        self.arrange_load_window()
        self.open_side_window(self.load_layout, 'load')


    def arrange_load_window(self):
        # Window Parameters
        self.buttons_height = 45
        self.textbox_width = 275

        # Style
        self.textbox_stylesheet = (self.config['THEME']['textbox_style_sheet'])
        self.button_style_sheet = self.config['THEME']['button_style_sheet']
        self.BUTTON_FONT = QtGui.QFont(self.config['THEME']['font'], self.config['THEME']['font_button_size'])

        # Elements
        self.load_layout = widget.QGridLayout()
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0)
        self.load_layout.addWidget(self.create_load_button(), 1, 0, 1, 1)

        # Fill
        self.fill_flashcard_files_list()
        if self.files_count: self.flashcard_files_qlist.setCurrentRow(self.cur_load_index)


    def get_flashcard_files_list(self):
        self.flashcard_files_qlist = widget.QListWidget(self)
        self.flashcard_files_qlist.setFixedWidth(self.textbox_width)
        self.flashcard_files_qlist.setFont(self.BUTTON_FONT)
        self.flashcard_files_qlist.setStyleSheet(self.textbox_stylesheet)
        self.flashcard_files_qlist.setVerticalScrollBar(self.get_scrollbar())
        return self.flashcard_files_qlist


    def fill_flashcard_files_list(self):
        self.db.update_fds()
        self.load_map, i = dict(), 0
        for fd in self.db.get_sorted_languages():
            self.flashcard_files_qlist.addItem(fd.basename)
            self.load_map[i] = fd.filepath
            i+=1
        for fd in self.db.get_sorted_mistakes():
            self.flashcard_files_qlist.addItem(fd.basename)
            self.load_map[i] = fd.filepath
            i+=1
        for fd in self.db.get_sorted_revisions():
            self.flashcard_files_qlist.addItem(fd.basename)
            self.load_map[i] = fd.filepath
            i+=1
        self.files_count = self.flashcard_files_qlist.count()

        
    def create_load_button(self):
        load_button = widget.QPushButton(self)
        load_button.setFixedHeight(self.buttons_height)
        load_button.setFixedWidth(self.textbox_width)
        load_button.setFont(self.BUTTON_FONT)
        load_button.setText('Load')
        load_button.setStyleSheet(self.button_style_sheet)
        load_button.clicked.connect(self.load_selected_file)
        return load_button

    
    def nagivate_load_list(self, move:int):
        new_index = self.cur_load_index + move
        if new_index < 0: self.cur_load_index = self.files_count-1
        elif new_index >= self.files_count: self.cur_load_index = 0
        else: self.cur_load_index = new_index 
        self.flashcard_files_qlist.setCurrentRow(self.cur_load_index)


    def load_selected_file(self):
        self.initiate_flashcards(
            self.db.files[self.load_map[self.flashcard_files_qlist.currentRow()]]
        )



class mistakes_gui():
    # Used for showing cards that user guessed wrong
    # after the revision finishes
    # no logic module for this side window

    def __init__(self):
        self.side_window_titles['mistakes'] = 'Mistakes'
        self.score_button.clicked.connect(self.get_mistakes_sidewindow)
        self.init_shortcuts_mistakes()


    def init_shortcuts_mistakes(self):
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'main')
        self.add_shortcut('efc', self.get_efc_sidewindow, 'mistakes')
        self.add_shortcut('load', self.get_load_sidewindow, 'mistakes')
        self.add_shortcut('progress', self.get_progress_sidewindow, 'mistakes')
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'mistakes')
        self.add_shortcut('config', self.get_config_sidewindow, 'mistakes')
        self.add_shortcut('stats', self.get_stats_sidewindow, 'mistakes')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'mistakes')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'mistakes')
    
    def get_mistakes_sidewindow(self):
        if self.active_file.kind in self.db.GRADED:
            self.arrange_mistakes_window()
            self.open_side_window(self.mistakes_layout, 'mistakes')
            self.show_mistakes()
        else:
            fcc_queue.put('Mistakes are unavailable for a Language')

    def arrange_mistakes_window(self):
        self.textbox_stylesheet = self.config['THEME']['textbox_style_sheet']
        self.button_style_sheet = self.config['THEME']['button_style_sheet']
        self.mistakes_layout = widget.QGridLayout()
        self.mistakes_layout.addWidget(self.create_mistakes_list(), 0, 0)
        
    def show_mistakes(self):
        out, sep = list(), ' | '
        cell_args = {
            'pixlim':(self.config['GEOMETRY']['mistakes'][0]-self.caliper.strwidth(sep))/2 - 2*self.caliper.scw, 
            'suffix':self.config['THEME']['default_suffix'], 
            'align':self.config['cell_alignment']
        }
        for m in self.mistakes_list:
            m1 = self.caliper.make_cell(m[self.default_side], **cell_args)
            m2 = self.caliper.make_cell(m[1-self.default_side], **cell_args)
            out.append(f"{m1}{sep}{m2}")
        self.mistakes_qtext.setText('\n'.join(out))

    def create_mistakes_list(self):
        self.mistakes_qtext = widget.QTextEdit(self)
        self.mistakes_qtext.setFont(self.CONSOLE_FONT)
        self.mistakes_qtext.setReadOnly(True)
        self.mistakes_qtext.setStyleSheet(self.textbox_stylesheet)
        return self.mistakes_qtext


class stats_gui(stats):

    def __init__(self):
        self.side_window_titles['stats'] = 'Statistics'
        stats.__init__(self)
        self.stats_button = self.create_button(self.config["ICONS"]["stats"], self.get_stats_sidewindow)
        self.layout_fourth_row.addWidget(self.stats_button, 3, 1)
        self.init_shortcuts_stats()


    def init_shortcuts_stats(self):
        self.add_shortcut('stats', self.get_stats_sidewindow, 'main')
        self.add_shortcut('efc', self.get_efc_sidewindow, 'stats')
        self.add_shortcut('load', self.get_load_sidewindow, 'stats')
        self.add_shortcut('progress', self.get_progress_sidewindow, 'stats')
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'stats')
        self.add_shortcut('config', self.get_config_sidewindow, 'stats')
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'stats')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'stats')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'stats')


    def get_stats_sidewindow(self):
        if self.active_file.kind in self.db.GRADED:
            self.arrange_stats_sidewindow()
            self.open_side_window(self.stats_layout, 'stats')
        else:
            fcc_queue.put(f'Statistics are not available for a {self.db.KFN[self.active_file.kind]}')

    def arrange_stats_sidewindow(self):
        self.get_data_for_current_revision(self.active_file.signature)
        self.get_stats_chart()
        self.get_stats_table()
        self.stats_layout = widget.QGridLayout()
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stats_layout.addLayout(self.stat_table, 1, 0)
    

    def get_stats_chart(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        rect = None

        ax = self.figure.add_subplot()
        ax.bar(self.formatted_dates, self.chart_values, color=config['THEME']['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center')

        # Time spent for each revision
        time_spent_plot = ax.twinx()
        time_spent_plot.plot(self.formatted_dates, self.time_spent_minutes, color='#979dac', 
                linewidth=1, zorder=9)

        # Labels
        for rect, label in zip(ax.patches, self.dynamic_chain_index):
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                    color=self.config['THEME']['stat_chart_text_color'])

         # horizontal line at EFC predicate
        if rect and self.config['opt']['show_efc_line']:
            ax.axhline(y=self.total_cards*0.8, color='#a0a0a0', linestyle='--', zorder=-3)
            ax.text(rect.get_x() + rect.get_width()/1, self.total_cards*0.8, f'{self.config["efc_threshold"]}%', va="bottom", color='#a0a0a0')

        # add labels - time spent
        if self.config['opt']['show_cpm_stats']:
            time_spent_labels = ['{:.0f}'.format(self.total_cards/(x/60)) if x else '-' for x in self.time_spent_seconds]
        else:
            time_spent_labels = self.time_spent_minutes
        for x, y in zip(self.formatted_dates, time_spent_labels):
            # xytext - distance between points and text label
            time_spent_plot.annotate(y, (x, y), textcoords="offset points", xytext=(0,5), ha='center',
                        color=self.config['THEME']['stat_chart_text_color'])

        # Style
        self.figure.set_facecolor(self.config['THEME']['stat_background_color'])
        ax.set_facecolor(self.config['THEME']['stat_chart_background_color'])
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.set_ylim([0, self.total_cards+2])
        ax.tick_params(colors=self.config['THEME']['stat_chart_text_color'],
                        labelrotation=0,
                        pad=1)
        self.figure.tight_layout(pad=0.1)
        ax.get_yaxis().set_visible(False)
        time_spent_plot.get_yaxis().set_visible(False)
        time_spent_plot.set_ylim([0, 9999])
        self.figure.subplots_adjust(left=0.0, bottom=0.1, right=0.999, top=0.997)

        self.canvas.draw()        


    def get_stats_table(self):
        self.stat_table = widget.QGridLayout()

        self.repeated_times_button = self.create_button(f'Repeated\n{self.sum_repeated} time{"s" if self.sum_repeated > 1 else ""}')
        self.days_from_last_rev = self.create_button(f'Last Revision\n{str(self.last_rev_days_ago).split(",")[0]} ago')
        self.days_from_creation = self.create_button(f'Created\n{str(self.days_ago).split(",")[0]} ago')

        # estimate total time spent if some records miss time_spent
        interval, rem = (('minute', 0), ('hour', 2))[self.total_seconds_spent>3600]
        if self.missing_records_cnt == 0:
            self.missing_records_adj = format_seconds_to(
                self.total_seconds_spent, interval, int_name=interval.capitalize(), rem=rem, sep=':'
            )
        elif self.total_seconds_spent != 0:
            # estimate total time by adding to actual total_seconds_spent, 
            # the estimate = X * count of missing records multiplied by average time spent on non-zero revision
            # X is an arbitrary number to adjust for learning curve
            adjustment = 1.481*self.missing_records_cnt*(self.total_seconds_spent/(self.sum_repeated-self.missing_records_cnt))
            fmt_time = format_seconds_to(self.total_seconds_spent + adjustment, interval, int_name=interval.capitalize(), rem=rem, sep=':')
            self.missing_records_adj = f"±{fmt_time}"
        else:
            # no time records for this revision
            fmt_time = format_seconds_to(self.sum_repeated*(60*self.total_cards/12), interval, int_name=interval.capitalize(), rem=rem, sep=':')
            self.missing_records_adj = f'±{fmt_time}'

        self.total_time_spent = self.create_button(f'Spent\n{self.missing_records_adj}')

        self.stat_table.addWidget(self.repeated_times_button, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev, 0, 1)
        self.stat_table.addWidget(self.days_from_creation, 0, 2)
        self.stat_table.addWidget(self.total_time_spent, 0, 3)



class progress_gui(stats):

    def __init__(self):
        stats.__init__(self)
        self.side_window_titles['progress'] = 'Progress'
        self.progress_button = self.create_button(self.config["ICONS"]["progress"], self.get_progress_sidewindow)
        self.layout_fourth_row.addWidget(self.progress_button, 3, 2)
        self.init_shortcuts_progress()
    

    def init_shortcuts_progress(self):
        self.add_shortcut('progress', self.get_progress_sidewindow, 'main')
        self.add_shortcut('stats', self.get_stats_sidewindow, 'progress')
        self.add_shortcut('efc', self.get_efc_sidewindow, 'progress')
        self.add_shortcut('load', self.get_load_sidewindow, 'progress')
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'progress')
        self.add_shortcut('config', self.get_config_sidewindow, 'progress')
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'progress')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'progress')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'progress')


    def get_progress_sidewindow(self, lngs:set=None):
        try:
            self.arrange_progress_sidewindow(lngs or self.config['languages'])
            self.open_side_window(self.progress_layout, 'progress')
        except ValueError:
            fcc_queue.put('No data found for Progress')


    def arrange_progress_sidewindow(self, lngs:set):
        self.get_data_for_progress(lngs)
        self.get_progress_chart(lngs)
        self.progress_layout = widget.QGridLayout()
        self.progress_layout.addWidget(self.canvas, 0, 0)


    def get_progress_chart(self, lngs:set):
        
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

        # initiate plots
        total_words_plot = self.figure.add_subplot()
        total_words_plot.bar(self.formatted_dates, self.second_chart_values, color='#979dac', 
                edgecolor='#000000', linewidth=0.7, align='center', zorder=9)

        positives_plot = total_words_plot.twinx()
        positives_plot.bar(self.formatted_dates, self.chart_values, color=config['THEME']['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center', zorder=0)

        revision_count_plot = total_words_plot.twinx()
        revision_count_plot.plot(self.formatted_dates, self.revision_count, color='#979dac', 
                linewidth=1, zorder=9)

        # add labels - last positives sum
        for rect, label in zip(positives_plot.patches, self.chart_values):
                height = rect.get_height()
                label = '' if label == 0 else "{:.0f}".format(label)
                positives_plot.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                        color=self.config['THEME']['stat_chart_text_color'], zorder=10)

        # add labels - total sum
        unlearned = self.second_chart_values - self.chart_values 
        for rect, label in zip(total_words_plot.patches, unlearned):
            height = rect.get_height()
            x = rect.get_x() + rect.get_width()/2
            y = height-label/1.25
            label = '' if label == 0 else "{:.0f}".format(label)
            total_words_plot.text(x, y, label, ha="center", va="bottom", 
                    color=self.config['THEME']['stat_chart_text_color'], zorder=10)
        
        # add labels - repeated times
        for x, y in zip(self.formatted_dates, self.revision_count):
            # xytext - distance between points and text label
            revision_count_plot.annotate("#{:.0f}".format(y), (x, y), textcoords="offset points", xytext=(0,5), ha='center',
                        color=self.config['THEME']['stat_chart_text_color'])
                      
        # Style
        self.figure.set_facecolor(self.config['THEME']['stat_background_color'])
        total_words_plot.set_facecolor(self.config['THEME']['stat_chart_background_color'])
        positives_plot.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        total_words_plot.tick_params(colors=self.config['THEME']['stat_chart_text_color'])
        self.figure.tight_layout(pad=0.1)
        positives_plot.get_yaxis().set_visible(False)
        revision_count_plot.get_yaxis().set_visible(False)
        positives_plot.get_xaxis().set_visible(False)
        title = ' & '.join(lngs) if lngs else 'All'
        self.figure.suptitle(title, fontsize=18, y=0.92, color=self.config['THEME']['font_color'])
        self.figure.subplots_adjust(left=0.0, bottom=0.06, right=0.997, top=0.997)

        # synchronize axes
        max_ = max(
            self.chart_values.max(), 
            self.second_chart_values.max()
        )
        positives_plot.set_ylim([0, max_*1.2])
        total_words_plot.set_ylim([0, max_*1.2])
        revision_count_plot.set_ylim([0, max_*99])

        self.canvas.draw()        



class config_gui():

    def __init__(self):
        self.side_window_titles['config'] = 'Settings'
        self.config = Config()
        self.funcs_to_restart = list()
        self.config_button = self.create_button(self.config["ICONS"]['config'], self.get_config_sidewindow)
        self.layout_third_row.addWidget(self.config_button, 2, 5)
        self.add_shortcut('config', self.get_config_sidewindow, 'main')


    def get_config_sidewindow(self):
        self.themes_dict = self.load_themes()
        self.arrange_config_sidewindow()
        self.open_side_window(self.config_layout, 'config')


    def arrange_config_sidewindow(self):
        # Window Parameters
        self.buttons_height = 45
        self.textbox_width = 275

        # Style
        self.textbox_stylesheet = self.config['THEME']['textbox_style_sheet']
        self.button_style_sheet = self.config['THEME']['button_style_sheet']
        self.BUTTON_FONT = QtGui.QFont(self.config['THEME']['font'], self.config['THEME']['font_button_size'])

        # Elements
        self.config_layout = widget.QGridLayout()
        self.opt_scroll_area = widget.QScrollArea()
        self.opt_scroll_area.setWidgetResizable(True)
        self.opt_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.opt_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.opt_scroll_area.setVerticalScrollBar(self.get_scrollbar())
        self.options_layout = ScrollableOptionsWidget()
        self.opt_scroll_area.setWidget(self.options_layout)
        self.config_layout.addWidget(self.opt_scroll_area)
        self.db.update_fds()
        self.fill_config_list()


    def _init_confirm_and_close_button(self) -> widget.QPushButton:
        if self.funcs_to_restart:
            self.confirm_and_close_button = self.create_button(
                "Restart required", 
                lambda: self.__on_config_commit_restart(self.funcs_to_restart)
            )
        else:
            self.confirm_and_close_button = self.create_button(
                'Confirm changes', 
                self.commit_config_update
            )

    def fill_config_list(self):
        # initate labels and comboboxes
        self._init_confirm_and_close_button()
        self.card_default_cbx = self.create_combobox(self.config['card_default_side'], ['0','1','Random'], multi_choice=False)
        self.languages_cbx = self.create_combobox(self.config['languages'], self.db.get_available_languages())
        self.efc_threshold_qle = self.create_config_qlineedit(self.config['efc_threshold'])
        self.efc_cache_exp_qle = self.create_config_qlineedit(self.config['efc_cache_expiry_hours'])
        self.next_efc_policy_cbx = self.create_combobox(self.config['next_efc'], list(self.config["next_efc"].keys()))
        self.days_to_new_rev_qle = self.create_config_qlineedit(self.config['days_to_new_rev'])
        self.mst_rev_int_qle = self.create_config_qlineedit(self.config['mistakes_review_interval_days'])
        self.optional_featuers_cbx = self.create_combobox(self.config['opt'], list(self.config["opt"].keys()))
        self.init_rep_qle = self.create_config_qlineedit(self.config['init_revs_cnt'])
        self.init_revh_qle = self.create_config_qlineedit(self.config['init_revs_inth'])
        self.check_file_monitor_cbx = self.create_combobox(
            self.config['allow_file_monitor'], ["True", "False"], multi_choice=False
        )
        self.mistakes_buffer_qle = self.create_config_qlineedit(self.config['mistakes_buffer'])
        self.theme_cbx = self.create_combobox(self.config['active_theme'], self.themes_dict.keys(), multi_choice=False)
        self.final_actions_cbx = self.create_combobox(
            self.config['final_actions'], 
            list(self.config["final_actions"].keys()),
            multi_choice=False,
        )
        self.pace_card_qle = self.create_config_qlineedit(self.config['pace_card_interval'])
        self.csv_sniffer_qle = self.create_config_qlineedit(self.config['csv_sniffer'])
        self.sod_init_lng_cbx = self.create_combobox(
            self.config["SOD"]['initial_language'], ['auto', 'native', 'foreign'], multi_choice=False
        )
        self.cre_settings_cbx = self.create_combobox(
            self.config['CRE'], ['reversed', 'auto_save_mistakes', 'auto_next'],  multi_choice=True
        )
        self.hide_tips_policy_rev_cbx = self.create_combobox(
            self.config["hide_tips"]["policy"][self.db.KINDS.rev], 
            [
                *HIDE_TIPS_POLICIES.get_common(),
                HIDE_TIPS_POLICIES.reg_rev, 
            ], 
            multi_choice=True
        )
        self.hide_tips_policy_lng_cbx = self.create_combobox(
            self.config["hide_tips"]["policy"][self.db.KINDS.lng], 
            [*HIDE_TIPS_POLICIES.get_common()], 
            multi_choice=True
        )
        self.hide_tips_policy_mst_cbx = self.create_combobox(
            self.config["hide_tips"]["policy"][self.db.KINDS.mst], 
            [*HIDE_TIPS_POLICIES.get_common()], 
            multi_choice=True
        )
        self.hide_tips_policy_eph_cbx = self.create_combobox(
            self.config["hide_tips"]["policy"][self.db.KINDS.eph], 
            [*HIDE_TIPS_POLICIES.get_common()], 
            multi_choice=True
        )
        self.hide_tips_pattern_qle = self.create_config_qlineedit(self.config["hide_tips"]['pattern'])
        self.hide_tips_connector_cbx = self.create_combobox(
            self.config["hide_tips"]['connector'],
            ["and", "or"],
            multi_choice=False
        )
        self.timespent_len_qle = self.create_config_qlineedit(self.config["timespent_len"])
        self.afterface_qle = self.create_config_qlineedit(self.config["after_face"])
        self.cell_alignment_cbx = self.create_combobox(self.config["cell_alignment"], ["left", "right"], multi_choice=False)
        self.emo_discretizer_cbx = self.create_combobox(self.config["EMO"]["discretizer"], 
            ["yeo-johnson", "decision-tree"],
            multi_choice=False
        )
        self.emo_lngs_cbx = self.create_combobox(self.config["EMO"]["languages"], 
            self.db.get_available_languages(),
            multi_choice=True
        )
        self.emo_approach_cbx = self.create_combobox(self.config["EMO"]["approach"], 
            ["Universal", "Language-Specific"],
            multi_choice=False
        )
        self.emo_cap_fold_qle = self.create_config_qlineedit(self.config["EMO"]["cap_fold"])
        self.emo_min_records_qle = self.create_config_qlineedit(self.config["EMO"]["min_records"])
        self.sod_files_cbx = self.create_combobox(
            self.config["SOD"]["files_list"], multi_choice=True, 
            content=sorted(self.db.get_all_files(dirs={self.db.LNG_DIR}))
        )
        self.popup_timeout_qle = self.create_config_qlineedit(self.config["POPUPS"]["timeout_ms"])
        self.popup_showani_qle = self.create_config_qlineedit(self.config["POPUPS"]["show_animation_ms"])
        self.popup_hideani_qle = self.create_config_qlineedit(self.config["POPUPS"]["hide_animation_ms"])
        self.popup_checkint_qle = self.create_config_qlineedit(self.config["POPUPS"]["check_interval_ms"])
        self.popup_importance_cbx = self.create_combobox(self.config["POPUPS"]["importance"], multi_choice=False, 
                                                    content=["0", "10", "20", "30", "40", "50"])
        self.popup_trigger_unrevmistakes_qle = self.create_config_qlineedit(self.config["POPUPS"]["triggers"]["unreviewed_mistakes_cnt"])
        
        self.options_layout.add_widget(self.card_default_cbx, self.create_label('Card default side'))
        self.options_layout.add_widget(self.languages_cbx, self.create_label('Languages'))
        self.options_layout.add_widget(self.efc_threshold_qle, self.create_label('EFC threshold'))
        self.options_layout.add_widget(self.efc_cache_exp_qle, self.create_label('EFC cache expiry (hours)'))
        self.options_layout.add_widget(self.next_efc_policy_cbx, self.create_label('EFC next policy'))
        self.options_layout.add_widget(self.days_to_new_rev_qle, self.create_label('Days between new revisions'))
        self.options_layout.add_widget(self.mst_rev_int_qle, self.create_label('Days between mistake reviews'))
        self.options_layout.add_widget(self.optional_featuers_cbx, self.create_label('Optional features'))
        self.options_layout.add_widget(self.init_rep_qle, self.create_label("Initial revision count"))
        self.options_layout.add_widget(self.init_revh_qle, self.create_label("Initial revision interval"))
        self.options_layout.add_widget(self.check_file_monitor_cbx, self.create_label('File monitor'))
        self.options_layout.add_widget(self.mistakes_buffer_qle, self.create_label('Mistakes buffer'))
        self.options_layout.add_widget(self.theme_cbx, self.create_label('Theme'))
        self.options_layout.add_widget(self.final_actions_cbx, self.create_label('Final actions'))
        self.options_layout.add_widget(self.pace_card_qle, self.create_label('Card pacing'))
        self.options_layout.add_widget(self.csv_sniffer_qle, self.create_label('CSV sniffer'))
        self.options_layout.add_widget(self.sod_files_cbx, self.create_label('SOD files list'))
        self.options_layout.add_widget(self.sod_init_lng_cbx, self.create_label('SOD initial language'))
        self.options_layout.add_widget(self.cre_settings_cbx, self.create_label('Comprehensive review'))
        self.options_layout.add_widget(self.hide_tips_policy_rev_cbx, self.create_label('Hide tips policy: Rev'))
        self.options_layout.add_widget(self.hide_tips_policy_lng_cbx, self.create_label('Hide tips policy: Lng'))
        self.options_layout.add_widget(self.hide_tips_policy_mst_cbx, self.create_label('Hide tips policy: Mst'))
        self.options_layout.add_widget(self.hide_tips_policy_eph_cbx, self.create_label('Hide tips policy: Eph'))
        self.options_layout.add_widget(self.hide_tips_pattern_qle, self.create_label('Hide tips pattern'))
        self.options_layout.add_widget(self.hide_tips_connector_cbx, self.create_label('Hide tips connector'))
        self.options_layout.add_widget(self.timespent_len_qle, self.create_label('Timespent display length'))
        self.options_layout.add_widget(self.afterface_qle, self.create_label('Afterface'))
        self.options_layout.add_widget(self.cell_alignment_cbx, self.create_label('Cell alignment'))
        self.options_layout.add_widget(self.emo_discretizer_cbx, self.create_label('EMO discretizer'))
        self.options_layout.add_widget(self.emo_lngs_cbx, self.create_label('EMO languages'))
        self.options_layout.add_widget(self.emo_approach_cbx, self.create_label('EMO approach'))
        self.options_layout.add_widget(self.emo_cap_fold_qle, self.create_label('EMO cap fold'))
        self.options_layout.add_widget(self.emo_min_records_qle, self.create_label('EMO min records'))
        self.options_layout.add_widget(self.popup_timeout_qle, self.create_label('Popup timeout (msec)'))
        self.options_layout.add_widget(self.popup_showani_qle, self.create_label('Popup enter (msec)'))
        self.options_layout.add_widget(self.popup_hideani_qle, self.create_label('Popup hide (msec)'))
        self.options_layout.add_widget(self.popup_checkint_qle, self.create_label('Popup check interval (msec)'))
        self.options_layout.add_widget(self.popup_importance_cbx, self.create_label('Popup importance threshold'))
        self.options_layout.add_widget(self.popup_trigger_unrevmistakes_qle, self.create_label('Popup Trigger mistakes cnt'))
        self.config_layout.addWidget(self.confirm_and_close_button)


    def commit_config_update(self):
        modified_config = deepcopy(self.config)
        modified_config['card_default_side'] = self.card_default_cbx.currentDataList()[0]
        modified_config['languages'] = self.languages_cbx.currentDataList()
        modified_config['efc_threshold'] = int(self.efc_threshold_qle.text())
        modified_config['efc_cache_expiry_hours'] = int(self.efc_cache_exp_qle.text())
        modified_config['next_efc'] = self.next_efc_policy_cbx.currentDataDict()
        modified_config['days_to_new_rev'] = int(self.days_to_new_rev_qle.text())
        modified_config['mistakes_review_interval_days'] = int(self.mst_rev_int_qle.text())
        modified_config['opt'] = self.optional_featuers_cbx.currentDataDict()
        modified_config['init_revs_cnt'] = int(self.init_rep_qle.text())
        modified_config['init_revs_inth'] = int(self.init_revh_qle.text())
        modified_config['allow_file_monitor'] = self.check_file_monitor_cbx.currentDataList()[0] == "True"
        modified_config['mistakes_buffer'] = max(1, int(self.mistakes_buffer_qle.text()))
        modified_config['active_theme'] = self.theme_cbx.currentDataList()[0]
        modified_config['final_actions'] = self.final_actions_cbx.currentDataDict()
        modified_config['THEME'].update(self.themes_dict[modified_config['active_theme']])
        modified_config['pace_card_interval'] = int(self.pace_card_qle.text())
        modified_config['csv_sniffer'] = self.csv_sniffer_qle.text()
        modified_config['SOD']['initial_language'] = self.sod_init_lng_cbx.currentDataList()[0]
        modified_config['SOD']['files_list'] = self.sod_files_cbx.currentDataList()
        modified_config["CRE"].update(self.cre_settings_cbx.currentDataDict())
        modified_config["hide_tips"]["policy"][self.db.KINDS.rev] = self.hide_tips_policy_rev_cbx.currentDataList()
        modified_config["hide_tips"]["policy"][self.db.KINDS.lng] = self.hide_tips_policy_lng_cbx.currentDataList()
        modified_config["hide_tips"]["policy"][self.db.KINDS.mst] = self.hide_tips_policy_mst_cbx.currentDataList()
        modified_config["hide_tips"]["policy"][self.db.KINDS.eph] = self.hide_tips_policy_eph_cbx.currentDataList()
        modified_config["hide_tips"]["pattern"] = self.hide_tips_pattern_qle.text()
        modified_config["hide_tips"]["connector"] = self.hide_tips_connector_cbx.currentDataList()[0]
        modified_config["timespent_len"] = int(self.timespent_len_qle.text())
        modified_config["after_face"] = self.afterface_qle.text()
        modified_config["cell_alignment"] = self.cell_alignment_cbx.currentDataList()[0]
        modified_config["EMO"]["discretizer"] = self.emo_discretizer_cbx.currentDataList()[0]
        modified_config["EMO"]["languages"] = self.emo_lngs_cbx.currentDataList()
        modified_config["EMO"]["approach"] = self.emo_approach_cbx.currentDataList()[0]
        modified_config["EMO"]["cap_fold"] = float(self.emo_cap_fold_qle.text())
        modified_config["EMO"]["min_records"] = int(self.emo_min_records_qle.text())
        modified_config["POPUPS"]["timeout_ms"] = int(self.popup_timeout_qle.text())
        modified_config["POPUPS"]["show_animation_ms"] = int(self.popup_showani_qle.text())
        modified_config["POPUPS"]["hide_animation_ms"] = int(self.popup_hideani_qle.text())
        modified_config["POPUPS"]["check_interval_ms"] = int(self.popup_checkint_qle.text())
        modified_config["POPUPS"]["importance"] = int(self.popup_importance_cbx.currentDataList()[0])
        modified_config["POPUPS"]["triggers"]["unreviewed_mistakes_cnt"] = int(self.popup_trigger_unrevmistakes_qle.text())

        if not self.config['opt']['side_by_side'] and modified_config['opt']['side_by_side']:
            self.toggle_primary_widgets_visibility(True)
        else:
            self.unfix_size(self)
            self.unfix_size(self.textbox)

        if modified_config['active_theme'] != self.config['active_theme']:
            self.funcs_to_restart.append(self.set_theme)

        if modified_config['allow_file_monitor'] != self.config['allow_file_monitor']:
            self.funcs_to_restart.append(self._modify_file_monitor)

        self.config.update(modified_config)
        self.config_manual_update()
        self.display_text(self.get_current_card().iloc[self.side])

        # Reload config window
        if not self.funcs_to_restart:
            self.confirm_and_close_button.setText("Config saved")
            self.confirm_and_close_button.clicked.disconnect()
        else:
            self.confirm_and_close_button.setText("Restart required")
            self.confirm_and_close_button.clicked.disconnect()
            self.confirm_and_close_button.clicked.connect(
                lambda: self.__on_config_commit_restart(self.funcs_to_restart)
            )


    def __on_config_commit_restart(self, funcs: list[Callable]):
        for f in funcs:
            f()
        self.funcs_to_restart.clear()
        self.confirm_and_close_button.setText("Config saved")
        self.confirm_and_close_button.clicked.disconnect()
        self.del_side_window()


    def _modify_file_monitor(self):
        self.initiate_file_monitor()
        if not self.active_file.tmp:
            self.file_monitor_add_path(self.active_file.filepath)
        self.file_monitor_add_path(self.config["SOD"]["last_file"])


    def create_combobox(self, value, content:list, multi_choice:bool=True):
        cb = CheckableComboBox(
            self, 
            allow_multichoice=multi_choice, 
            width=self.config["GEOMETRY"]["config"][0] // 2
        )
        cb.setStyleSheet(self.button_style_sheet)
        cb.setFont(self.BUTTON_FONT)
        if isinstance(value, dict):
            value = [k for k, v in value.items() if v is True]
        for i in content:
            try:
                cb.addItem(i, is_checked= i in value)
            except TypeError:
                cb.addItem(i, is_checked= i == str(value))
        return cb


    def create_config_qlineedit(self, value):
        qlineedit = widget.QLineEdit(self)
        qlineedit.setText(str(value))
        qlineedit.setFont(self.BUTTON_FONT)
        qlineedit.setStyleSheet(self.button_style_sheet)
        return qlineedit


    def create_label(self, text):
        label = widget.QLabel(self)
        label.setText(text)
        label.setFont(self.BUTTON_FONT)
        label.setText(text)
        label.setStyleSheet(self.button_style_sheet)
        return label
    
    def create_blank_widget(self):
        blank = widget.QLabel(self)
        blank.setStyleSheet("border: 0px")
        return blank

    def load_themes(self) -> dict:
        themes_dict = dict()
        themes_path = os.path.join(self.db.RES_PATH, "themes")
        theme_files = [f for f in os.listdir(themes_path) if f.endswith(".json")]
        for f in theme_files:
            theme = json.load(open(os.path.join(themes_path, f), "r"))
            theme_name = f.split(".")[0]
            themes_dict[theme_name] = theme
        return themes_dict

    def config_manual_update(self, key:str=None, subdict:str=None):
        if subdict == 'THEME':
            if key == 'console_font_size':
                self.init_font()
                self.console.setFont(self.CONSOLE_FONT)
                self.caliper.pixlen.cache_clear()
        elif not (key or subdict):
            self._efc_last_calc_time = 0
            self.db.update_fds()
            self.update_default_side()
            self.revtimer_hide_timer = self.config['opt']['hide_timer']
            self.revtimer_show_cpm_timer = self.config['opt']['show_cpm_timer']
            self.set_append_seconds_spent_function()
            self.initiate_pace_timer()
            self.initiate_notification_timer()
            self.tips_hide_re = re.compile(self.config["hide_tips"]["pattern"])
            self.set_should_hide_tips()



class timer_gui():

    def __init__(self):
        self.config = Config()
        self.side_window_titles['timer'] = 'Time Spent'
        self.data_getter = timer.Timespent_BE()
        self.TIMER_FONT_SIZE = 12
        self.timer_button = self.create_button(self.config["ICONS"]["timer"], self.get_timer_sidewindow)
        self.layout_fourth_row.addWidget(self.timer_button, 3, 5)
        self.TIMER_FONT = QtGui.QFont('Consolas', self.TIMER_FONT_SIZE)
        self.init_shortcuts_timer()


    def init_shortcuts_timer(self):
        self.add_shortcut('timespent', self.get_timer_sidewindow, 'main')
        self.add_shortcut('progress', self.get_progress_sidewindow, 'timer')
        self.add_shortcut('stats', self.get_stats_sidewindow, 'timer')
        self.add_shortcut('efc', self.get_efc_sidewindow, 'timer')
        self.add_shortcut('load', self.get_load_sidewindow, 'timer')
        self.add_shortcut('mistakes', self.get_mistakes_sidewindow, 'timer')
        self.add_shortcut('config', self.get_config_sidewindow, 'timer')
        self.add_shortcut('fcc', self.get_fcc_sidewindow, 'timer')
        self.add_shortcut('sod', self.get_sod_sidewindow, 'timer')


    def get_timer_sidewindow(self):
        self.create_timer_console()
        self.arrange_timer_sidewindow()
        self.show_data()
        self.open_side_window(self.timer_layout, 'timer')


    def arrange_timer_sidewindow(self, width_=500):
        self.timer_layout = widget.QGridLayout()
        self.timer_layout.addWidget(self.timer_console, 0, 0)


    def create_timer_console(self):
        self.timer_console = widget.QTextEdit(self)
        self.timer_console.setFont(self.TIMER_FONT)
        self.timer_console.setStyleSheet(self.textbox_stylesheet)
        self.timer_console.setReadOnly(True)


    def show_data(self):
        last_n = self.config['timespent_len']
        interval = 'm'
        res = self.data_getter.get_timespent_printout(last_n, interval)
        self.timer_console.setText(res)



class side_windows(fcc_gui, efc_gui, load_gui, 
                mistakes_gui, stats_gui, progress_gui, config_gui, timer_gui):
    def __init__(self):
        self.side_window_titles = dict()
        fcc_gui.__init__(self)
        efc_gui.__init__(self)
        load_gui.__init__(self)
        mistakes_gui.__init__(self)
        stats_gui.__init__(self)
        progress_gui.__init__(self)
        config_gui.__init__(self)
        timer_gui.__init__(self)
    

    def __del__(self):
        del self
