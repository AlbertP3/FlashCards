import db_api
import efc
from PyQt5 import QtCore
from utils import *
from mistakes_dialog import Mistakes
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
import stats
import load


class main_window(widget.QWidget):

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
        self.side_window_right = None  # 'efc', 'mistakes', 'stats', 'load'

        # Window Parameters
        self.left = 10
        self.top = 10
        self.default_width = 475
        self.default_height = 450
        self.textbox_height = 280
        self.buttons_height = 45

        # Set Parameters
        self.setWindowTitle('Lama Learning')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '\\icon.png'))
        self.setGeometry(self.left, self.top, self.default_width, self.default_height)

        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.font = self.config['font']
        self.font_button_size = self.config['font_button_size']
        self.font_textbox_size = self.config['font_textbox_size']
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        
        # Layout
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
        self.next_button = self.create_button('Next', self.click_next)
        self.prev_button = self.create_button('Prev', self.click_prev)
        self.reverse_button = self.create_button('Reverse', self.reverse_side)
        self.load_button = self.create_button('Load', self.load_button_click)
        self.positive_button = self.create_button('✔️', self.positive_click)
        self.negative_button = self.create_button('❌', self.negative_click)
        self.score_button = self.create_button('<>')
        self.settings_button = self.create_button('🎢', self.show_stats)
        self.save_button = self.create_button('Save', self.do_save)
        self.del_button = self.create_button('🗑', self.delete_card)
        self.load_again_button = self.create_button('⟳', self.load_again_click)
        self.revmode_button = self.create_button('RM:{}'.format('ON' if self.revmode else 'OFF'), self.change_revmode)
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
        
        # Button functionality control
        if self.config['keyboard_shortcuts'].lower() in ['on','yes','true','1', 'y']:
            self.add_shortcuts()

        # Experimental
        if 'switch_lng_rev' in self.config['experimental'].split('|'):
            # Switch between lng and rev
            self.switch_lng_rev_button = self.create_button('🦙', self.switch_lng_rev)
            self.layout_third_row.addWidget(self.switch_lng_rev_button, 2, 4)

        # Continue where you left off
        self.load_from_path(self.file_path)
        
        # Execute
        self.center()
        self.show()


    def create_textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setReadOnly(True)
        self.textbox.setStyleSheet(self.textbox_stylesheet)
        self.textbox.setAlignment(QtCore.Qt.Alignment(QtCore.Qt.AlignCenter))
        return self.textbox


    def create_button(self, text, function=None):
        new_button = widget.QPushButton(self)
        new_button.setMinimumHeight(self.buttons_height)
        new_button.setFont(self.button_font)
        new_button.setText(text)
        new_button.setStyleSheet(self.button_style_sheet)
        if function is not None:
            new_button.clicked.connect(function)
        return new_button


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

        # Check conditions to record revision
        if diff_words == 1 and self.is_revision and self.is_saved == False:
            db_api.create_record(self.signature, self.total_words, self.positives)
            self.is_saved = True
            self.insert_text(self.get_rating())
            self.change_revmode(force_mode=False)
            if self.negatives != 0:
                self.show_mistakes()


    def click_prev(self):
        if self.current_index >= 1:
            self.decrease_current_index()
            self.words_back+=1
            self.visible(False, False, True)
            self.side = self.config['card_default_side']
            self.insert_text(self.get_current_card())


    def reverse_side(self):
        self.side = 1 - self.side
        self.insert_text(self.get_current_card())
     

    def load_again_click(self):
        self.load_from_path(self.file_path)


    def delete_card(self):
        if self.total_words > 1:
            self.dataset.drop([self.current_index], inplace=True, axis=0)
            # card_to_del = self.dataset.iloc[self.current_index].values.tolist()
            # print(f'Deleted Card: {card_to_del}')
            self.dataset.reset_index(inplace=True, drop=True)
            
            self.total_words = self.dataset.shape[0]
            self.update_words_button()
            self.side = self.config['card_default_side']
            self.insert_text(self.get_current_card())
        else:
            print('Unable to delete last card')


    def do_save(self):
        if not self.is_revision:
            self.signature = self.signature[:6] + datetime.now().strftime('%m%d%Y%H%M%S')
            save(self.dataset.iloc[:self.current_index+1, :], self.signature)
            # Create initial record
            db_api.create_record(self.signature, self.current_index+1, self.positives)
            self.load_from_path(self.config['revs_path'] + '\\' + self.signature + '.csv')
        else:
            print('Cannot save revision')


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def insert_text(self, text, default_font=16):
        dynamic_font_size = 32 - int(len(str(text))/24)
        self.font_textbox_size = dynamic_font_size if dynamic_font_size >= 8 else default_font
        self.textbox.setFont(QtGui.QFont(self.font, self.font_textbox_size))
        self.textbox.setText(str(text))
        padding = max(0, 90 - len(str(text))*0.7)
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
            score = round(100*self.positives / total, 0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def change_revmode(self, force_mode=None):
        # Disable changing to revision mode for lngs
        if not self.is_revision:
            return

        if force_mode is None:
            self.revmode = False if self.revmode else True
        else:
            self.revmode = force_mode

        self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))
        # show/hide buttons
        if self.revmode:
            self.visible(True, True, False)
        else:
            self.visible(False, False, True)
            

    def load_button_click(self):
        self.load_layout = load.Load_dialog(self)
        self.switch_side_window(self.load_layout.get_load_layout(), 'load', 250 + self.left)


    def load_from_path(self, path):
        initial_load = load.Load_dialog(self)
        initial_load.load_file(path)


    def set_dataset(self, data):
        self.dataset = data
    def set_signature(self, signature):
        self.signature = signature
    def set_is_revision(self, is_revision):
        self.is_revision = is_revision
    def set_title(self, title):
        self.setWindowTitle(title)
    def set_file_path(self, file_path):
        self.file_path = file_path


    def add_shortcuts(self):
        def add_shortcut(key:str, function):
            shortcut = widget.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(function)

        add_shortcut('right', self.ks_nav_next)
        add_shortcut('down', self.ks_nav_negative)
        add_shortcut('left', self.click_prev)
        add_shortcut('up', self.reverse_side)
        add_shortcut('p', self.change_revmode)
        add_shortcut('d', self.delete_card)
        add_shortcut('e', self.show_efc)
        add_shortcut('s', self.show_stats)
        add_shortcut('r', self.load_again_click)
        add_shortcut('l', self.load_button_click)


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
        self.switch_side_window(self.efc_window.get_efc_layout(), 'efc', 250 + self.left)
            

    def show_mistakes(self):
        self.mistakes_window = Mistakes(self.mistakes_list, self)
        self.switch_side_window(self.mistakes_window.get_mistakes_layout(), 'mistakes', 510 + self.left)


    def show_stats(self):
        if self.is_revision:
            self.stats_window = stats.Stats(self)
            self.switch_side_window(self.stats_window.get_stats_layout(), 'stats', 400 + self.left)
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
        self.mistakes_list = list()
        self.is_saved = False
        self.side = self.config['card_default_side']
        self.total_words = self.dataset.shape[0]
        self.insert_text(self.get_current_card())
        self.update_words_button()
        self.update_score()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.side_window_right is not None:
                self.del_side_window()
    

    def get_rating(self):
        pos_share = self.positives / self.total_words

        if pos_share == 1:
            rating = 'Perfect!!!'
        elif pos_share >= 0.92:
            rating = 'Excellent!'
        elif pos_share >= 0.8:
            rating = 'Awesome'
        elif pos_share >= 0.68:
            rating = 'Good'
        else:
            rating = 'Try harder next time.'

        return rating


    def switch_lng_rev(self):
        if self.is_revision:
            # filename includes the extension
            matching_filename = get_most_similar_file(self.config['lngs_path'], self.signature[4:6], 
                                                                            nothing_found='load_any')
            file_path = self.config['lngs_path'] + '\\' + matching_filename
        else:
            db_interface = db_api.db_interface()
            last_rev_signature = db_interface.get_newest_record(lng=self.signature[4:6])
            file_path = '.\\revisions\\' + last_rev_signature + '.csv'
        self.load_button_click(provided_file_path=file_path)                                                                            

    
    def switch_side_window(self, layout, name, extra_width):
 
        if self.side_window_right != name:
            self.del_side_window()
            self.add_side_window(layout, name, extra_width)
        else:
            self.del_side_window()

        # Keeps window at the same position
        self.move(self.pos())
        

    def add_side_window(self, layout, name, extra_width):
        self.side_window_layout = layout
        self.layout.addLayout(self.side_window_layout, 0, 1, 4, 1)
        self.setFixedWidth(self.default_width + extra_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        # Todo resizable window
        self.side_window_right = name

    def del_side_window(self):
        remove_layout(self.side_window_layout)
        self.setFixedWidth(self.default_width)
        self.setMinimumWidth(0)
        self.setMaximumWidth(widget.QWIDGETSIZE_MAX)
        # Todo resizable window
        self.side_window_right = None



if __name__ == '__main__':
    app = widget.QApplication([])
    mw = main_window()
    mw.show()
    app.exec()