import traceback
import sys
from PyQt5 import QtCore
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QTimer
from main_window_logic import main_window_logic
from side_windows_gui import *



class main_window_gui(widget.QWidget, main_window_logic, side_windows):

    def __init__(self):
        self.window_title = 'FlashCards'
        self.q_app = widget.QApplication([self.window_title])
        widget.QWidget.__init__(self)
        sys.excepthook = self.excepthook


    def launch_app(self):
        main_window_logic.__init__(self)
        self.build_interface()      
        self.initiate_timer()
        self.initiate_cyclic_file_update()
        self.set_qtextedit_console(self.get_fcc_console())
        self.initiate_flashcards(self.file_path)
        self.q_app.exec()


    def build_interface(self):
        self.configure_window()
        self.build_layout()   
        self.optional_features()
        side_windows.__init__(self)


    def configure_window(self):
        
        # Window Parameters
        self.C_MG = 5  # Content Margin
        self.LEFT = 10
        self.TOP = 10
        self.DEFAULT_WIDTH = int(self.config['default_width'])
        self.DEFAULT_HEIGHT = int(self.config['default_height'])
        self.TEXTBOX_HEIGHT = int(self.config['textbox_height'])
        self.BUTTONS_HEIGHT = int(self.config['buttons_height'])
        self.prev_width = self.DEFAULT_WIDTH
        self.prev_height = self.DEFAULT_HEIGHT

        # Set Window Parameters
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '/icon.ico'))
        self.setGeometry(self.LEFT, self.TOP, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        # Initialize
        self.used_keybindings = list()
        self.layout = None
        self.side_window_id = None
        self.center_window()
        self.show()


    def build_layout(self):
        # Layout & Style
        if self.layout is None:
            self.layout = widget.QGridLayout()
            self.setLayout(self.layout)
        self.layout.setContentsMargins(self.C_MG,self.C_MG,self.C_MG,self.C_MG)
        self.FONT = self.config['font']
        self.FONT_BUTTON_SIZE = int(self.config['font_button_size'])
        self.FONT_TEXTBOX_SIZE = int(self.config['font_textbox_size'])
        self.TEXTBOX_FONT = QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE)
        self.BUTTON_FONT = QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE)

        # Organize Layout
        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = self.config['textbox_style_sheet']
        self.button_style_sheet = self.config['button_style_sheet']

        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()
        self.layout_next_navigation = widget.QGridLayout()
        self.side_window_layout = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        # Buttons
        self.next_button = self.create_button('Next', self.click_next_button)
        self.prev_button = self.create_button('Prev', self.click_prev_button)
        self.reverse_button = self.create_button('Reverse', self.reverse_side)
        self.positive_button = self.create_button('✔️', self.click_positive)
        self.negative_button = self.create_button('❌', self.click_negative)
        self.score_button = self.create_button('<>')
        self.save_button = self.create_button('Save', self.click_save_button)
        self.del_button = self.create_button('🗑', self.delete_current_card)
        self.load_again_button = self.create_button('⟳', self.load_again_click)
        self.revmode_button = self.create_button('RM:{}'.format('OFF'), lambda: self.change_revmode('auto'))
        self.words_button = self.create_button('-')

        # Widgets
        self.layout_first_row.addWidget(self.create_textbox(), 0, 0)

        self.layout_second_row.addWidget(self.prev_button, 0, 0)
        self.layout_second_row.addWidget(self.reverse_button, 0, 1)
        self.layout_second_row.addLayout(self.layout_next_navigation, 0, 2)
        
        self.layout_next_navigation.addWidget(self.next_button, 0, 0)
        self.layout_next_navigation.addWidget(self.negative_button, 0, 0)
        self.layout_next_navigation.addWidget(self.positive_button, 0, 1)
        self.negative_button.hide()
        self.positive_button.hide()
        
        self.layout_third_row.addWidget(self.load_again_button, 2, 1)
        self.layout_third_row.addWidget(self.del_button, 2, 3)
        self.layout_third_row.addWidget(self.save_button, 2, 4)

        self.layout_fourth_row.addWidget(self.score_button, 3, 0)
        self.layout_fourth_row.addWidget(self.words_button, 3, 3)
        self.layout_fourth_row.addWidget(self.revmode_button, 3, 4)


    def set_theme(self):
        for i in get_children_layouts(self.layout):
            remove_layout(i)
        self.build_layout()
        self.initiate_timer()
        side_windows.__init__(self)
        self.display_text(self.get_current_card()[self.side])
        self.update_words_button()

    
    def create_textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox.setFont(self.TEXTBOX_FONT)
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet(self.textbox_stylesheet)
        self.textbox.setAlignment(QtCore.Qt.Alignment(QtCore.Qt.AlignCenter))
        return self.textbox


    def create_button(self, text, function=None):
        new_button = widget.QPushButton(self)
        new_button.setMinimumHeight(self.BUTTONS_HEIGHT)
        new_button.setFont(self.BUTTON_FONT)
        new_button.setText(text)
        new_button.setStyleSheet(self.button_style_sheet)
        if function is not None:
            new_button.clicked.connect(function)
        return new_button


    def display_text(self, text=None, forced_size=None):
        if not text: text = self.get_current_card()[self.side]
        if not forced_size:
            min_font_size = 18
            len_factor = int(len(str(text))/30)
            width_factor = int((self.frameGeometry().width())/43)
            self.FONT_TEXTBOX_SIZE = min_font_size + max(width_factor - len_factor,0)
        else:
            self.FONT_TEXTBOX_SIZE = forced_size
        self.textbox.setFont(QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE))
        self.textbox.setText(str(text))
        padding = max(0, 90 - len(str(text))*0.7)
        self.textbox.setStyleSheet('''{} padding-top: {}%;'''.format(self.textbox_stylesheet, padding))
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def click_save_button(self):
        if self.is_revision:
            self.save_revision()
        else:
            super().handle_saving(seconds_spent=self.seconds_spent)
            self.update_interface_parameters()
            self.reset_timer()


    def delete_current_card(self):
        super().delete_current_card()
        self.update_words_button()
        self.display_text(self.get_current_card()[self.side])


    def reverse_side(self):
        super().reverse_side()
        self.display_text(self.get_current_card()[self.side])
        if not self.TIMER_RUNNING_FLAG and not self.is_saved: 
            self.start_timer()


    def load_again_click(self):
        if not self.TEMP_FILE_FLAG:
            dataset = load_dataset(self.file_path)
        else:
            dataset = shuffle_dataset(self.dataset)
        self.update_backend_parameters(self.file_path, dataset)
        self.update_interface_parameters()
        self.reset_timer()
        self.start_file_update_timer()


    def initiate_flashcards(self, file_path):
        # Manage whole process of loading flashcards file
        dataset = super().load_flashcards(file_path)
        if dataset_is_valid(dataset):
            self.update_backend_parameters(file_path, dataset)
            self.update_interface_parameters()
            self.del_side_window()
            self.reset_timer()
            self.start_file_update_timer()


    def update_interface_parameters(self):
        filename = self.file_path.split('/')[-1].split('.')[0]
        self.window_title = self.signature if self.is_revision else filename
        self.setWindowTitle(self.window_title)
            
        self.display_text(self.get_current_card()[self.side])
        self.update_words_button()
        self.update_score_button()


    def append_current_index(self):
            super().append_current_index()
            self.update_words_button()

    
    def decrease_current_index(self, value=1):
        super().decrease_current_index(value)
        self.update_words_button()


    def click_prev_button(self):
        if self.current_index >= 1:
            super().goto_prev_card()
            self.nav_buttons_visibility_control(False, False, True)
            self.display_text(self.get_current_card()[self.side])


    def click_next_button(self):
        diff_words = self.total_words - self.current_index - 1
        if diff_words > 0:
            super().goto_next_card()
            self.display_text(self.get_current_card()[self.side])
            last_card_was_reached = self.cards_seen+1 == self.total_words
            conditions_to_stop_timer = last_card_was_reached and not self.is_revision and not self.is_mistakes_list
            if not self.TIMER_RUNNING_FLAG and not self.is_saved: self.start_timer()
            elif conditions_to_stop_timer: self.stop_timer()
            self.update_score_button()
            if self.words_back_mode(): self.nav_buttons_visibility_control(True, True, False)
        elif self.is_complete_revision() and self.is_saved == False: 
            self.handle_revision_complete()
        elif self.conditions_to_save_time_for_mistakes_are_met(diff_words):
            self.save_revision()
        elif self.is_revision:
            self.display_text(self.revision_summary)
        else:
            self.kill_timer()
            self.display_text("You have reached the world's edge, none but devils play past here")
        

    def save_revision(self):
        self.kill_timer()
        self.record_revision_to_db(self.seconds_spent)
        self.is_saved = True


    def conditions_to_save_time_for_mistakes_are_met(self, diff_words):
        if not self.is_revision and self.is_mistakes_list and \
            not self.is_saved and diff_words==0:
            return True
        else:
            return False


    def click_negative(self):
        super().result_negative()
        self.click_next_button()
    

    def click_positive(self):
        super().result_positive()
        self.click_next_button()


    def handle_revision_complete(self):

        if self.positives + self.negatives == self.total_words:
            self.revision_summary = self.get_rating_message()
            self.display_text(self.revision_summary)
            self.record_revision_to_db(seconds_spent=self.seconds_spent)
        else:
            self.display_text()

        self.change_revmode(force_mode=False)
        self.is_saved = True
        self.reset_timer(clear_indicator=False)

        if self.negatives != 0:
            self.get_mistakes_sidewindow()


    def add_shortcuts(self): 
        self.add_shortcut('right', self.ks_nav_next)
        self.add_shortcut('down', self.ks_nav_negative)
        self.add_shortcut('left', self.click_prev_button)
        self.add_shortcut('up', self.reverse_side)
        self.add_shortcut('p', self.change_revmode)
        self.add_shortcut('d', self.delete_current_card)
        self.add_shortcut('r', self.load_again_click)
        

    def add_shortcut(self, key:str, function):
        # binding twice on the same key breaks the shortcut permanently
        if key not in self.used_keybindings:
            shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(function)
            self.used_keybindings.append(key)


    def ks_nav_next(self):
        if self.revmode:
            self.click_positive()
        else:
            self.click_next_button()


    def ks_nav_negative(self):
        if self.revmode:
            self.click_negative()
        else:
            pass


    def nav_buttons_visibility_control(self, pos_button:bool, neg_button:bool, next_button:bool):
        if pos_button is True:
            self.positive_button.show()
        else:
            self.positive_button.hide()   
        if neg_button is True:
            self.negative_button.show()
        else:
            self.negative_button.hide()     
        if next_button is True:
            self.next_button.show()
        else:
            self.next_button.hide()


    def open_side_window(self, layout, name, extra_width):
        if 'side_by_side' in self.config['optional']:
            self.open_side_by_side(layout, name, extra_width)
        else:
            self.open_in_place(layout, name, extra_width)
        
    def del_side_window(self):
        if 'side_by_side' in self.config['optional']:
            self.del_side_window_side_by_side()
        else:
            self.del_side_window_in_place()


    def open_in_place(self, layout, name, extra_width):
        if self.side_window_id != name:
            if self.side_window_id: self.del_side_window_in_place()
            self.add_window_in_place(layout, name)
        else:
            self.del_side_window_in_place()
        self.move(self.pos()) 
    
    def add_window_in_place(self, layout, name):
        self.side_window_layout = layout
        self.toggle_primary_widgets_visibility(False)
        self.layout.addLayout(self.side_window_layout, 0, 1, 5, 1)
        self.layout.setContentsMargins(self.C_MG,self.C_MG,self.C_MG,self.C_MG)
        self.side_window_id = name
        self.stop_timer()
    
    def del_side_window_in_place(self):
        remove_layout(self.side_window_layout)
        self.toggle_primary_widgets_visibility(True)
        self.reset_window_size()
        self.layout.setContentsMargins(self.C_MG,self.C_MG,self.C_MG, self.C_MG)
        self.side_window_id = None
        self.resume_timer()


    def open_side_by_side(self, layout, name, extra_width):
        if self.side_window_id != name:
            if self.side_window_id: self.del_side_window_side_by_side()
            else: self.update_width_and_height()
            self.add_window_to_side(layout, name, extra_width)
        else:
            self.del_side_window_side_by_side()
        self.move(self.pos()) 

    def add_window_to_side(self, layout, name, extra_width):
        self.side_window_layout = layout
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setFixedWidth(self.prev_width+extra_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.side_window_id = name
        self.stop_timer()
    
    def del_side_window_side_by_side(self): 
        remove_layout(self.side_window_layout)
        self.reset_window_size()
        self.side_window_id = None
        self.resume_timer()


    def reset_window_size(self):
        self.setFixedWidth(self.prev_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.setFixedHeight(self.prev_height)
        self.setMinimumHeight(0)
        self.setMaximumHeight(widget.QWIDGETSIZE_MAX)


    def toggle_primary_widgets_visibility(self, target_mode):
        if target_mode:
            if not self.revmode or self.words_back or self.is_saved: 
                self.next_button.show()
            else:
                self.positive_button.show()
                self.negative_button.show()
            self.prev_button.show(); self.reverse_button.show(); self.score_button.show(); self.save_button.show()
            self.del_button.show(); self.load_again_button.show(); self.revmode_button.show(); self.words_button.show(); 
            self.textbox.show(); self.stats_button.show(); self.progress_button.show(); self.efc_button.show()
            self.config_button.show(); self.timer_button.show(); self.load_button.show()
        else:
            self.next_button.hide(); self.prev_button.hide(); self.reverse_button.hide(); self.positive_button.hide()
            self.negative_button.hide(); self.score_button.hide(); self.save_button.hide(); self.del_button.hide()
            self.load_again_button.hide(); self.revmode_button.hide(); self.words_button.hide(); self.textbox.hide()
            self.stats_button.hide(); self.progress_button.hide(); self.efc_button.hide(); self.config_button.hide()
            self.timer_button.hide(); self.load_button.hide()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.side_window_id is not None:
                self.del_side_window()


    def center_window(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def change_revmode(self, force_mode='auto'):
        if self.side_window_id: return

        super().change_revmode(force_mode)

        if not self.is_saved:
            self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))
        if self.revmode and not self.is_saved:
            self.nav_buttons_visibility_control(True, True, False)
        else:
            self.nav_buttons_visibility_control(False, False, True)
        
        if not self.is_revision and force_mode=='auto':
            # post only if action is performed by the user
            self.post_fcc('Revision mode is unavailable for a Language.')


    def update_words_button(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))

    
    def update_score_button(self):
        total = self.positives + self.negatives
        if total != 0:
            score = round(100*self.positives / total, 0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def optional_features(self):
        optional_features = self.config['optional']
        if 'keyboard_shortcuts' in optional_features:
            self.add_shortcuts()
        self.do_show_timer = 'hide_timer' not in optional_features
        

    def excepthook(self, exc_type, exc_value, exc_tb):
        err_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.log_add(err_traceback, exc_value)


    def update_width_and_height(self):
        self.prev_width = self.frameGeometry().width()
        # window changes height by 37 with every side window close. Why?
        self.prev_height = self.frameGeometry().height()-37


    # =============== FILE UPDATE TIMER ================
    def initiate_cyclic_file_update(self):
        if self.config['file_update_interval']=='0':
            self.file_update_timer = None
        else:
            self.file_update_timer = QTimer()

    
    def start_file_update_timer(self):
        if not self.condition_to_run_file_update_timer(): return
        self.post_fcc('File update timer: started')
        self.last_file_update_seconds_ago = 0
        self.file_update_timer.timeout.connect(self.file_update_timer_handler)
        self.file_update_timer.start(1000)    


    def file_update_timer_handler(self):
        self.last_file_update_seconds_ago+=1
        interval_sec = int(self.config['file_update_interval'])
        if interval_sec == 0 or self.TEMP_FILE_FLAG:
            self.file_update_timer.stop()
            self.post_fcc('File update timer: stopped')
        elif interval_sec <= self.last_file_update_seconds_ago:
            mod_time = os.path.getmtime(self.file_path)
            if mod_time > self.last_modification_time:
                self.update_dataset()
                self.post_fcc('Dataset refreshed')
            self.last_file_update_seconds_ago = 0
            self.last_modification_time = mod_time


    def condition_to_run_file_update_timer(self):
        c = self.file_update_timer is not None \
            and not self.TEMP_FILE_FLAG and \
            self.config['file_update_interval']!='0'
        return c


    def update_dataset(self):
            self.dataset = load_dataset(self.file_path, seed=self.config['pd_random_seed'])
            self.display_text(self.get_current_card()[self.side])


    #  ============= REVISION TIMER ==================
    def initiate_timer(self):
        self.q_app.installEventFilter(self)
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        self.timer=QTimer()
        self.timer.timeout.connect(self.append_seconds_spent)
        self.create_timer_button()

    def create_timer_button(self):
        self.timer_button = self.create_button('⏲', self.show_timespent_sidewindow)
        self.add_shortcut('t', self.show_timespent_sidewindow)
        self.layout_fourth_row.addWidget(self.timer_button, 3, 5)

    def start_timer(self):
        if not self.TIMER_KILLED_FLAG:
            self.timer.start(1000)
            self.TIMER_RUNNING_FLAG = True
    
    def resume_timer(self):
        if self.conditions_to_resume_timer_are_met():
            self.start_timer()

    def conditions_to_resume_timer_are_met(self):
        if self.seconds_spent != 0 \
            and self.is_saved is False \
            and self.side_window_id is None \
            and not self.TIMER_KILLED_FLAG:
            conditions_met = True
        else:
            conditions_met = False
        return conditions_met

    def stop_timer(self):
        self.timer.stop()
        self.TIMER_RUNNING_FLAG = False
        if not self.do_show_timer:
            self.timer_button.setText('⏹')

    def reset_timer(self, clear_indicator=True):
        self.timer.stop()
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        if clear_indicator:
            self.timer_button.setText('⏲')

    def kill_timer(self):
        self.stop_timer()
        self.TIMER_KILLED_FLAG = True
   
    def append_seconds_spent(self):
        self.seconds_spent+=1
        if self.do_show_timer:
            interval = 'minute' if self.seconds_spent < 3600 else 'hour'
            self.timer_button.setText(format_seconds_to(self.seconds_spent, interval))
        else:
            self.timer_button.setText('⏲')

    def get_seconds_spent(self):
        return self.seconds_spent

    def show_timespent_sidewindow(self):
        # displays time spent table utilizing FCC interface
        timespent_sidewindow_width = len(self.config['languages'])*120
        self.get_fcc_sidewindow(width_=timespent_sidewindow_width, read_only=True, show_history=False)
        self.execute_command(['tts', '12', 'm'], followup_prompt=False, save_to_log=False)


    # default methods overrides
    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.FocusOut and type(source) == QtGui.QWindow:
            self.stop_timer()
        if event.type() == QtCore.QEvent.FocusIn and type(source) == QtGui.QWindow:
            self.resume_timer()
        return super(main_window_gui, self).eventFilter(source, event)


    # def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
    #     if abs(self.frameGeometry().width() - self.prev_width) > 25:
    #         print('resize with condition')
