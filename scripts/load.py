from utils import *
import db_api


class load():
    # Displays side window with list of all available files
    
    def __init__(self):
        self.selected_file_name = None
        self.config = Config()
    

    def get_lng_files(self):
        self.lng_files_list = get_files_in_dir(self.config['lngs_path'])
        self.lng_files_list = filter_with_list(self.config['languages'], self.lng_files_list, case_sensitive=True)
        self.lng_files_list.sort(reverse=False)  
        return self.lng_files_list


    def get_rev_files(self):
        self.rev_files_list = get_files_in_dir(self.config['revs_path'])
        self.rev_files_list = filter_with_list(self.config['languages'], self.rev_files_list, case_sensitive=True)
        dbapi = db_api.db_interface()
        self.rev_files_list.sort(key=dbapi.get_first_date_by_filename, reverse=True)  
        return self.rev_files_list


    def get_selected_file_path(self, flashcard_files_qlist):
        
        selected_index = flashcard_files_qlist.currentRow()  
        if selected_index < 0: return # safety-check

        # Deterime if selected file is rev or lng by its position in the list
        if selected_index < len(self.lng_files_list):
            corresponing_path = self.config['lngs_path']
        else:
            corresponing_path = self.config['revs_path']

        concatenated_lists = self.lng_files_list + self.rev_files_list
        file_path = corresponing_path + concatenated_lists[selected_index]
        
        return file_path

