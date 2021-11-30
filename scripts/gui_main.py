import db_api
import efc
from PyQt5 import QtCore
from utils import *
from mistakes_dialog import Mistakes
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
import close_dialog


def __launch_main_window():
    # keep a reference to the opened window, 
    # otherwise it goes out of scope and is garbage collected
    mw = main_window()
    mw.show()
    return mw



class main_window(widget.QWidget):
    # Everything user sees is a widget
    # self.load_button.clicked.connect(self.dummy_insert) <- func w/o args

    def __init__(self):

        # Configuration
        self.config = load_config()

        super().__init__()

        # Flashcards parameters
        self.revmode = False
        self.total_words = 0
        self.current_index = 0
        self.dataset = None
        self.side = self.config['card_default_side']
        self.positives = 0
        self.negatives = 0
        self.mistakes_list = list()
        self.words_back = 0
        self.file_path = self.config['onload_file_path']
        self.signature = ''
        self.is_saved = False
        self.is_revision = False

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 475
        self.height = 450
        self.textbox_height = 280
        self.buttons_height = 45

        # Set Parameters
        self.setWindowTitle('Lama Learning')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '\\icon.png'))
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.font = self.config['font']
        self.font_button_size = self.config['font_button_size']
        self.font_textbox_size = self.config['font_textbox_size']
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        
        # see all available styles
        # print(PyQt5.QtWidgets.QStyleFactory.keys())
        # self.setStyle(widget.QStyleFactory.create('WindowsXP'))

        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = (self.config['button_style_sheet'])

        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()
        self.layout_next_navigation = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        # Widgets
        self.layout_first_row.addWidget(self.create_textbox(), 0, 0)

        self.layout_second_row.addWidget(self.create_prev_button(), 0, 0)
        self.layout_second_row.addWidget(self.create_reverse_button(), 0, 1)
        self.layout_second_row.addLayout(self.layout_next_navigation, 0, 2)
        
        self.layout_next_navigation.addWidget(self.create_next_button(), 0, 0)
        self.layout_next_navigation.addWidget(self.create_negative_button(), 0, 0)
        self.layout_next_navigation.addWidget(self.create_positive_button(), 0, 1)
        self.negative_button.hide()
        self.positive_button.hide()
        
        self.layout_third_row.addWidget(self.create_load_button(), 2, 0)
        self.layout_third_row.addWidget(self.create_del_button(), 2, 1)
        self.layout_third_row.addWidget(self.create_efc_button(), 2, 2)
        self.layout_third_row.addWidget(self.create_save_button(), 2, 3)

        self.layout_fourth_row.addWidget(self.create_score_button(), 3, 0)
        self.layout_fourth_row.addWidget(self.create_settings_button(), 3, 1)
        self.layout_fourth_row.addWidget(self.create_load_again_button(), 3, 2)
        self.layout_fourth_row.addWidget(self.create_words_button(), 3, 3)
        self.layout_fourth_row.addWidget(self.create_revmode_button(), 3, 4)
        
        # Button functionality control
        self.add_buttons_functionality()
        if self.config['keyboard_shortcuts'].lower() in ['on','yes','true','1', 'y']:
            self.add_shortcuts()

        # Execute
        self.center()
        self.show()

        # Continue where you left off
        self.load_button_click(self.file_path)
    

    # Button Initialization Functions
    def create_textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox.setFixedHeight(self.textbox_height)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet(self.textbox_stylesheet)
        self.textbox.setAlignment(QtCore.Qt.Alignment(QtCore.Qt.AlignCenter))
        return self.textbox
    
    def create_load_button(self):
        self.load_button = widget.QPushButton(self)
        self.load_button.setMinimumHeight(self.buttons_height)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.clicked.connect(self.load_button_click)
        self.load_button.setStyleSheet(self.button_style_sheet)
        return self.load_button

    def create_prev_button(self):
        self.prev_button = widget.QPushButton(self)
        self.prev_button.setMinimumHeight(self.buttons_height)
        self.prev_button.setFont(self.button_font)
        self.prev_button.setText('Prev')
        self.prev_button.setStyleSheet(self.button_style_sheet)
        return self.prev_button

    def create_next_button(self):
        self.next_button = widget.QPushButton(self)
        self.next_button.setMinimumHeight(self.buttons_height)
        self.next_button.setFont(self.button_font)
        self.next_button.setText('Next')
        self.next_button.setStyleSheet(self.button_style_sheet)
        return self.next_button
    
    def create_positive_button(self):
        self.positive_button = widget.QPushButton(self)
        self.positive_button.setMinimumHeight(self.buttons_height)
        self.positive_button.setFont(self.button_font)
        self.positive_button.setText('✔️')
        self.positive_button.setStyleSheet(self.button_style_sheet)
        return self.positive_button

    def create_negative_button(self):
        self.negative_button = widget.QPushButton(self)
        self.negative_button.setMinimumHeight(self.buttons_height)
        self.negative_button.setFont(self.button_font)
        self.negative_button.setText('❌')
        self.negative_button.setStyleSheet(self.button_style_sheet)
        return self.negative_button

    def create_reverse_button(self):
        self.reverse_button = widget.QPushButton(self)
        self.reverse_button.setMinimumHeight(self.buttons_height)
        self.reverse_button.setFont(self.button_font)
        self.reverse_button.setText('Reverse')
        self.reverse_button.setStyleSheet(self.button_style_sheet)
        return self.reverse_button

    def create_score_button(self):
        self.score_button = widget.QPushButton(self)
        self.score_button.setMinimumHeight(self.buttons_height)
        self.score_button.setFont(self.button_font)
        self.score_button.setText('<>')
        self.score_button.setStyleSheet(self.button_style_sheet)
        return self.score_button

    def create_settings_button(self):
        self.settings_button = widget.QPushButton(self)
        self.settings_button.setMinimumHeight(self.buttons_height)
        self.settings_button.setFont(self.button_font)
        self.settings_button.setText('🎢')
        self.settings_button.setStyleSheet(self.button_style_sheet)
        return self.settings_button

    def create_save_button(self):
        self.save_button = widget.QPushButton(self)
        self.save_button.setMinimumHeight(self.buttons_height)
        self.save_button.setFont(self.button_font)
        self.save_button.setText('Save')
        self.save_button.clicked.connect(self.do_save)
        self.save_button.setStyleSheet(self.button_style_sheet)
        return self.save_button

    def create_del_button(self):
        self.del_button = widget.QPushButton(self)
        self.del_button.setMinimumHeight(self.buttons_height)
        self.del_button.setFont(self.button_font)
        self.del_button.setText('🗑')
        self.del_button.setStyleSheet(self.button_style_sheet)
        return self.del_button

    def create_load_again_button(self):
        self.load_again_button = widget.QPushButton(self)
        self.load_again_button.setMinimumHeight(self.buttons_height)
        self.load_again_button.setFont(self.button_font)
        self.load_again_button.setText('⟳')
        self.load_again_button.setStyleSheet(self.button_style_sheet)
        return self.load_again_button

    def create_revmode_button(self):
        self.revmode_button = widget.QPushButton(self)
        self.revmode_button.setMinimumHeight(self.buttons_height)
        self.revmode_button.setFont(self.button_font)
        self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))
        self.revmode_button.setStyleSheet(self.button_style_sheet)
        return self.revmode_button

    def create_efc_button(self):
        self.efc_button = widget.QPushButton(self)
        self.efc_button.setMinimumHeight(self.buttons_height)
        self.efc_button.setFont(self.button_font)
        self.efc_button.setText('📜')
        self.efc_button.setStyleSheet(self.button_style_sheet)
        self.efc_button.clicked.connect(self.show_efc)
        return self.efc_button

    def create_words_button(self):
        self.words_button = widget.QPushButton(self)
        self.words_button.setMinimumHeight(self.buttons_height)
        self.words_button.setFont(self.button_font)
        self.words_button.setStyleSheet(self.button_style_sheet)
        self.words_button.setText('-')
        return self.words_button

    # End of buttons initialization 

    # Navigation
    def append_current_index(self):
        if self.current_index < self.total_words - 1:
            self.current_index += 1
            self.update_words_button()


    def decrease_current_index(self, value=1):
        if self.current_index >= value:
            self.current_index -= value
            self.update_words_button()


    def positive_click(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
        self.click_next()
    

    def negative_click(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
            self.mistakes_list.append([self.get_current_card(self.config['card_default_side']), 
                                        self.get_current_card(1-self.config['card_default_side'])])
        self.click_next()


    def click_next(self):
        diff_words = self.total_words - self.current_index
        if diff_words > 0:
            self.update_score()
            self.side = self.config['card_default_side']
            self.append_current_index()
            self.insert_text(self.get_current_card())

            # Words Back Controls
            if self.words_back > 0:
                self.words_back-=1
            if self.words_back == 0:
                if self.revmode:
                    self.visible(True, True, False)
                else:
                    self.visible(False, False, True)

        # Conditions to record revision - last card 
        if diff_words == 1 and self.signature[:4] == 'REV_' and self.is_saved == False:
            db_api.create_record(self.signature, self.total_words, self.positives)
            self.is_saved = True
            if self.revmode: self.change_revmode()
            self.insert_text('Done!')

            if self.negatives != 0:
                self.show_mistakes()


    def click_prev(self):
        if self.current_index > 1:
            self.decrease_current_index()
            self.words_back+=1
            self.visible(False, False, True)
            self.side = self.config['card_default_side']
            self.insert_text(self.get_current_card())


    def reverse_side(self):
        self.side = 1 - self.side
        self.insert_text(self.get_current_card())
     

    def load_again_click(self):
        self.dataset, self.file_path = load_dataset(self.file_path)
        self.reset_flashcard_parameters()


    def delete_card(self):
        if self.total_words > 1:
            card_to_del = self.dataset.iloc[self.current_index].values.tolist()
            self.dataset.drop([self.current_index], inplace=True, axis=0)
            print(f'Deleted Card: {card_to_del}')
            self.dataset.reset_index(inplace=True, drop=True)
            
            self.total_words = self.dataset.shape[0]
            self.update_words_button()
            self.side = self.config['card_default_side']
            self.insert_text(self.get_current_card())

        else:
            print('Unable to delete last card')


    def do_save(self):
        if not self.is_revision:
            save(self.dataset.iloc[:self.current_index+1, :], self.signature)
            # Create initial record
            db_api.create_record(self.signature, self.total_words, self.positives)
            self.load_button_click(self.config['revs_path'] + '\\' + self.signature + '.csv')
        else:
            print('Cannot save revision')


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())

    
    def insert_text(self, text, default_font=16):
        dynamic_font_size = 32 - int(len(str(text))/12)
        self.font_textbox_size = dynamic_font_size if dynamic_font_size >= 8 else default_font
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setText(str(text))
        padding = 90 - len(str(text))*0.6
        padding = max(0, padding)
        self.textbox.setStyleSheet('''{} 
                                    padding-top: {}%;'''.format(self.textbox_stylesheet, padding))
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def update_words_button(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))


    def get_current_card(self, side=None):
        side = self.side if side is None else side
        return self.dataset.iloc[self.current_index, side]


    def update_score(self):
        total = self.positives + self.negatives
        if self.revmode and total != 0:
            score = self.positives / (total)
            score = round(score*100,0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def change_revmode(self):
        
        # Disable changing to revision mode for lngs
        if not self.is_revision:
            return

        self.revmode = False if self.revmode else True
        self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))
        # show/hide buttons
        if self.revmode:
            self.visible(True, True, False)
        else:
            self.visible(False, False, True)
            

    def load_button_click(self, provided_file_path=None):

        # function loads provided path or asks user for a path
        try:
            if provided_file_path is False or provided_file_path is None:
                self.dataset, self.file_path = load_dataset()
            else:
                self.dataset, self.file_path = load_dataset(provided_file_path)
        except FileNotFoundError:
            print('File Not Found')
            return

        if self.file_path is not None:
            self.reset_flashcard_parameters()
            self.signature, self.is_revision = get_signature_and_isrevision(self.dataset.columns.tolist()[0], 
                                            get_filename_from_path(self.file_path, include_extension=False))
            # Update config file with new onload_path
            update_config('onload_file_path', get_relative_path_from_abs_path(self.file_path))


    def set_file_path(self, new_file_path):
        self.file_path = new_file_path


    def add_buttons_functionality(self):
        # Blocks buttons actions until a file is loaded (error prevetion)
        self.prev_button.clicked.connect(self.click_prev)
        self.next_button.clicked.connect(self.click_next)
        self.positive_button.clicked.connect(self.positive_click)
        self.negative_button.clicked.connect(self.negative_click)
        self.reverse_button.clicked.connect(self.reverse_side)
        self.settings_button.clicked.connect(self.show_stats)
        self.del_button.clicked.connect(self.delete_card)
        self.load_again_button.clicked.connect(self.load_again_click)
        self.revmode_button.clicked.connect(self.change_revmode)
        self.efc_button.clicked.connect(self.show_efc)


    def add_shortcuts(self):
        self.next_button_shortcut = widget.QShortcut(QtGui.QKeySequence('right'), self)
        self.next_button_shortcut.activated.connect(self.ks_nav_next)
        self.negative_button_shortcut = widget.QShortcut(QtGui.QKeySequence('down'), self)
        self.negative_button_shortcut.activated.connect(self.ks_nav_negative)
        self.prev_button_shortcut = widget.QShortcut(QtGui.QKeySequence('left'), self)
        self.prev_button_shortcut.activated.connect(self.click_prev)
        self.reverse_button_shortcut = widget.QShortcut(QtGui.QKeySequence('up'), self)
        self.reverse_button_shortcut.activated.connect(self.reverse_side)
        self.revmode_shortcut = widget.QShortcut(QtGui.QKeySequence('p'), self)
        self.revmode_shortcut.activated.connect(self.change_revmode)
        self.delete_click_shortcut = widget.QShortcut(QtGui.QKeySequence('d'), self)
        self.delete_click_shortcut.activated.connect(self.delete_card)
        self.efc_shortcut = widget.QShortcut(QtGui.QKeySequence('e'), self)
        self.efc_shortcut.activated.connect(self.show_efc)
        self.save_button_shortcut = widget.QShortcut(QtGui.QKeySequence('~'), self)
        self.save_button_shortcut.activated.connect(self.do_save)


    def ks_nav_next(self):
        if self.revmode:
            self.positive_click()
        else:
            self.click_next()


    def ks_nav_negative(self):
        if self.revmode:
            self.negative_click()
        else:
            pass


    def show_efc(self):
        self.efc_window = efc.EFC(self)
        self.efc_window.show()
        self.efc_window.move(self.pos().x()+int(self.width/2)-int(self.efc_window.width/2), 
                            self.pos().y() + int(self.height/5))

    def show_mistakes(self):
        self.mistakes_window = Mistakes(self.mistakes_list, self)
        self.mistakes_window.show()
        self.mistakes_window.move(self.pos().x()+int(self.width/2)-int(self.mistakes_window.width/2), 
                                self.pos().y() + int(self.height/5))


    def show_stats(self):
        if self.is_revision:
            db_interface = db_api.db_interface()
            db_interface.get_positives_chart(self.signature)
        else:
            print('Statistics not available')


    def visible(self, pos_button:bool, neg_button:bool, next_button:bool):
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


    def reset_flashcard_parameters(self):
        self.current_index = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.is_saved = False
        self.total_words = self.dataset.shape[0]
        self.insert_text(self.get_current_card())
        self.update_words_button()
        self.update_score()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_dialog = close_dialog.Close_dialog(self)
            self.close_dialog.show()


    

def launch():
    # [] or sys.argv represent cmd lines passed to the application
    app = widget.QApplication([])
    window = __launch_main_window()
    app.exec()
    return window


if __name__ == '__main__':
    window = launch()