import joblib
from random import choice
from datetime import datetime
import DBAC.api as api
from utils import *



class efc():
    # based on Ebbinghaus Forgetting Curve
    # function estimates the percentage of words in-memory for today

    def __init__(self):
        self.config = Config()
        self.paths_to_suggested_lngs = dict()
        self.db = api.db_interface()
        self.efc_model = Placeholder()
        self.efc_model.name = None
        self.efc_model.mtime = 0
        self.load_pickled_model()


    def load_pickled_model(self):
        new_model:str = self.config['efc_model']
        new_model_path = os.path.join(self.config['resources_path'],'efc_models', f'{new_model}.pkl')
        new_model_mtime = os.path.getmtime(new_model_path)
        if new_model != self.efc_model.name or self.efc_model.mtime < new_model_mtime:
            self.efc_model = joblib.load(new_model_path)
            self.efc_model.mtime = new_model_mtime


    def get_recommendations(self):
        recommendations = list()
        self.new_revs = 0
        if self.config['days_to_new_rev']>0:
            recommendations.extend(self.is_it_time_for_something_new())
        for rev in self.get_complete_efc_table():
            efc_critera_met = rev[2] < self.config['efc_threshold']
            if efc_critera_met:
                recommendations.append(rev[0]) 
        return recommendations


    def get_complete_efc_table(self, preds:bool=False) -> list[str, str, float]:
        rev_table_data = list()
        self.db.filter_for_efc_model()
        unqs = self.db.gather_efc_record_data()
        init_revs = self.config['init_revs_cnt']
        init_revs_inth = self.config['init_revs_inth']

        for fd in self.db.get_sorted_revisions():
            # data: (TIMESTAMP, TOTAL, POSITIVES, SEC_SPENT)
            data = unqs.get(fd.signature)
            if data:
                since_last_rev = (datetime.now()-data[-1][0]).total_seconds()/3600
                cnt = len(data)+1
                if cnt <= init_revs:
                    efc = [[0 if since_last_rev>=init_revs_inth else 100]]
                    pred = init_revs_inth - since_last_rev if since_last_rev<=init_revs_inth else 0
                else:
                    total = data[-1][1]
                    since_creation = (datetime.now()-data[0][0]).total_seconds()/3600
                    prev_wpm = 60*data[-1][1]/data[-1][3] if data[-1][3] != 0 else 0
                    prev_score = int(100*(data[-1][2] / data[-1][1]))
                    rec = [total, prev_wpm, since_creation, since_last_rev, cnt, prev_score]
                    efc = self.efc_model.predict([rec])
                    pred = self.guess_when_due(rec.copy(), warm_start=efc[0][0]) if preds else 0
                s_efc = [fd.signature, since_last_rev/24, efc[0][0], pred]
            else:
                s_efc = [fd.signature, 'inf', 0, 0]
            rev_table_data.append(s_efc)
            
        return rev_table_data
 

    def guess_when_due(self, record, resh=800, warm_start=1, max_cycles=100, prog_resh=1.1, t_tol=0.01):
        # returns #hours to efc falling below the threshold
        # resh - step resolution in hours
        # warm_start - initial efc value
        # prog_resh - factor for adjusting resh
        # t_tol - target diff tolerance in points
        efc_ = warm_start or 1
        t = self.config['efc_threshold']
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
                pred = format_seconds_to(rev[3]*3600, 'hour', rem=2, sep=':')
            elif abs(rev[3]) < 10000:
                pred = format_seconds_to(rev[3]*3600, 'day', rem=0)
            else:
                pred = "Too Long"
            diff_days = '{:.1f}'.format(rev[1]) if isinstance(rev[1], float) else rev[1]
            efc_stats_list.append([rev[0], diff_days, '{:.2f}'.format(rev[2]), pred])
        printout = get_pretty_print(efc_stats_list, extra_indent=1, separator='|', 
                    alingment=['^', '>', '>', '>'], keep_last_border=True)
        return printout


    def get_fd_from_selected_file(self):
        try:
            i = self.recommendation_list.currentItem().text()
            if self.recommendation_list.currentRow() >= self.new_revs:
                fd = [fd for fd in self.db.files.values() if fd.basename == i][0]
            else:  # Select New Recommendation
                fd = self.db.files[
                    self.paths_to_suggested_lngs[i]
                ]
        except AttributeError:  # if no item is selected
            fd = None
        return fd


    def is_it_time_for_something_new(self):
        # Periodically recommend to create new revision for every lng
        new_recommendations = list()
        for lng in self.config['languages']:
            for fd in self.db.get_sorted_revisions():  
                if fd.lng == lng:
                    time_delta = self.db.get_timedelta_from_creation(fd.signature)
                    if time_delta.days >= self.config['days_to_new_rev']:
                        new_recommendations.append(self.get_recommendation_text(lng))
                    break
        return new_recommendations


    def get_recommendation_text(self, lng:str):
        # adding key to the dictionary facilitates matching 
        # recommendation text with the lng file
        text = self.config['RECOMMENDATIONS'].get(lng, f"It's time for {lng}")
        self.paths_to_suggested_lngs[text] = choice(
            [fd.filepath for fd in self.db.files.values() if fd.lng == lng and fd.kind == 'language']
        )
        self.new_revs+=1
        return text
