import PyQt5.QtWidgets as widget
from utils import * 
from PyQt5 import QtGui
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FormatStrFormatter
from fcc import fcc
from efc import efc
from load import load
from stats import stats

# each class espouses one type of sidewindow (GUI + inherited logic)
# side_windows class comprising of multiple sidewindows is to be inherited by the main GUI


class fcc_gui(fcc):

    def __init__(self):
        fcc.__init__(self, qtextedit_console=True)

        self.CONSOLE_FONT = QtGui.QFont('Consolas', 14)
        self.CONSOLE_PROMPT = '$~>'
        self.CONSOLE_LOG = ''

        self.add_shortcut('c', self.get_fcc_sidewindow)
        self.add_shortcut('Insert', self.run_command)

        self.arrange_fcc_window()


    def get_fcc_sidewindow(self):
        self.arrange_fcc_window()
        self.switch_side_window(self.fcc_layout, 'fcc', 500 + self.LEFT)
        self.console.setText(self.reload_logs())
        self.console.setFocus()
        self.move_cursor_to_end()
        
        
    def arrange_fcc_window(self):
        self.fcc_layout = widget.QGridLayout()
        self.fcc_layout.addWidget(self.create_console(), 0, 0)

        
    def create_console(self):
        self.console = widget.QTextEdit(self)
        self.console.setFont(self.CONSOLE_FONT)
        self.console.setReadOnly(False)
        self.console.setStyleSheet(self.textbox_stylesheet)
        return self.console
    

    def run_command(self):
        # format user input
        trimmed_command = self.console.toPlainText().strip()

        # get command from last line
        last_prompt_index = trimmed_command.rfind(self.CONSOLE_PROMPT)
        trimmed_command = trimmed_command[last_prompt_index+len(self.CONSOLE_PROMPT):]

        # execute command
        parsed_command = trimmed_command.split(' ')   
        fcc.execute_command(self, parsed_command)

        self.move_cursor_to_end()
    

    def move_cursor_to_end(self):
        self.console.moveCursor(QtGui.QTextCursor.End)
    

    def reload_logs(self):
        
        # remove extensive command prompts
        self.CONSOLE_LOG = self.CONSOLE_LOG.replace(self.CONSOLE_PROMPT+'\n', '')
        
        if self.CONSOLE_LOG.endswith(self.CONSOLE_PROMPT):
            logs = self.CONSOLE_LOG
        else:
            logs = self.CONSOLE_LOG + '\n' + self.CONSOLE_PROMPT
        

        return logs


    def get_fcc_console(self):
        return self.console



class efc_gui(efc):

    def __init__(self):
        efc.__init__(self)

        # add button to main window
        self.efc_button = self.create_button('📜', self.get_efc_sidewindow)
        self.layout_third_row.addWidget(self.efc_button, 2, 2)
        self.add_shortcut('e', self.get_efc_sidewindow)


    def get_efc_sidewindow(self):
        self.arrange_efc_window()
        self.switch_side_window(self.efc_layout, 'efc', 250 + self.LEFT)
        

    def arrange_efc_window(self):
        # Style
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = int(self.config['efc_button_font_size'])
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        self.textbox_width = 275
        self.textbox_height = 200
        self.buttons_height = 45

        # Elements
        self.efc_layout = widget.QGridLayout()
        self.efc_layout.addWidget(self.create_recommendations_list(), 0, 0)
        self.efc_layout.addWidget(self.create_load_efc_button(), 1, 0, 1, 1)

        # Fill List Widget
        [self.recommendation_list.addItem(str(r)) for r in self.get_recommendations()]


    def create_recommendations_list(self):
        self.recommendation_list = widget.QListWidget(self)
        self.recommendation_list.setFixedWidth(self.textbox_width)
        self.recommendation_list.setFont(self.button_font)
        self.recommendation_list.setStyleSheet(self.textbox_stylesheet)
        return self.recommendation_list


    def create_load_efc_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFixedWidth(self.textbox_width)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.setStyleSheet(self.button_style_sheet)
        self.load_button.clicked.connect(self.load_selected_efc)
        return self.load_button


    def load_selected_efc(self):
        selected_path = self.get_path_from_selected_file()
        self.initiate_flashcards(selected_path)
        self.del_side_window()



class load_gui(load):

    def __init__(self):
        load.__init__(self)

        # add button to main window
        self.load_button = self.create_button('Load', self.get_load_sidewindow)
        self.layout_third_row.addWidget(self.load_button, 2, 0)
        self.add_shortcut('l', self.get_load_sidewindow)
    

    def get_load_sidewindow(self):
        self.arrange_load_window()
        self.switch_side_window(self.load_layout, 'load', 250 + self.LEFT)


    def arrange_load_window(self):
        # Window Parameters
        self.buttons_height = 45
        self.textbox_width = 275

        # Style
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = int(self.config['efc_button_font_size'])
        self.button_font = QtGui.QFont(self.font, self.font_button_size)

        # Elements
        self.load_layout = widget.QGridLayout()
        self.load_layout.addWidget(self.get_flashcard_files_list(), 0, 0)
        self.load_layout.addWidget(self.create_load_button(), 1, 0, 1, 1)

        # Fill
        self.fill_flashcard_files_list()


    def get_flashcard_files_list(self):
        self.flashcard_files_qlist = widget.QListWidget(self)
        self.flashcard_files_qlist.setFixedWidth(self.textbox_width)
        self.flashcard_files_qlist.setFont(self.button_font)
        self.flashcard_files_qlist.setStyleSheet(self.textbox_stylesheet)
        return self.flashcard_files_qlist


    def fill_flashcard_files_list(self):
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_lng_files()]
        [self.flashcard_files_qlist.addItem(str(file).split('.')[0]) for file in self.get_rev_files()]

        
    def create_load_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFixedWidth(self.textbox_width)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.setStyleSheet(self.button_style_sheet)
        self.load_button.clicked.connect(self.load_selected_file)
        return self.load_button


    def load_selected_file(self):
        file_path = super().get_selected_file_path(self.flashcard_files_qlist)
        self.initiate_flashcards(file_path)



class mistakes_gui():
    # Used for showing cards that user guessed wrong
    # after the revision finishes
    # no logic module for this side window

    def __init__(self):
        self.add_shortcut('m', self.get_mistakes_sidewindow)
        self.score_button.clicked.connect(self.get_mistakes_sidewindow)

    
    def get_mistakes_sidewindow(self):
        self.arrange_mistakes_window()
        self.switch_side_window(self.mistakes_layout, 'mistakes', 400 + self.LEFT)


    def arrange_mistakes_window(self):
        # Style
        self.textbox_stylesheet = self.config['textbox_style_sheet']
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = int(self.config['efc_button_font_size'])
        self.button_font = QtGui.QFont(self.font, self.font_button_size)

        # Elements
        self.mistakes_layout = widget.QGridLayout()
        self.mistakes_layout.addWidget(self.create_mistakes_list_alternate_side(), 0, 0)
        self.mistakes_layout.addWidget(self.create_mistakes_list_default_side(), 0, 1)
        
        # Fill
        [self.mistakes_list_default_side.addItem(m[self.default_side]) for m in self.mistakes_list]
        [self.mistakes_list_alternate_side.addItem(m[1-self.default_side]) for m in self.mistakes_list]


    def create_mistakes_list_default_side(self):
        self.mistakes_list_default_side = widget.QListWidget(self)
        self.mistakes_list_default_side.setFont(self.button_font)
        self.mistakes_list_default_side.setStyleSheet(self.textbox_stylesheet)
        return self.mistakes_list_default_side
    

    def create_mistakes_list_alternate_side(self):
        self.mistakes_list_alternate_side = widget.QListWidget(self)
        self.mistakes_list_alternate_side.setFont(self.button_font)
        self.mistakes_list_alternate_side.setStyleSheet(self.textbox_stylesheet)
        return self.mistakes_list_alternate_side



class stats_gui(stats):

    def __init__(self):
        stats.__init__(self)
        self.stats_button = self.create_button('🎢', self.get_stats_sidewindow)
        self.layout_fourth_row.addWidget(self.stats_button, 3, 1)
        self.add_shortcut('s', self.get_stats_sidewindow)


    def arrange_stats_sidewindow(self):
        self.get_data_for_current_revision(self.signature)
        self.get_stats_chart()
        self.get_stats_table()
        self.stats_layout = widget.QGridLayout()
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stats_layout.addLayout(self.stat_table, 1, 0)
    

    def get_stats_sidewindow(self):
        if self.is_revision:
            self.arrange_stats_sidewindow()
            self.switch_side_window(self.stats_layout, 'stats', 400 + self.LEFT)
        else:
            print('Statistics not available for a Language')


    def get_stats_chart(self):
        self.figure = Figure(figsize=(5,2))
        self.canvas = FigureCanvas(self.figure)

        ax = self.figure.add_subplot()
        ax.bar(self.formatted_dates, self.chart_values, color=config['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center')

        # Labels - don't show if many records as labels become hazy
        if len(self.dynamic_chain_index) <= 12:
            for rect, label in zip(ax.patches, self.dynamic_chain_index):
                height = rect.get_height()
                ax.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                        color=self.config['stat_chart_text_color'])

        # Style
        self.figure.set_facecolor(self.config['stat_background_color'])
        ax.set_facecolor(self.config['stat_chart_background_color'])
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.set_ylim([0, self.total_words])
        ax.tick_params(colors=self.config['stat_chart_text_color'])
        self.figure.tight_layout(pad=0.1)
        # ax.get_yaxis().set_visible(False)

        self.canvas.draw()        


    def get_stats_table(self):
        self.stat_table = widget.QGridLayout()

        self.repeated_times_button = self.create_button(f'{" "*(len(str(self.sum_repeated))+1)}Repeated {self.sum_repeated} Time{"s" if int(self.sum_repeated) > 1 else ""}')
        self.days_from_last_rev = self.create_button(f'Last Rev {str(self.last_rev_days_ago).split(",")[0]} ago')
        self.days_from_creation = self.create_button(f'Created {str(self.days_ago).split(",")[0]} ago')
        
        self.stat_table.addWidget(self.repeated_times_button, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev, 0, 1)
        self.stat_table.addWidget(self.days_from_creation, 0, 2)



class progress_gui(stats):

    def __init__(self):
        stats.__init__(self)
        self.progress_button = self.create_button('🏆', self.get_progress_sidewindow)
        self.layout_fourth_row.addWidget(self.progress_button, 3, 2)
    

    def arrange_progress_sidewindow(self):
        self.get_data_for_progress(self.signature)
        self.get_progress_chart()
        self.progress_layout = widget.QGridLayout()
        self.progress_layout.addWidget(self.canvas, 0, 0)
    

    def get_progress_sidewindow(self):
        self.arrange_progress_sidewindow()
        self.switch_side_window(self.progress_layout, 'prog', 400 + self.LEFT)


    def get_progress_chart(self):
        
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

        # initiate plots
        total_words_plot = self.figure.add_subplot()
        total_words_plot.bar(self.formatted_dates, self.second_chart_values, color='#979dac', 
                edgecolor='#000000', linewidth=0.7, align='center', zorder=9)

        positives_plot = total_words_plot.twinx()
        positives_plot.bar(self.formatted_dates, self.chart_values, color=config['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center', zorder=0)

        revision_count_plot = total_words_plot.twinx()
        revision_count_plot.plot(self.formatted_dates, self.revision_count, color='#979dac', 
                linewidth=1, zorder=9)

        # add labels - last positives sum
        for rect, label in zip(positives_plot.patches, self.chart_values):
                height = rect.get_height()
                label = '' if label == 0 else "{:.0f}".format(label)
                positives_plot.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                        color=self.config['stat_chart_text_color'], zorder=10)

        # add labels - total sum
        unlearned = self.second_chart_values - self.chart_values 
        for rect, label in zip(total_words_plot.patches, unlearned):
            height = rect.get_height()
            x = rect.get_x() + rect.get_width()/2
            y = height-label/1.25
            label = '' if label == 0 else "{:.0f}".format(label)
            total_words_plot.text(x, y, label, ha="center", va="bottom", 
                    color=self.config['stat_chart_text_color'], zorder=10)
        
        # add labels - repeated times
        for x, y in zip(self.formatted_dates, self.revision_count):
            # xytext - distance between points and text label
            revision_count_plot.annotate("{:.0f}".format(y), (x, y), textcoords="offset points", xytext=(0,5), ha='center',
                        color=self.config['stat_chart_text_color'])
                      
        # Style
        self.figure.set_facecolor(self.config['stat_background_color'])
        total_words_plot.set_facecolor(self.config['stat_chart_background_color'])
        positives_plot.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        total_words_plot.tick_params(colors=self.config['stat_chart_text_color'])
        self.figure.tight_layout(pad=0.1)
        positives_plot.get_yaxis().set_visible(False)
        revision_count_plot.get_yaxis().set_visible(False)
        positives_plot.get_xaxis().set_visible(False)

        # synchronize axes
        max_ = max(self.chart_values.max(), self.second_chart_values.max())
        positives_plot.set_ylim([0, max_*1.2])
        total_words_plot.set_ylim([0, max_*1.2])
        revision_count_plot.set_ylim([0, max_*99])

        self.canvas.draw()        



class side_windows(fcc_gui, efc_gui, load_gui, 
                mistakes_gui, stats_gui, progress_gui):
    def __init__(self):
        fcc_gui.__init__(self)
        efc_gui.__init__(self)
        load_gui.__init__(self)
        mistakes_gui.__init__(self)
        stats_gui.__init__(self)
        progress_gui.__init__(self)