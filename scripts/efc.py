import db_api
from utils import *
from math import exp
from os import listdir

class efc():

    def __init__(self):
        self.config = Config()
        self.INITIAL_REPETITIONS = 2
        self.EFC_THRESHOLD = 0.8
        self.paths_to_suggested_lngs = dict()
        self.reccommendation_texts = {'EN':'Oi mate, take a gander', 
                                        'RU':'давай товарищ, двигаемся!', 
                                        'DE':'Es ist an der Zeit zu handeln!',
                                        'IT':'Andiamo a lavorare',
                                        'FR':'Mettons-nous au travail'}
        self.db_interface = db_api.db_interface()
        self.unique_signatures = set()

    def refresh_source_data(self):
        if self.db_interface.refresh():
            self.db_interface.filter_where_lng(lngs=self.config['languages'])
            self.unique_signatures = {s for s in self.db_interface.db['SIGNATURE'] 
                                    if s + '.csv' in listdir(self.config['revs_path'])}


    def efc_function(self, last_datetime, total_words, last_positives, repeated_times):
            # based on Ebbinghaus Forgetting Curve
            # function estimates the percentage of words in-memory for today

            diff_days_from_last = (make_todaytime() - last_datetime).total_seconds()/86400
            
            # employ forgetting curve
            pos_share = last_positives/total_words if total_words != 0 else 0
            x1, x2, x3, x4 = 2.039, -4.566, -12.495, -0.001
            s = (repeated_times**x1 + pos_share*x2) - (x3*exp(total_words*x4))
            initial_handicap = self.get_initial_handicap(repeated_times, diff_days_from_last)
            efc = exp(-diff_days_from_last/s) + initial_handicap

            return efc


    def get_initial_handicap(self, repeated_times, diff_days_from_last):
        # force daily revision for the first 3 days in min. 12h intervals
        if repeated_times==1: handicap = -0.21
        elif repeated_times <= int(self.config['initial_repetitions']) and diff_days_from_last>=0.5: handicap = -0.21
        else: handicap = 0
        return handicap


    def get_recommendations(self):
        reccommendations = list()

        if 'reccommend_new' in self.config['optional']:
            reccommendations.extend(self.is_it_time_for_something_new())

        # get parameters and efc_function result for each unique signature
        for rev in self.get_complete_efc_table():
            efc_critera_met = rev[-1] < self.EFC_THRESHOLD
            if efc_critera_met:
                reccommendations.append(rev[0])
        
        return reccommendations


    def get_complete_efc_table(self) -> list[str, str, float]:
        rev_table_data = list()

        for signature in self.unique_signatures:
            last_datetime = self.db_interface.get_last_datetime(signature)
            repeated_times = self.db_interface.get_sum_repeated(signature)
            total = self.db_interface.get_total_words(signature)
            last_positives = self.db_interface.get_last_positives(signature)
            efc = self.efc_function(last_datetime, total, last_positives, repeated_times)
            
            days_from_last_rev = (make_todaytime() - last_datetime).days
            rev_table_data.append([signature, days_from_last_rev, round(efc, 2)])

        return rev_table_data


    def get_efc_table_printout(self, efc_table_data):
        # sort revs by number of days ago since last revision
        efc_table_data.sort(key=lambda x: x[2])
        efc_stats_list = [['REV NAME', 'ΔD', 'EFC']]
        for rev in efc_table_data:
            efc_stats_list.append([rev[0], rev[1], rev[2]])
        printout = get_pretty_print(efc_stats_list, extra_indent=1, separator='|')
        return printout


    def get_path_from_selected_file(self):
        # safety-check if no item is selected
        if self.recommendation_list.currentItem() is None: return

        selected_li = self.recommendation_list.currentItem().text()
        try:
            # Check if selected item is a suggestion to create a new revision
            if selected_li in self.paths_to_suggested_lngs.keys():
                path = self.config['lngs_path'] + self.paths_to_suggested_lngs[selected_li]
            else:
                path = self.config['revs_path'] + str(selected_li) + '.csv'
                                     
        except FileNotFoundError:
            path = None
            print('Requested File Not Found')
    
        return path


    def is_it_time_for_something_new(self):
        # Periodically reccommend to create new revision for every lng
        lngs = self.config['languages']
        new_reccommendations = list()

        for lng in lngs:
            for signature in sorted(list(self.unique_signatures), key=self.db_interface.get_first_datetime, reverse=True):  
                if lng in signature:
                    initial_date = self.db_interface.get_first_datetime(signature)
                    time_delta = (make_todaytime() - initial_date).days
                    if time_delta >= int(self.config['days_to_new_rev']):
                        new_reccommendations.append(self.get_reccommendation_text(lng))
                    break
        return new_reccommendations


    def get_reccommendation_text(self, lng):
        # adding key to the dictionary facilitates matching 
        # reccommendation text with the lng file

        # if lng message is specified else get default
        if lng in self.reccommendation_texts:
            text = self.reccommendation_texts[lng]  
        else:
            text = f"It's time for {lng}"     
        
        self.paths_to_suggested_lngs[text] = get_most_similar_file(config['lngs_path'], lng)
        return text
    
