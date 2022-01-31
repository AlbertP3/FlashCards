import db_api
from utils import *
from fcc import fcc


class main_window_logic(fcc):

    def __init__(self):
        validate_setup()
        super().__init__()

        # Flashcards parameters
        self.config = load_config()
        self.default_side = int(self.config['card_default_side'])
        self.side = self.default_side
        self.file_path = self.config['onload_file_path']
        self.revmode = False
        self.cards_seen = 0


    def build_backend_only(self):
        data = self.load_flashcards(self.file_path)
        if dataset_is_valid(data):
            self.update_backend_parameters(self.file_path, data)


    def init_fcc(self):
        self.init_command_prompt()


    def result_positive(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.positives+=1
    

    def result_negative(self):
        if self.current_index + 1 <= self.total_words and self.words_back == 0:
            self.negatives+=1
            self.mistakes_list.append([self.get_current_card()[self.default_side], 
                                        self.get_current_card()[1-self.default_side]])
        

    def goto_next_card(self):
        diff_words = self.total_words - self.current_index - 1
        if diff_words >= 0:
            self.side = self.default_side
            self.append_current_index()


    def append_current_index(self):
        if self.current_index < self.total_words - 1:
            self.current_index += 1
            self.track_cards_seen()


    def track_cards_seen(self):
        if self.current_index > self.cards_seen:
            self.cards_seen = self.current_index


    def decrease_current_index(self, value=1):
        if self.current_index >= value:
            self.current_index -= value

            
    def words_back_mode(self):
        # used for managing visibility of buttons
        # occurs when user goes to previous cards
        wordback_mode = False
        if self.words_back > 0:
            self.words_back-=1
            if self.words_back == 0 and self.revmode:
                wordback_mode = True
        return wordback_mode


    def record_revision_to_db(self):
        db_api.create_record(self.signature, self.total_words, self.positives)


    def goto_prev_card(self):
        if self.current_index >= 1:
            self.decrease_current_index()
            self.words_back+=1    
            self.side = self.default_side
            

    def reverse_side(self):
        self.side = 1 - self.side
        
     
    def delete_current_card(self):
        self.dataset.drop([self.current_index], inplace=True, axis=0)
        self.dataset.reset_index(inplace=True, drop=True)
        self.total_words = self.dataset.shape[0]
        self.side = self.default_side
        

    def load_flashcards(self, file_path):
        try:
            self.TEMP_FILE_FLAG = False
            return load_dataset(file_path, do_shuffle=True)
        except FileNotFoundError:
            print('File Not Found.')


    def is_complete_revision(self):
        diff_words = self.total_words - self.current_index - 1
        return diff_words == 0 and self.is_revision and self.is_saved == False


    def handle_saving(self):
        # Check preconditions
        if self.is_revision:
            print('Cannot save a revision')
            return
        
        # get new revision filename            
        if 'custom_saveprefix' in self.config['optional']:
            self.signature = ask_user_for_custom_signature()
        else:
            self.signature = update_signature_timestamp(self.signature)

        save_success = save_revision(self.dataset.iloc[:self.cards_seen+1, :], self.signature)
        if save_success:
            print('Saved successfully')

        # Create initial record
        db_api.create_record(self.signature, self.cards_seen+1, self.positives)
        
        # immediately load the revision
        new_path = self.config['revs_path'] + self.signature + '.csv'
        data = self.load_flashcards(new_path)
        self.update_backend_parameters(new_path, data)


    def change_revmode(self, force_mode='auto'):
        if self.is_revision:
            if force_mode == 'auto':
                self.revmode = not self.revmode
            else:
                self.revmode = force_mode
        else:
            self.revmode = False

    
    def update_backend_parameters(self, file_path, data):

        # set updated values
        file_path_parts = file_path.split('/')
        filename = file_path_parts[-1].split('.')[0]
        dir_name = file_path_parts[-2]
        
        self.file_path = file_path
        self.dataset = data
        self.is_revision = True if dir_name == self.config['revs_path'][2:-1] else False
        self.change_revmode(self.is_revision)
        self.signature = get_signature(filename, str(data.columns[0])[:2], self.is_revision)
        print(f'{"Revision" if self.is_revision else "Language"} loaded: {filename}')
        update_config('onload_file_path', file_path)

        # reset flashcards parameters
        self.current_index = 0
        self.cards_seen = 0
        self.positives = 0
        self.negatives = 0
        self.words_back = 0
        self.mistakes_list = list()
        self.is_saved = False
        self.side = self.default_side
        self.total_words = self.dataset.shape[0]


    def get_rating_message(self):
        dbapi = db_api.db_interface()
        last_positives = dbapi.get_last_positives(self.signature)
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
        if last_positives in [0, None]:
            # revision not in DB
            prefix = 'Impressive' if positives/total >= 0.8 else 'Not bad'
            progress = f'{prefix} for a first try.'
        else:
            delta_last_rev = positives - last_positives
            suffix = '' if abs(delta_last_rev) == 1 else 's'
            if positives == total:
                progress = 'You guessed everything right!'
            elif delta_last_rev > 0:
                prefix = 'However, y' if positives / total < 0.68 else 'Y'
                progress = f'{prefix}ou guessed {delta_last_rev} card{suffix} more than last time'
            elif delta_last_rev == 0:
                progress = 'You guessed the exact same number of cards as last time'
            else:
                prefix = 'However, y' if positives / total >= 0.68 else 'Y'
                progress = f'{prefix}ou guessed {abs(delta_last_rev)} card{suffix} less than last time'
        return progress


    def switch_between_lng_and_rev(self):
        # go to last rev matching currently loaded LNG or go to best matching LNG file

        if self.is_revision:
            matching_filename_with_extension = get_most_similar_file(self.config['lngs_path'], 
                                get_lng_from_signature(self.signature), if_nothing_found='load_any')
            file_path = self.config['lngs_path'] + matching_filename_with_extension
        else:
            db_interface = db_api.db_interface()
            last_rev_signature = db_interface.get_latest_record_signature(lng=self.dataset.columns[0])
            file_path = f"{self.config['revs_path']}" + last_rev_signature + '.csv'
        self.load_flashcards(file_path)                                                                          


    def get_current_card(self):
        return self.dataset.iloc[self.current_index, :]

    def get_positives(self):
        return self.positives

    def get_total_words(self):
        return self.total_words

    def get_filepath(self):
        return self.file_path  

    def get_dataset(self):
        return self.dataset
    
    def get_current_side(self):
        return self.side
    
    def get_mistakes_list(self):
        return self.mistakes_list
    
    def get_headings(self):
        return self.dataset.columns
    
    def set_cards_seen(self, cards_seen):
        self.cards_seen = cards_seen