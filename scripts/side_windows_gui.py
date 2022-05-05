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
from checkable_combobox import CheckableComboBox

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


    def get_fcc_sidewindow(self, width_=500, read_only=False, show_history=True):
        self.arrange_fcc_window(read_only=read_only)
        self.switch_side_window(self.fcc_layout, 'fcc', width_ + self.LEFT)
        if show_history:
            self.console.setText(self.reload_logs())
        self.console.setFocus()
        self.move_cursor_to_end()
        
        
    def arrange_fcc_window(self, read_only=False):
        self.fcc_layout = widget.QGridLayout()
        self.fcc_layout.addWidget(self.create_console(read_only=read_only), 0, 0)

        
    def create_console(self, read_only=False):
        self.console = widget.QTextEdit(self)
        self.console.setFont(self.CONSOLE_FONT)
        self.console.setReadOnly(read_only)
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
        if self.is_revision:
            self.arrange_mistakes_window()
            self.switch_side_window(self.mistakes_layout, 'mistakes', 400 + self.LEFT)
        else:
            self.post_fcc('Mistakes are unavailable for a Language.')

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


    def get_stats_sidewindow(self):
        if self.is_revision:
            self.arrange_stats_sidewindow()
            self.switch_side_window(self.stats_layout, 'stats', 430)
        else:
            self.post_fcc('Statistics are not available for a Language')


    def arrange_stats_sidewindow(self):
        self.get_data_for_current_revision(self.signature)
        self.get_stats_chart()
        self.get_stats_table()
        self.stats_layout = widget.QGridLayout()
        self.stats_layout.addWidget(self.canvas, 0, 0)
        self.stats_layout.addLayout(self.stat_table, 1, 0)
    

    def get_stats_chart(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        ax = self.figure.add_subplot()
        ax.bar(self.formatted_dates, self.chart_values, color=config['stat_bar_color'], 
                edgecolor='#000000', linewidth=0.7, align='center')

        # Time spent for each revision
        time_spent_plot = ax.twinx()
        time_spent_plot.plot(self.formatted_dates, self.time_spent_minutes, color='#979dac', 
                linewidth=1, zorder=9)

        # Labels
        for rect, label in zip(ax.patches, self.dynamic_chain_index):
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()/2, height/2, label, ha="center", va="bottom", 
                    color=self.config['stat_chart_text_color'])

        # add labels - time spent
        for x, y in zip(self.formatted_dates, self.time_spent_minutes):
            # xytext - distance between points and text label
            time_spent_plot.annotate(y, (x, y), textcoords="offset points", xytext=(0,5), ha='center',
                        color=self.config['stat_chart_text_color'])

        # Style
        self.figure.set_facecolor(self.config['stat_background_color'])
        ax.set_facecolor(self.config['stat_chart_background_color'])
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.set_ylim([0, self.total_words])
        ax.tick_params(colors=self.config['stat_chart_text_color'],
                        labelrotation=0,
                        pad=1)
        self.figure.tight_layout(pad=0.1)
        ax.get_yaxis().set_visible(False)
        time_spent_plot.get_yaxis().set_visible(False)
        time_spent_plot.set_ylim([0, 999])
        self.figure.subplots_adjust(left=0.0, bottom=0.1, right=0.999, top=0.997)

        self.canvas.draw()        

    def get_stats_table(self):
        self.stat_table = widget.QGridLayout()

        self.repeated_times_button = self.create_button(f'{" "*(len(str(self.sum_repeated))+1)}Repeated {self.sum_repeated} time{"s" if int(self.sum_repeated) > 1 else ""}')
        self.days_from_last_rev = self.create_button(f'Last rev {str(self.last_rev_days_ago).split(",")[0]} ago')
        self.days_from_creation = self.create_button(f'Created {str(self.days_ago).split(",")[0]} ago')
        
        self.stat_table.addWidget(self.repeated_times_button, 0, 0)
        self.stat_table.addWidget(self.days_from_last_rev, 0, 1)
        self.stat_table.addWidget(self.days_from_creation, 0, 2)



class progress_gui(stats):

    def __init__(self):
        stats.__init__(self)
        self.progress_button = self.create_button('🏆', self.get_progress_sidewindow)
        self.layout_fourth_row.addWidget(self.progress_button, 3, 2)
        self.add_shortcut('h', self.get_progress_sidewindow)
    
    
    def get_progress_sidewindow(self, override_lng_gist=False):
        if override_lng_gist:
            # allows showing data for all lngs
            lng_gist = ''
        else:
            lng_gist = get_lng_from_signature(self.signature)

        self.arrange_progress_sidewindow(lng_gist)
        self.switch_side_window(self.progress_layout, 'prog', 400 + self.LEFT)


    def arrange_progress_sidewindow(self, lng_gist):
        self.get_data_for_progress(lng_gist)
        self.get_progress_chart(lng_gist)
        self.progress_layout = widget.QGridLayout()
        self.progress_layout.addWidget(self.canvas, 0, 0)


    def get_progress_chart(self, lng_gist):
        
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
            revision_count_plot.annotate("#{:.0f}".format(y), (x, y), textcoords="offset points", xytext=(0,5), ha='center',
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
        title = lng_gist if lng_gist != '' else 'ALL'
        self.figure.suptitle(title, fontsize=18, y=0.92)
        self.figure.subplots_adjust(left=0.0, bottom=0.06, right=0.997, top=0.997)

        # synchronize axes
        max_ = max(self.chart_values.max(), self.second_chart_values.max())
        positives_plot.set_ylim([0, max_*1.2])
        total_words_plot.set_ylim([0, max_*1.2])
        revision_count_plot.set_ylim([0, max_*99])

        self.canvas.draw()        



class config_gui():

    def __init__(self):
        self.config = load_config()
        self.config_button = self.create_button('⚙️', self.get_config_sidewindow)
        self.layout_third_row.addWidget(self.config_button, 2, 5)
        self.add_shortcut('q', self.get_config_sidewindow)

    
    def get_config_sidewindow(self):
        self.arrange_config_sidewindow()
        self.switch_side_window(self.config_layout, 'config', 350 + self.LEFT)


    def arrange_config_sidewindow(self):
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
        self.config_layout = widget.QGridLayout()
        self.fill_config_list()


    def fill_config_list(self):

        # initate labels and comboboxes
        self.confirm_and_close_button = self.create_button('Confirm Changes', self.del_config_side_window)
        self.card_default_combobox = self.create_config_combobox('card_default_side',['0','1','Random'])
        self.card_default_label = self.create_label('Card Default Side')
        self.lngs_checkablecombobox = self.create_config_checkable_combobox('languages', ['EN','RU','JP','DE','IT','FR'])
        self.lngs_label = self.create_label('Languages')
        self.days_to_new_rev_qlineedit = self.create_config_qlineedit('days_to_new_rev')
        self.days_to_new_rev_label = self.create_label('Days between Revs')
        self.optional_checkablecombobox = self.create_config_checkable_combobox('optional', ['reccommend_new','keyboard_shortcuts',])
        self.optional_label = self.create_label('Optional Features')
        self.revs_path_qline = self.create_config_qlineedit('revs_path')
        self.revs_path_label = self.create_label('Revs Path')
        self.lngs_path_qline = self.create_config_qlineedit('lngs_path')
        self.lngs_path_label = self.create_label('Lngs Path')

        # add widgets
        self.config_layout.addWidget(self.card_default_label, 0, 0)
        self.config_layout.addWidget(self.card_default_combobox, 0, 1)
        self.config_layout.addWidget(self.lngs_label, 1, 0)
        self.config_layout.addWidget(self.lngs_checkablecombobox, 1, 1)
        self.config_layout.addWidget(self.days_to_new_rev_label, 2, 0)
        self.config_layout.addWidget(self.days_to_new_rev_qlineedit, 2, 1)
        self.config_layout.addWidget(self.optional_label, 3, 0)
        self.config_layout.addWidget(self.optional_checkablecombobox, 3, 1)
        self.config_layout.addWidget(self.revs_path_label, 4, 0)
        self.config_layout.addWidget(self.revs_path_qline, 4, 1)
        self.config_layout.addWidget(self.lngs_path_label, 5, 0)
        self.config_layout.addWidget(self.lngs_path_qline, 5, 1)
        self.config_layout.addWidget(self.confirm_and_close_button, 8, 0, 1, 2)

        # blank spaces
        self.config_layout.addWidget(self.create_blank_widget(),6,0)
        self.config_layout.addWidget(self.create_blank_widget(),7,0)


    def create_config_combobox(self, key:str, content:list):
        combobox = widget.QComboBox(self)
        combobox.addItems(content)
        combobox.setCurrentText(self.config[key])
        combobox.setMinimumHeight(self.BUTTONS_HEIGHT)
        combobox.setFont(self.BUTTON_FONT)
        combobox.setStyleSheet(self.button_style_sheet)
        return combobox
    

    def create_config_checkable_combobox(self, key:str, content:list):
        checkable_cb = CheckableComboBox(self)
        for i in content:
            checkable_cb.addItem(i, is_checked= i in self.config[key])
        checkable_cb.setMinimumHeight(self.BUTTONS_HEIGHT)
        checkable_cb.setFont(self.BUTTON_FONT)
        checkable_cb.setStyleSheet(self.button_style_sheet)
        return checkable_cb


    def create_config_qlineedit(self, key:str):
        qlineedit = widget.QLineEdit(self)
        qlineedit.setText(self.config[key])
        qlineedit.setMinimumHeight(self.BUTTONS_HEIGHT)
        qlineedit.setFont(self.BUTTON_FONT)
        qlineedit.setStyleSheet(self.button_style_sheet)
        return qlineedit


    def create_label(self, text):
        label = widget.QLabel(self)
        label.setText(text)
        label.setMinimumHeight(self.BUTTONS_HEIGHT)
        label.setFont(self.BUTTON_FONT)
        label.setText(text)
        label.setStyleSheet(self.button_style_sheet)
        return label

    def create_blank_widget(self):
        blank = widget.QLabel(self)
        blank.setStyleSheet("border: 0px")
        blank.setMinimumHeight(self.BUTTONS_HEIGHT)
        return blank


    def del_config_side_window(self):
        modified_dict = dict()
        modified_dict['card_default_side'] = self.card_default_combobox.currentText()
        modified_dict['languages'] = '|'.join(self.lngs_checkablecombobox.currentData())
        modified_dict['days_to_new_rev'] = self.days_to_new_rev_qlineedit.text()
        modified_dict['optional'] = '|'.join(self.optional_checkablecombobox.currentData())
        modified_dict['revs_path'] = self.revs_path_qline.text()
        modified_dict['lngs_path'] = self.lngs_path_qline.text()

        update_config_bulk(modified_dict)
        self.del_side_window()

    

class side_windows(fcc_gui, efc_gui, load_gui, 
                mistakes_gui, stats_gui, progress_gui, config_gui):
    def __init__(self):
        fcc_gui.__init__(self)
        efc_gui.__init__(self)
        load_gui.__init__(self)
        mistakes_gui.__init__(self)
        stats_gui.__init__(self)
        progress_gui.__init__(self)
        config_gui.__init__(self)
