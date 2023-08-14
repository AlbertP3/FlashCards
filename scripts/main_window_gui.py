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
        self.initiate_pace_timer()
        self.initiate_cyclic_file_update()
        self.initiate_flashcards(self.file_path)
        self.q_app.exec()

    def build_interface(self):
        self.configure_window()
        self.build_layout()   
        self.add_shortcuts()
        side_windows.__init__(self)


    def configure_window(self):
        # Window Parameters
        self.C_MG = 5  # Content Margin
        self.LEFT = 10
        self.TOP = 10
        self.TEXTBOX_HEIGHT = int(self.config['THEME']['textbox_height'])
        self.BUTTONS_HEIGHT = int(self.config['THEME']['buttons_height'])

        # Set Window Parameters
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '/icon.ico'))
        self.set_geometry(self.config['GEOMETRY']['main']) 

        # Initialize
        self.used_keybindings = set()
        self.create_ks_mapping()
        self.layout = None
        self.side_window_id:str = 'main'
        self.center_window()
        self.show()

    
    def create_ks_mapping(self):
        # create dict[window_id][nagivation]=dummy_function
        # for managing keybindings calls dependent on context of the current side_window
        self.nav_mapping = dict()
        sw_ids = {'main','load','efc','config','fcc','mistakes','stats','progress','timer'}
        for id in sw_ids:
            self.nav_mapping[id] = {k: lambda:'' for k in self.config['KEYBOARD_SHORTCUTS'].keys()} 


    def build_layout(self):
        # Layout & Style
        if self.layout is None:
            self.layout = widget.QGridLayout()
            self.setLayout(self.layout)
        # left, top, right, bottom
        self.layout.setContentsMargins(self.C_MG,self.C_MG,self.C_MG,self.C_MG)
        self.FONT = self.config['THEME']['font']
        self.FONT_BUTTON_SIZE = int(self.config['THEME']['font_button_size'])
        self.FONT_TEXTBOX_SIZE = int(self.config['THEME']['font_textbox_size'])
        self.TEXTBOX_FONT = QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE)
        self.BUTTON_FONT = QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE)

        # Organize Layout
        self.setStyleSheet(self.config['THEME']['main_style_sheet'])
        self.textbox_stylesheet = self.config['THEME']['textbox_style_sheet']
        self.button_style_sheet = self.config['THEME']['button_style_sheet']

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
        self.revmode_button = self.create_button('RM:{}'.format('OFF'), lambda: self.change_revmode(None))
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


    def update_default_side(self):
        super().update_default_side()

    
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
            if self.mistakes_list[self.auto_cfm_offset:]:
                self.save_to_mistakes_list()
            else:
                self.post_logic('No mistakes to save')
        else:
            if self.cards_seen != 0:
                super().handle_saving(seconds_spent=self.seconds_spent)
                self.update_interface_parameters()
            else:
                self.post_logic('Unable to save an empty file')
                

    def delete_current_card(self):
        super().delete_current_card()
        self.update_words_button()
        self.display_text(self.get_current_card()[self.side])


    def reverse_side(self):
        super().reverse_side()
        self.display_text(self.get_current_card()[self.side])
        if not self.TIMER_RUNNING_FLAG and not self.is_saved: 
            self.start_timer()
            if self.is_revision: self.start_pace_timer()


    def load_again_click(self):
        if self.dataset.empty:
            self.post_logic('Cannot reload an empty file')
            return
        elif self.TEMP_FILE_FLAG:
            dataset = shuffle_dataset(self.dataset)
        else:
            dataset = load_dataset(self.file_path)

        self.update_backend_parameters(self.file_path, dataset)
        self.update_interface_parameters()
        self.change_revmode(self.is_revision)
        self.start_file_update_timer()


    def initiate_flashcards(self, file_path):
        # Manage whole process of loading flashcards file
        dataset = super().load_flashcards(file_path)
        if dataset_is_valid(dataset):
            self.update_backend_parameters(file_path, dataset)
            self.update_interface_parameters()
            self.del_side_window()
            self.start_file_update_timer()


    def update_interface_parameters(self):
        filename = self.file_path.split('/')[-1].split('.')[0]
        self.window_title = self.signature if self.is_revision else filename
        self.setWindowTitle(self.window_title)
            
        self.display_text(self.get_current_card()[self.side])
        self.update_words_button()
        self.update_score_button()
        self.reset_timer(clear_indicator=True)
        self.reset_pace_timer(); self.stop_pace_timer()


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
            self.reset_pace_timer()
            if not self.TIMER_RUNNING_FLAG and not self.is_saved and not last_card_was_reached: 
                self.start_timer()
                if self.is_revision: self.start_pace_timer()
            elif conditions_to_stop_timer: 
                self.stop_timer(for_good=True)
                self.stop_pace_timer()
            self.update_score_button()
            if self.words_back_mode(): self.nav_buttons_visibility_control(True, True, False)
        elif self.is_complete_revision() and self.is_saved == False: 
            self.handle_revision_complete()
        elif self.conditions_to_save_time_for_mistakes_are_met(diff_words):
            self.save_revision()
        elif self.is_revision:
            self.display_text(self.revision_summary)
        else:
            self.stop_pace_timer()
            self.display_text("You have reached the world's edge, none but devils play past here")
        

    def save_revision(self):
        self.record_revision_to_db(self.seconds_spent)
        self.reset_timer()
        self.stop_pace_timer()
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
            self.update_score_button()
            self.revision_summary = self.get_rating_message()
            self.display_text(self.revision_summary)
            self.record_revision_to_db(seconds_spent=self.seconds_spent)
        else:
            self.display_text()

        self.is_saved = True
        self.change_revmode()
        self.reset_timer(clear_indicator=False)
        self.stop_pace_timer()
        # if self.negatives != 0:
        #     self.get_mistakes_sidewindow()


    def add_shortcuts(self): 
        self.add_shortcut('next', self.ks_nav_next, 'main')
        self.add_shortcut('negative', self.ks_nav_negative, 'main')
        self.add_shortcut('prev', self.click_prev_button, 'main')
        self.add_shortcut('reverse', self.reverse_side, 'main')
        self.add_shortcut('change_revmode', self.change_revmode, 'main')
        self.add_shortcut('del_cur_card', self.delete_current_card, 'main')
        self.add_shortcut('load_again', self.load_again_click, 'main')
        self.add_shortcut('save', self.click_save_button, 'main')
        

    def add_shortcut(self, action:str, function, sw_id:str='main'):
        # binding twice on the same key breaks the shortcut permanently
        key = self.config['KEYBOARD_SHORTCUTS'][action]
        self.nav_mapping[sw_id][action] = function
        if key not in self.used_keybindings:
            self.used_keybindings.add(key)
            shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(lambda: self._exec_ks(action))


    def _exec_ks(self, action):
        self.nav_mapping[self.side_window_id][action]()


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
        self.setWindowTitle(self.side_window_titles[name])
        self.stop_timer()
        self.stop_pace_timer()
        

    def del_side_window(self):
        if 'side_by_side' in self.config['optional']:
            self.del_side_window_side_by_side()
        else:
            self.del_side_window_in_place()
        self.setWindowTitle(self.window_title)
        self.resume_timer()
        self.resume_pace_timer()


    def open_in_place(self, layout, name, extra_width):
        if self.side_window_id != name:
            if self.side_window_id != 'main': self.del_side_window_in_place()
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
        self.set_geometry(self.config['GEOMETRY'][name])
    
    def del_side_window_in_place(self):
        remove_layout(self.side_window_layout)
        self.toggle_primary_widgets_visibility(True)
        self.side_window_id = 'main'
        self.layout.setContentsMargins(self.C_MG,self.C_MG,self.C_MG, self.C_MG)
        self.set_geometry(self.config['GEOMETRY']['main'])


    def open_side_by_side(self, layout, name, extra_width):
        if self.side_window_id != name:
            if self.side_window_id != 'main': self.del_side_window_side_by_side()
            self.add_window_to_side(layout, name, extra_width)
        else:
            self.del_side_window_side_by_side()
        self.move(self.pos()) 

    def add_window_to_side(self, layout, name, extra_width):
        self.side_window_layout = layout
        self.side_window_id = name
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setFixedWidth(self.config['GEOMETRY']['main'][2]+extra_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
    
    def del_side_window_side_by_side(self): 
        remove_layout(self.side_window_layout)
        self.side_window_id = 'main'
        self.set_geometry(self.config['GEOMETRY']['main'])


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
            if self.side_window_id != 'main':
                self.del_side_window()
        elif event.key() == Qt.Key_Return:
            self.nav_mapping[self.side_window_id]['run_command']()


    def center_window(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def change_revmode(self, force_which=None):
        # Wrapper for main_window_logic.change_revmode. Beware of the MRO.
        super().change_revmode(force_which)

        if self.revmode:
            self.nav_buttons_visibility_control(True, True, False)
            self.revmode_button.setText('RM:ON')
        else:
            self.nav_buttons_visibility_control(False, False, True)
            self.revmode_button.setText('RM:OFF')
        
        if not self.is_revision and force_which is None:
            self.fcc_inst.post_fcc('Revision mode is unavailable for a Language.')


    def update_words_button(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))

    
    def update_score_button(self):
        total = self.positives + self.negatives
        if total != 0:
            score = round(100*self.positives / total, 0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def excepthook(self, exc_type, exc_value, exc_tb):
        err_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.notify_on_error(err_traceback, exc_value)


    def set_geometry(self, rect:tuple[int,int,int,int]):
        # Change widht and height only
        cur_geo = self.geometry().getRect()
        self.setGeometry(cur_geo[0], cur_geo[1], rect[2], rect[3])


    # =============== FILE UPDATE TIMER ================
    def initiate_cyclic_file_update(self):
        if self.config['file_update_interval']=='0':
            self.file_update_timer = None
        else:
            self.file_update_timer = QTimer()

    
    def start_file_update_timer(self):
        if not self.condition_to_run_file_update_timer(): return
        self.fcc_inst.post_fcc('File update timer: started')
        self.last_file_update_seconds_ago = 0
        self.file_update_timer.timeout.connect(self.file_update_timer_handler)
        self.file_update_timer.start(1000)    


    def file_update_timer_handler(self):
        self.last_file_update_seconds_ago+=1
        interval_sec = int(self.config['file_update_interval'])
        if interval_sec == 0 or self.TEMP_FILE_FLAG:
            self.file_update_timer.stop()
            self.fcc_inst.post_fcc('File update timer: stopped')
        elif interval_sec <= self.last_file_update_seconds_ago:
            mod_time = os.path.getmtime(self.file_path)
            if mod_time > self.last_modification_time:
                self.update_dataset()
                self.fcc_inst.post_fcc('Dataset refreshed')
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
        self.timer_prev_text = '⏲'
        self.revtimer_hide_timer = 'hide_timer' in self.config['optional']
        self.revtimer_show_cpm_timer = 'show_cpm_timer' in self.config['optional']
        self.set_append_seconds_spent_function()


    def start_timer(self):
        self.timer.start(1000)
        self.TIMER_RUNNING_FLAG = True
    
    def resume_timer(self):
        if self.conditions_to_resume_timer_are_met():
            self.timer_button.setText(self.timer_prev_text)
            self.start_timer()

    def conditions_to_resume_timer_are_met(self):
        if self.seconds_spent != 0 \
            and self.is_saved is False \
            and self.side_window_id == 'main':
            conditions_met = True
        else:
            conditions_met = False
        return conditions_met

    def stop_timer(self, for_good=False):
        self.timer.stop()
        self.TIMER_RUNNING_FLAG = False
        if not self.revtimer_hide_timer:
            self.timer_prev_text = self.timer_button.text()
            self.timer_button.setText('⏲' if for_good or not self.seconds_spent else '⏸')

    def reset_timer(self, clear_indicator=True):
        self.timer.stop()
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        if clear_indicator:
            self.timer_button.setText('⏲')

    def set_append_seconds_spent_function(self):
        self.timer = QTimer()
        if self.revtimer_hide_timer: self.append_seconds_spent = self._revtimer_func_hidden
        elif self.revtimer_show_cpm_timer: self.append_seconds_spent = self._revtimer_func_cpm
        else: self.append_seconds_spent = self._revtimer_func_time
        self.timer.timeout.connect(self.append_seconds_spent)

    def _revtimer_func_hidden(self):
        self.seconds_spent+=1
        self.timer_button.setText('⏲')
        
    def _revtimer_func_cpm(self):
        self.seconds_spent+=1
        cpm = self.cards_seen/(self.seconds_spent/60)
        self.timer_button.setText(f'{cpm:.0f}')

    def _revtimer_func_time(self):
        self.seconds_spent+=1
        interval = 'minute' if self.seconds_spent < 3600 else 'hour'
        self.timer_button.setText(format_seconds_to(self.seconds_spent, interval))


    ############### PACE TIMER ############### 
    def initiate_pace_timer(self):
        interval = int(self.config['pace_card_interval'])
        self.pace_spent = 0
        if interval > 0:
            self.pace_timer = QTimer()
            self.pace_timer_interval = interval
            self.start_pace_timer = self._start_pace_timer
            self.resume_pace_timer = self._resume_pace_timer
            self.stop_pace_timer = self._stop_pace_timer
            self.reset_pace_timer = self._reset_pace_timer
        else:
            self.pace_timer = None
            self.start_pace_timer = lambda: None
            self.resume_pace_timer = lambda: None
            self.stop_pace_timer = lambda: None
            self.reset_pace_timer = lambda: None

    def _start_pace_timer(self):
        self.pace_timer = QTimer()
        self.pace_timer.timeout.connect(self.pace_timer_func)
        self.pace_timer.start(1000)

    def pace_timer_func(self):
        if self.words_back > 0: return
        self.pace_spent+=1
        if self.pace_spent >= self.pace_timer_interval:
            self.click_negative()

    def _resume_pace_timer(self):
        if not self.is_revision or self.is_saved or self.cards_seen==0 \
            or self.side_window_id!='main': return
        self.start_pace_timer()
        
    def _stop_pace_timer(self):
        self.pace_timer.stop()

    def _reset_pace_timer(self):
        self.pace_spent = 0
        

    # default methods overrides
    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.FocusOut and type(source) == QtGui.QWindow:
            self.stop_timer()
            self.stop_pace_timer()
        if event.type() == QtCore.QEvent.FocusIn and type(source) == QtGui.QWindow:
            self.resume_timer()
            self.resume_pace_timer()
        return super(main_window_gui, self).eventFilter(source, event)


    def closeEvent(self, event):
        self.config.save()


    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self.config['GEOMETRY'][self.side_window_id] = self.geometry().getRect()
