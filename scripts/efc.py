import db_api
from utils import *
from os import listdir
import joblib



class efc():
    # based on Ebbinghaus Forgetting Curve
    # function estimates the percentage of words in-memory for today

    def __init__(self):
        self.config = Config()
        self.paths_to_suggested_lngs = dict()
        self.reccommendation_texts = {'EN':'Oi mate, take a gander', 
                                        'RU':'давай товарищ, двигаемся!', 
                                        'DE':'Es ist an der Zeit zu handeln!',
                                        'IT':'Andiamo a lavorare',
                                        'FR':'Mettons-nous au travail'}
        self.db_interface = db_api.db_interface()
        self.unique_signatures = set()
        self.efc_model = Placeholder()
        self.efc_model.name = None
        self.efc_model.mtime = 0


    def refresh_source_data(self):
        if self.db_interface.refresh():
            self.load_pickled_model()
            self.db_interface.filter_where_lng(lngs=self.config['languages'])
            self.unique_signatures = {s for s in self.db_interface.db['SIGNATURE'] 
                                    if s + '.csv' in listdir(self.config['revs_path'])}


    def load_pickled_model(self):
        new_model:str = self.config['efc_model']
        new_model_path = os.path.join(self.config['resources_path'],'efc_models', f'{new_model}.pkl')
        new_model_mtime = os.path.getmtime(new_model_path)
        if new_model != self.efc_model.name or self.efc_model.mtime < new_model_mtime:
            self.efc_model = joblib.load(new_model_path)
            self.efc_model.mtime = new_model_mtime


    def get_recommendations(self):
        reccommendations = list()

        if int(self.config['days_to_new_rev'])>0:
            reccommendations.extend(self.is_it_time_for_something_new())

        # get parameters and efc_function result for each unique signature
        for rev in self.get_complete_efc_table():
            efc_critera_met = rev[2] < int(self.config['efc_threshold'])
            if efc_critera_met:
                reccommendations.append(rev[0])
        
        return reccommendations


    def get_complete_efc_table(self, preds:bool=False) -> list[str, str, float]:
        rev_table_data = list()
        self.db_interface.filter_for_efc_model()
        unqs = self.db_interface.gather_efc_record_data()

        for s in self.unique_signatures:
            # data: (TIMESTAMP, TOTAL, POSITIVES, SEC_SPENT)
            data = unqs.get(s)
            if data:
                since_last_rev = (datetime.now()-data[-1][0]).total_seconds()/3600
                cnt = len(data)+1
                if cnt <= int(self.config['initial_repetitions']):
                    efc = [[0 if since_last_rev>=12 else 100]]
                    pred = 12 - since_last_rev if since_last_rev<=12 else 0
                else:
                    total = data[-1][1]
                    since_creation = (datetime.now()-data[0][0]).total_seconds()/3600
                    prev_wpm = 60*data[-1][1]/data[-1][3] if data[-1][3] != 0 else 0
                    prev_score = int(100*(data[-1][2] / data[-1][1]))
                    rec = [total, prev_wpm, since_creation, since_last_rev, cnt, prev_score]
                    efc = self.efc_model.predict([rec])
                    pred = self.guess_when_due(rec.copy(), warm_start=efc[0][0]) if preds else 0
                s_efc = [s, since_last_rev/24, efc[0][0], pred]
            else:
                s_efc = [s, 'inf', 0, 0]
            rev_table_data.append(s_efc)
            
        return rev_table_data
 

    def guess_when_due(self, record, resh=800, warm_start=1, max_cycles=100, prog_resh=1.1, t_tol=0.01):
        # returns #hours to efc falling below the threshold
        # resh - step resolution in hours
        # warm_start - initial efc value
        # prog_resh - factor for adjusting resh
        # t_tol - target diff tolerance in points
        efc_ = warm_start or 1
        t = int(self.config['efc_threshold'])
        init = record[3]
        cycles = 0
        while cycles < max_cycles:
            if efc_ > t + t_tol:
                record[3]+=resh
            elif efc_ < t - t_tol:
               record[3]-=resh
            else:
                break
            efc_ = self.efc_model.predict([record])[0][0]
            resh/=prog_resh
            cycles+=1
        return record[3]-init


    def get_efc_table_printout(self, efc_table_data, lim=None):
        # sort revs by number of days ago since last revision
        efc_table_data.sort(key=lambda x: x[3])
        if lim: efc_table_data=efc_table_data[:lim]
        efc_stats_list = [['REV NAME', 'AGO', 'EFC', 'DUE']]
        for rev in efc_table_data:
            if abs(rev[3]) < 48:
                pred = f"{format_seconds_to(rev[3]*3600, 'hour')}"
            elif abs(rev[3]) < 10000:
                pred = f"{format_seconds_to(rev[3]*3600, 'day', include_remainder=False)}"  
            else:
                pred = "Too Long"
            diff_days = '{:.1f}'.format(rev[1]) if isinstance(rev[1], float) else rev[1]
            efc_stats_list.append([rev[0], diff_days, '{:.2f}'.format(rev[2]), pred])
        printout = get_pretty_print(efc_stats_list, extra_indent=1, separator='|', 
                    alingment=['^', '>', '>', '>'], keep_last_border=True)
        return printout


    def get_path_from_selected_file(self):
        # safety-check if no item is selected
        if self.recommendation_list.currentItem() is None: return

        selected_li = self.recommendation_list.currentItem().text()
        try:
            # Check if selected item is a suggestion to create a new revision
            if selected_li in self.paths_to_suggested_lngs.keys():
                path = os.path.join(self.config['lngs_path'], self.paths_to_suggested_lngs[selected_li])
            else:
                path = os.path.join(self.config['revs_path'], f"{selected_li}.csv")
                                     
        except FileNotFoundError:
            path = None
    
        return path


    def is_it_time_for_something_new(self):
        # Periodically reccommend to create new revision for every lng
        lngs = self.config['languages']
        new_reccommendations = list()

        for lng in lngs:
            for signature in sorted(list(self.unique_signatures), key=self.db_interface.get_first_datetime, reverse=True):  
                if lng in signature:
                    initial_date = self.db_interface.get_first_datetime(signature)
                    time_delta = (datetime.now() - initial_date).days
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
        
        self.paths_to_suggested_lngs[text] = get_most_similar_file_regex(config['lngs_path'], lng)
        return text
    
