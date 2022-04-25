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
        self.q_app = widget.QApplication([])
        widget.QWidget.__init__(self)
        sys.excepthook = self.excepthook


    def launch_app(self):
        main_window_logic.__init__(self)
        self.build_interface()
        
        self.initiate_timer()

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
        self.LEFT = 10
        self.TOP = 10
        self.DEFAULT_WIDTH = int(self.config['default_width'])
        self.DEFAULT_HEIGHT = int(self.config['default_height'])
        self.TEXTBOX_HEIGHT = int(self.config['textbox_height'])
        self.BUTTONS_HEIGHT = int(self.config['buttons_height'])

        # Set Window Parameters
        self.setWindowTitle('Lama Learning')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '/icon.ico'))
        self.setGeometry(self.LEFT, self.TOP, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # Initialize
        self.side_window_id = None
        self.center_window()
        self.show()


    def build_layout(self):
        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.FONT = self.config['font']
        self.FONT_BUTTON_SIZE = int(self.config['font_button_size'])
        self.FONT_TEXTBOX_SIZE = int(self.config['font_textbox_size'])
        self.TEXTBOX_FONT = QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE)
        self.BUTTON_FONT = QtGui.QFont(self.FONT, self.FONT_BUTTON_SIZE)

        # Organize Layout
        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = (self.config['button_style_sheet'])

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


    def display_text(self, text, default_font=16):
        dynamic_font_size = 32 - int(len(str(text))/24)
        self.FONT_TEXTBOX_SIZE = dynamic_font_size if dynamic_font_size >= 8 else default_font
        self.textbox.setFont(QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE))
        self.textbox.setText(str(text))
        padding = max(0, 90 - len(str(text))*0.7)
        self.textbox.setStyleSheet('''{} padding-top: {}%;'''.format(self.textbox_stylesheet, padding))
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def click_save_button(self):
        if self.is_revision:
            self.post_logic('Cannot save a revision')
            return

        super().handle_saving(seconds_spent=self.seconds_spent)
        self.update_interface_parameters()


    def delete_current_card(self):
        super().delete_current_card()
        self.update_words_button()
        self.display_text(self.get_current_card()[self.side])


    def reverse_side(self):
        super().reverse_side()
        self.display_text(self.get_current_card()[self.side])


    def load_again_click(self):
        dataset = self.dataset.sample(frac=1).reset_index(drop=True)
        self.update_backend_parameters(self.file_path, dataset)
        self.update_interface_parameters()



    def initiate_flashcards(self, file_path):
        # Manage whole process of loading flashcards file
        dataset = super().load_flashcards(file_path)
        if dataset_is_valid(dataset):
            self.update_backend_parameters(file_path, dataset)
            self.update_interface_parameters()
            self.reset_timer()


    def update_interface_parameters(self):
        filename = self.file_path.split('/')[-1].split('.')[0]
        self.setWindowTitle(self.signature if self.is_revision else filename)
        
        if self.side_window_id != 'fcc':
            # close side window if its not a console
            self.del_side_window()
            
        self.display_text(self.get_current_card()[self.side])
        self.update_words_button()
        self.update_score_button()
        self.reset_timer()


    def append_current_index(self):
        super().append_current_index()
        self.update_words_button()

    
    def decrease_current_index(self, value=1):
        super().decrease_current_index(value)
        self.update_words_button()


    def click_prev_button(self):
        super().goto_prev_card()
        self.nav_buttons_visibility_control(False, False, True)
        self.display_text(self.get_current_card()[self.side])


    def click_next_button(self):
        
        if not self.is_complete_revision():
            super().goto_next_card()
            self.display_text(self.get_current_card()[self.side])
            if not self.TIMER_RUNNING_FLAG and not self.is_saved: self.start_timer()
        else:
            # is_saved flag allows to save current cardset only once
            if self.is_saved == False:
                self.handle_revision_complete()

        self.update_score_button()

        # modify buttons visibility when previous words are displayed
        if self.words_back_mode():
            self.nav_buttons_visibility_control(True, True, False)
        
        # record lng to db if last word is reached (mistakes lists)
        diff_words = self.total_words - self.current_index - 1
        if not self.is_revision and not self.is_saved and diff_words == 0:
            self.stop_timer()
            self.record_revision_to_db(self.seconds_spent)
            self.is_saved = True


    def click_negative(self):
        super().result_negative()
        self.click_next_button()
    

    def click_positive(self):
        super().result_positive()
        self.click_next_button()


    def handle_revision_complete(self):
        if self.positives !=  0:
            self.display_text(self.get_rating_message())

        if self.negatives != 0:
            self.show_mistakes()
        
        self.record_revision_to_db(seconds_spent=self.seconds_spent)
        self.change_revmode(force_mode=False)
        self.is_saved = True
        self.reset_timer(clear_indicator=False)


    def show_mistakes(self):
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
        shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
        shortcut.activated.connect(function)


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


    def switch_side_window(self, layout, name, extra_width):
        if self.side_window_id != name:
            self.del_side_window()
            self.add_side_window(layout, name, extra_width)
        else:
            self.del_side_window()
        # Keep window at the same position            
        self.move(self.pos())  


    def add_side_window(self, layout, name, extra_width):
        self.side_window_layout = layout
        self.setFixedWidth(self.DEFAULT_WIDTH + extra_width)
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.side_window_id = name
        self.stop_timer()


    def del_side_window(self):
        remove_layout(self.side_window_layout)
        self.setFixedWidth(self.DEFAULT_WIDTH)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.side_window_id = None
        self.resume_timer()


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
        super().change_revmode(force_mode)
        self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))
        if self.revmode:
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
        

    def excepthook(self, exc_type, exc_value, exc_tb):
        err_traceback = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self.log_add(err_traceback, exc_value)


    #  ============= TIMER ==================
    def initiate_timer(self):
        self.q_app.installEventFilter(self)
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        self.timer=QTimer()
        self.timer.timeout.connect(self.append_seconds_spent)
        self.create_timer_button()

    def create_timer_button(self):
        self.timer_button = self.create_button('00:00')
        self.layout_fourth_row.addWidget(self.timer_button, 3, 5)

    def start_timer(self):
        self.timer.start(1000)
        self.TIMER_RUNNING_FLAG = True
    
    def resume_timer(self):
        if self.seconds_spent != 0 and not self.is_saved:
            self.start_timer()

    def stop_timer(self):
        self.timer.stop()
        self.TIMER_RUNNING_FLAG = False

    def reset_timer(self, clear_indicator=True):
        self.timer.stop()
        self.seconds_spent = 0
        self.TIMER_RUNNING_FLAG = False
        if clear_indicator:
            self.timer_button.setText('00:00')

    def append_seconds_spent(self):
        self.seconds_spent+=1
        self.timer_button.setText(datetime.fromtimestamp(self.seconds_spent).strftime('%M:%S'))

    def get_seconds_spent(self):
        return self.seconds_spent

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.FocusOut and type(source) == QtGui.QWindow:
            self.stop_timer()
        if event.type() == QtCore.QEvent.FocusIn and type(source) == QtGui.QWindow:
            self.resume_timer()
        return super(main_window_gui, self).eventFilter(source, event)