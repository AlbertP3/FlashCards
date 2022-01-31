from PyQt5 import QtCore
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from utils import * 
from main_window_logic import main_window_logic
import efc
import stats
import load
from mistakes_dialog import Mistakes



class main_window_gui(widget.QWidget, main_window_logic):

    def __init__(self):
        self.q_app = widget.QApplication([])
        widget.QWidget.__init__(self)
        main_window_logic.__init__(self)


    def launch_app(self):
        self.build_interface()
        self.initiate_flashcards(self.file_path)
        self.q_app.exec()


    def build_interface(self):   
        self.configure_window()
        self.build_layout()   
        self.optional_features()


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
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '/icon.png'))
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
        self.load_button = self.create_button('Load', self.click_load_button)
        self.positive_button = self.create_button('✔️', self.click_positive)
        self.negative_button = self.create_button('❌', self.click_negative)
        self.score_button = self.create_button('<>', self.show_mistakes)
        self.settings_button = self.create_button('🎢', self.show_stats)
        self.save_button = self.create_button('Save', self.click_save_button)
        self.del_button = self.create_button('🗑', self.delete_current_card)
        self.load_again_button = self.create_button('⟳', self.load_again_click)
        self.revmode_button = self.create_button('RM:{}'.format('OFF'), lambda: self.change_revmode('auto'))
        self.efc_button = self.create_button('📜', self.show_efc)
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
        
        self.layout_third_row.addWidget(self.load_button, 2, 0)
        self.layout_third_row.addWidget(self.del_button, 2, 1)
        self.layout_third_row.addWidget(self.efc_button, 2, 2)
        self.layout_third_row.addWidget(self.save_button, 2, 3)

        self.layout_fourth_row.addWidget(self.score_button, 3, 0)
        self.layout_fourth_row.addWidget(self.settings_button, 3, 1)
        self.layout_fourth_row.addWidget(self.load_again_button, 3, 2)
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


    def click_load_button(self):
        self.load_window = load.Load_dialog(self)
        self.switch_side_window(self.load_window.get_load_layout(), 'load', 250 + self.LEFT)


    def click_save_button(self):
        super().handle_saving()
        self.update_interface_parameters()


    def delete_current_card(self):
        super().delete_current_card()
        self.update_words_button()
        self.display_text(self.get_current_card()[self.side])


    def reverse_side(self):
        super().reverse_side()
        self.display_text(self.get_current_card()[self.side])


    def load_again_click(self):
        self.initiate_flashcards(self.file_path)


    def initiate_flashcards(self, file_path):
        # Manage whole process of loading flashcards file
        dataset = super().load_flashcards(file_path)
        if dataset_is_valid(dataset):
            self.update_backend_parameters(file_path, dataset)
            self.update_interface_parameters()


    def update_interface_parameters(self):
        filename = self.file_path.split('/')[-1].split('.')[0]
        self.setWindowTitle(self.signature if self.is_revision else filename)
        self.del_side_window()
        self.display_text(self.get_current_card()[self.side])
        self.update_words_button()


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
        if self.is_complete_revision():
            self.handle_revision_complete()
        else:    
            super().goto_next_card()
            self.display_text(self.get_current_card()[self.side])

        self.update_score_button()

        # modify buttons visibility when previous words are displayed
        if self.words_back_mode():
            self.nav_buttons_visibility_control(True, True, False)


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
        
        self.record_revision_to_db()
        self.change_revmode(force_mode=False)
        self.is_saved = True


    def add_shortcuts(self):
        def add_shortcut(key:str, function):
            shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(function)
        
        add_shortcut('right', self.ks_nav_next)
        add_shortcut('down', self.ks_nav_negative)
        add_shortcut('left', self.click_prev_button)
        add_shortcut('up', self.reverse_side)
        add_shortcut('p', self.change_revmode)
        add_shortcut('d', self.delete_current_card)
        add_shortcut('e', self.show_efc)
        add_shortcut('s', self.show_stats)
        add_shortcut('r', self.load_again_click)
        add_shortcut('l', self.click_load_button)
        add_shortcut('m', self.show_mistakes)
        add_shortcut('c', self.init_fcc)


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


    def show_efc(self):
        self.efc_window = efc.EFC(self)
        self.switch_side_window(self.efc_window.get_efc_layout(), 'efc', 250 + self.LEFT)
            

    def show_mistakes(self):
        if not self.is_revision: return
        self.mistakes_window = Mistakes(self.mistakes_list, self)
        self.switch_side_window(self.mistakes_window.get_mistakes_layout(), 'mistakes', 510 + self.LEFT)


    def show_stats(self):
        if self.is_revision:
            self.stats_window = stats.Stats(self)
            self.switch_side_window(self.stats_window.get_stats_layout(), 'stats', 400 + self.LEFT)
        else:
            print('Statistics not available for a Language')


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
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setFixedWidth(self.DEFAULT_WIDTH + extra_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.side_window_id = name


    def del_side_window(self):
        remove_layout(self.side_window_layout)
        self.setFixedWidth(self.DEFAULT_WIDTH)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        self.side_window_id = None


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


    def update_words_button(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))

    
    def update_score_button(self):
        total = self.positives + self.negatives
        if self.revmode and total != 0:
            score = round(100*self.positives / total, 0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def optional_features(self):
        if self.config['keyboard_shortcuts'].lower() in ['on','yes','true','1', 'y']:
            self.add_shortcuts()
        if 'switch_lng_rev' in self.config['optional'].split('|'):
            self.switch_lng_rev_button = self.create_button('🦙', self.switch_between_lng_and_rev)
            self.layout_third_row.addWidget(self.switch_lng_rev_button, 2, 4)



if __name__ == '__main__':
    mw = main_window_gui()
    mw.launch_app()