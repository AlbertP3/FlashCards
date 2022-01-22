import db_api
import efc
import stats
import load
from PyQt5 import QtCore
from utils import *
from mistakes_dialog import Mistakes
import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt



class main_window_logic(widget.QWidget):

    def __init__(self):
        self.q_app = widget.QApplication([])
        super().__init__()
        validate_setup()

        # Flashcards parameters
        self.config = load_config()
        self.default_side = int(self.config['card_default_side'])
        self.file_path = self.config['onload_file_path']
        self.revmode = False

    
    def launch_app(self):   
        self.configure_window()
        self.build_layout()   
        self.optional_features()
        # Continue where you left off
        self.load_from_path(self.file_path)
        self.q_app.exec()

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
        self.next_button = self.create_button('Next', self.click_next)
        self.prev_button = self.create_button('Prev', self.click_prev)
        self.reverse_button = self.create_button('Reverse', self.reverse_side)
        self.load_button = self.create_button('Load', self.load_button_click)
        self.positive_button = self.create_button('✔️', self.click_positive)
        self.negative_button = self.create_button('❌', self.click_negative)
        self.score_button = self.create_button('<>', self.show_mistakes)
        self.settings_button = self.create_button('🎢', self.show_stats)
        self.save_button = self.create_button('Save', self.click_save)
        self.del_button = self.create_button('🗑', self.delete_card)
        self.load_again_button = self.create_button('⟳', self.load_again_click)
        self.revmode_button = self.create_button('RM:{}'.format('OFF'), self.change_revmode)
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
    

    def optional_features(self):
        if self.config['keyboard_shortcuts'].lower() in ['on','yes','true','1', 'y']:
            self.add_shortcuts()
        if 'switch_lng_rev' in self.config['optional'].split('|'):
            self.switch_lng_rev_button = self.create_button('🦙', self.switch_between_lng_and_rev)
            self.layout_third_row.addWidget(self.switch_lng_rev_button, 2, 4)

        
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


    def insert_text(self, text, default_font=16):
        dynamic_font_size = 32 - int(len(str(text))/24)
        self.FONT_TEXTBOX_SIZE = dynamic_font_size if dynamic_font_size >= 8 else default_font
        self.textbox.setFont(QtGui.QFont(self.FONT, self.FONT_TEXTBOX_SIZE))
        self.textbox.setText(str(text))
        padding = max(0, 90 - len(str(text))*0.7)
        self.textbox.setStyleSheet('''{} padding-top: {}%;'''.format(self.textbox_stylesheet, padding))
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def click_positive(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
        self.click_next()
    

    def click_negative(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
            self.mistakes_list.append([self.get_current_card(self.default_side), 
                                        self.get_current_card(1-self.default_side)])
        self.click_next()


    def click_next(self):
        diff_words = self.total_words - self.current_index - 1
        if diff_words >= 0:
            self.update_score()
            self.side = self.default_side
            self.append_current_index()
            self.insert_text(self.get_current_card())

            # Words Back Controls
            if self.words_back > 0:
                self.words_back-=1
                if self.words_back == 0 and self.revmode:
                        self.nav_buttons_visibility_control(True, True, False)

        # Revision Complete
        if diff_words == 0 and self.is_revision and self.is_saved == False:
            # message after revision is complete
            dbapi = db_api.db_interface()
            last_positives = dbapi.get_last_positives(self.signature)
            self.insert_text(self.get_rating_message(last_positives))
            # write record to db
            db_api.create_record(self.signature, self.total_words, self.positives)
            # update flashcards parameters
            self.is_saved = True
            self.change_revmode(force_mode=False)
            if self.negatives != 0:
                self.show_mistakes()


    def click_prev(self):
        if self.current_index >= 1:
            self.decrease_current_index()
            self.words_back+=1
            self.nav_buttons_visibility_control(False, False, True)
            self.side = self.default_side
            self.insert_text(self.get_current_card())


    def append_current_index(self):
        if self.current_index < self.total_words - 1:
            self.current_index += 1
            self.update_words_button()


    def decrease_current_index(self, value=1):
        if self.current_index >= value:
            self.current_index -= value
            self.update_words_button()


    def reverse_side(self):
        self.side = 1 - self.side
        self.insert_text(self.get_current_card())
     

    def load_again_click(self):
        self.load_from_path(self.file_path)


    def get_current_card(self, side=None):
        side = self.side if side is None else side
        return self.dataset.iloc[self.current_index, side]


    def delete_card(self):
        self.dataset.drop([self.current_index], inplace=True, axis=0)
        self.dataset.reset_index(inplace=True, drop=True)
        self.total_words = self.dataset.shape[0]
        self.update_words_button()
        self.side = self.default_side
        self.insert_text(self.get_current_card())


    def click_save(self):
        if self.is_revision:
            print('Cannot save a revision')
            return
        
        # get new revision filename            
        if 'custom_saveprefix' in self.config['optional']:
            self.signature = ask_user_for_custom_signature()
        else:
            self.signature = update_signature_timestamp(self.signature)

        save_new_revision(self.dataset.iloc[:self.current_index+1, :], self.signature)
        print('Saved Successfully')

        # Create initial record
        db_api.create_record(self.signature, self.current_index+1, self.positives)
        self.load_from_path(self.config['revs_path'] + '/' + self.signature + '.csv')


    def update_words_button(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))


    def update_score(self):
        total = self.positives + self.negatives
        if self.revmode and total != 0:
            score = round(100*self.positives / total, 0)
            self.score_button.setText('{}%'.format(int(score)))
        else:
            self.score_button.setText('<>')


    def change_revmode(self, force_mode='auto'):
        if self.is_revision:
            if force_mode == 'auto':
                self.revmode = not self.revmode
            else:
                self.revmode = force_mode
        else:
            self.revmode = False

        self.revmode_button.setText('RM:{}'.format('ON' if self.revmode else 'OFF'))

        if self.revmode:
            self.nav_buttons_visibility_control(True, True, False)
        else:
            self.nav_buttons_visibility_control(False, False, True)
            

    def load_button_click(self):
        self.load_window = load.Load_dialog(self)
        self.switch_side_window(self.load_window.get_load_layout(), 'load', 250 + self.LEFT)


    def load_from_path(self, path):
        try:
            data = load_dataset(path)
            if dataset_is_valid(data):
                self.update_main_window_parameters(path, data)
        except FileNotFoundError:
            print('File Not Found.')


    def update_main_window_parameters(self, file_path, data):
        file_path_parts = file_path.split('/')
        filename = file_path_parts[-1].split('.')[0]

        self.dataset = data
        self.is_revision = True if file_path_parts[-2] == self.config['revs_path'][2:] else False
        self.change_revmode(self.is_revision)
        self.signature = get_signature(filename, str(data.columns[0])[:2], self.is_revision)
        self.setWindowTitle(self.signature if self.is_revision else filename)
        self.del_side_window()
        self.reset_flashcard_parameters()
        update_config('onload_file_path', file_path)


    def reset_flashcard_parameters(self):
        self.current_index = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.mistakes_list = list()
        self.is_saved = False
        self.side = self.default_side
        self.total_words = self.dataset.shape[0]
        self.insert_text(self.get_current_card())
        self.update_words_button()
        self.update_score()


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
        add_shortcut('m', self.show_mistakes)


    def ks_nav_next(self):
        if self.revmode:
            self.click_positive()
        else:
            self.click_next()


    def ks_nav_negative(self):
        if self.revmode:
            self.click_negative()
        else:
            pass


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


    def get_rating_message(self, last_positives):
        rating = self.get_grade(self.positives, self.total_words)
        progress = self.get_progress(self.positives, last_positives, self.total_words)
        return rating + ' ' + progress

    
    def get_grade(self, positives, total_words):
        pos_share = positives / total_words
        if pos_share == 1:
            grade = 'Perfect!!!'
        elif pos_share >= 0.92:
            grade = 'Excellent!!'
        elif pos_share >= 0.8:
            grade = 'Awesome!'
        elif pos_share >= 0.68:
            grade = 'Good'
        else:
            grade = 'Try harder next time.'
        return grade


    def get_progress(self, positives, last_positives, total):
        delta_last_rev = positives - last_positives
        if positives == total:
            progress = 'You guessed everything right!'
        elif delta_last_rev > 0:
            progress = f'You guess right {delta_last_rev} cards more than last time'
        elif delta_last_rev == 0:
            progress = 'You guessed the exact same number of cards as last time.'
        else:
            progress = f'You guess right {delta_last_rev} cards less than last time'
        return progress


    def switch_between_lng_and_rev(self):
        if self.is_revision:
            # filename includes the extension
            matching_filename = get_most_similar_file(self.config['lngs_path'], 
                                get_lng_from_signature(self.signature), if_nothing_found='load_any')
            file_path = self.config['lngs_path'] + '/' + matching_filename
        else:
            db_interface = db_api.db_interface()
            last_rev_signature = db_interface.get_latest_record_signature(lng=self.dataset.columns[0])
            file_path = f"{self.config['revs_path']}/" + last_rev_signature + '.csv'
        self.load_from_path(file_path)                                                                          

    
    def switch_side_window(self, layout, name, extra_width):
        if self.side_window_id != name:
            self.del_side_window()
            self.add_side_window(layout, name, extra_width)
        else:
            self.del_side_window()
        self.move(self.pos())  # Keeps window at the same position
        

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


    def get_filepath(self):
        return self.file_path



if __name__ == '__main__':
    mw = main_window_logic()
    mw.launch_app()