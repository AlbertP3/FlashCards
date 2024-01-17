from time import monotonic
import pandas as pd
from utils import *


config = Config()
pd.options.mode.chained_assignment = None
DBAPI_STATUS_DICT = dict()


def post_dbapi(text):
    caller_function = inspect.stack()[1].function
    DBAPI_STATUS_DICT[caller_function] = text


@singleton
class db_interface():
    # handles communication with DB
    # when error occurs it's mainly because signature not in db
    # in that case, return value that suggests revision was made
    # as long ago as possible e.g 1900-1-1, or was never revised

    def __init__(self):
        self.config = Config()
        self.DEFAULT_DATE = datetime(1900, 1, 1)
        self.db = pd.DataFrame()
        self.filters = dict(
            POS_NOT_ZERO = False,
            BY_LNG = False,
            BY_SIGNATURE = False, 
            EFC_MODEL = False,
        )
        self.last_update:float = 0
        self.last_load:float = -1


    def create_record(self, signature, words_total, positives, seconds_spent):
        timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        with open(self.config['db_path'], 'a') as fd:
            fd.write(';'.join([timestamp, signature, str(words_total), 
                                str(positives), str(seconds_spent)])+'\n')
        self.last_update = monotonic()
        post_dbapi(f'Recorded {signature}')
    

    def __reset_filters_flags(self):
        for key in self.filters.keys():
            self.filters[key] = False


    def __load_db(self):
        if self.last_load < self.last_update or any(self.filters): 
            self.db = pd.read_csv(self.config['db_path'], encoding='utf-8', sep=';')
            self.last_load = monotonic()
            return True


    def refresh(self):
        if self.__load_db():
            self.__reset_filters_flags()
            return True


    def filter_for_efc_model(self):
        # Remove mistakes, obsolete lngs and revs with POSITIVES=0
        filtered = pd.DataFrame(columns=self.db.columns)
        for lng in config['languages']:
            l_df = self.db.loc[self.db.iloc[:, 1].str.contains(lng)]
            l_df = l_df.loc[~l_df.iloc[:, 1].str.contains('_mistakes')]
            filtered = pd.concat([filtered, l_df], ignore_index=True, sort=False)
        self.db = filtered.loc[filtered['POSITIVES'] != 0]
        self.filters['EFC_MODEL'] = True


    def add_efc_metrics(self, fill_timespent=False):
        # expands db with efc metrics and returns a dict consisting of per signature data
        self.db['TIMESTAMP'] = pd.to_datetime(self.db['TIMESTAMP'], format="%m/%d/%Y, %H:%M:%S")

        sig = {k:list() for k in self.db['SIGNATURE'].unique()}
        initial_reps = int(config['init_revs_cnt'])
        if fill_timespent: avg_wpsec = self.db['TOTAL'].sum() / self.db.loc[self.db['SEC_SPENT'] > 0]['SEC_SPENT'].sum()
        else: avg_wpsec = 0
        rows_to_del = list()
        self.db['PREV_WPM'] = float(0)
        self.db['TIMEDELTA_SINCE_CREATION'] = 0
        self.db['TIMEDELTA_LAST_REV'] = 0
        self.db['CUM_CNT_REVS'] = 0
        self.db['PREV_SCORE'] = 0
        self.db['SCORE'] = 0

        for i, r in self.db.iterrows():
            s = r['SIGNATURE']
            # Tackle missing sec_spent
            if int(r['SEC_SPENT']) == 0: 
                if fill_timespent:
                    self.db.loc[i, 'SEC_SPENT'] = int(int(r['TOTAL'] / avg_wpsec))
                    r['SEC_SPENT'] = int(int(r['TOTAL'] / avg_wpsec))
                else:
                    rows_to_del.append(i)
                    continue
            # Skip initial repetitions
            sig[s].append((r['TIMESTAMP'], r['TOTAL'], r['POSITIVES'], r['SEC_SPENT']))
            if len(sig[s]) <= initial_reps:
                rows_to_del.append(i)
                continue
            # '-2' denotes previous revision
            self.db.loc[i, 'PREV_WPM'] = 60*sig[s][-2][1]/sig[s][-2][3]
            self.db.loc[i, 'CUM_CNT_REVS'] = len(sig[s])
            self.db.loc[i, 'TIMEDELTA_LAST_REV'] = int((sig[s][-1][0] - sig[s][-2][0]).total_seconds()/3600)
            self.db.loc[i, 'TIMEDELTA_SINCE_CREATION'] = int((sig[s][-1][0] - sig[s][0][0]).total_seconds()/3600)
            self.db.loc[i, 'PREV_SCORE'] = int(100*(sig[s][-2][2] / sig[s][-2][1]))
            self.db.loc[i, 'SCORE'] = int(100*sig[s][-1][2] / sig[s][-1][1])

        self.db = self.db.drop(index=rows_to_del, axis=0)
        self.filters['EFC_MODEL'] = True


    def remove_cols_for_efc_model(self):
        cols_to_remove = {'POSITIVES','TIMESTAMP','SIGNATURE','SEC_SPENT'}
        self.db = self.db.drop(cols_to_remove, axis=1)
        self.db = self.db.apply(pd.to_numeric, errors = 'coerce')
        self.filters['EFC_MODEL'] = True


    def gather_efc_record_data(self) -> dict:
        # Create a dictionary, mapping signatures to tuples of all matching revs
        self.db['TIMESTAMP'] = pd.to_datetime(self.db['TIMESTAMP'], format="%m/%d/%Y, %H:%M:%S")
        sig = {k:list() for k in self.db['SIGNATURE'].unique()}
        for i, r in self.db.iterrows():
            s = r['SIGNATURE']
            sig[s].append((r['TIMESTAMP'], r['TOTAL'], r['POSITIVES'], r['SEC_SPENT']))
        return sig


    def rename_signature(self, old_signature, new_signature):
        self.db['SIGNATURE'] = self.db['SIGNATURE'].replace(old_signature, new_signature)
        self.db.to_csv(self.config['db_path'], encoding='utf-8', sep=';', index=False)
        

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature=None):
        repeated_times = self.get_filtered_db_if('SIGNATURE', signature)
        repeated_times = repeated_times.count().iloc[0]-1
        repeated_times = 0 if repeated_times is None else repeated_times
        return repeated_times
    

    def get_total_time_spent_for_signature(self, signature=None):
        time_spent = self.get_filtered_db_if('SIGNATURE', signature)
        time_spent = time_spent['SEC_SPENT'].sum()
        time_spent = time_spent if time_spent is not None else 0
        return time_spent
    

    def get_last_score(self, signature=None):
        try:
            positives = self.get_last_positives(signature)
            total = self.get_total_words(signature)
            return positives/total
        except:
            return 0

    
    def get_filtered_db_if(self, col:str, condition=None):
        # returns filtered db if condtion is not None
        if condition is None: return self.db
        else: return self.db[self.db[col]==condition]


    def get_last_positives(self, signature=None, req_pos:bool=False):
        try:
            res = self.get_filtered_db_if('SIGNATURE', signature)
            if req_pos:
                for _, row in res.iloc[::-1].iterrows():
                    if row['POSITIVES'] != 0:
                        return row['POSITIVES']
            return res['POSITIVES'].iloc[-1]
        except:
            return 0


    def get_last_time_spent(self, signature=None, req_pos=False):
        try:
            res = self.get_filtered_db_if('SIGNATURE', signature)
            if req_pos:
                for _, row in res.iloc[::-1].iterrows():
                    if row['POSITIVES'] != 0:
                        return row['SEC_SPENT']
            return res['SEC_SPENT'].iloc[-1]
        except:
            return 0



    def get_total_words(self, signature=None):
        try:
            res = self.get_filtered_db_if('SIGNATURE', signature)
            return res['TOTAL'].iloc[-1]
        except:
            return 0


    def get_max_positives_count(self, signature=None):
        try:
            positives_list = self.get_filtered_db_if('SIGNATURE', signature)
            positives_list = positives_list['POSITIVES']
            return positives_list.max()
        except:
            return 0


    def get_first_datetime(self, signature=None):
        try:
            first_date = self.get_filtered_db_if('SIGNATURE', signature)
            first_date = first_date['TIMESTAMP'].iloc[0]
            return make_datetime(first_date)
        except:
            return self.DEFAULT_DATE
            

    def get_first_date_by_filename(self, filename_with_extension):
        first_date = self.get_first_datetime(filename_with_extension.split('.')[0])
        if first_date is not None:
            return first_date
        else:
            return self.DEFAULT_DATE


    def get_last_datetime(self, signature=None):
        try:
            last_date = self.get_filtered_db_if('SIGNATURE', signature)
            last_date = last_date['TIMESTAMP'].iloc[-1]
            return make_datetime(last_date)
        except:
            return self.DEFAULT_DATE


    def get_timedelta_from_creation(self, signature=None):
        try:
            first_date = self.get_first_datetime(signature)
            return datetime.now() - first_date
        except:
            return 0


    def get_timedelta_from_last_rev(self, signature=None):
        try:
            last_date = self.get_last_datetime(signature)
            return datetime.now() - last_date
        except:
            return 0


    def get_latest_record_signature(self, lng):
        # returns last record from db
        # optionally matching the lng provided
        # if NA - returns last record
        
        match = ''
        for i in range(self.db.shape[0]-1, -1, -1):
            if lng in self.db['SIGNATURE'].iloc[i]:
                match =  self.db['SIGNATURE'].iloc[i]
                break

        if match == '':
            post_dbapi('File Not Found')
        
        return match


    def get_count_of_records_missing_time(self, signature=None):
        res = self.get_filtered_db_if('SIGNATURE', signature)
        return res[self.db['SEC_SPENT']==0].shape[0]


    def get_chart_positives(self, signature=None):
        return self.__get_chart_data_deduplicated('POSITIVES', signature)


    def get_chart_dates(self, signature=None):
        return self.__get_chart_data_deduplicated('TIMESTAMP', signature)


    def get_chart_time_spent(self, signature=None):
        return self.__get_chart_data_deduplicated('SEC_SPENT', signature)
        

    def __get_chart_data_deduplicated(self, return_col_name, signature=None):
        # get data for each repetition - if more than 1 repetition 
        # occured on one day - retrieve result for the last one.
        res = self.get_filtered_db_if('SIGNATURE', signature)
        res = res[self.db['POSITIVES'] != 0]
        res['TIME'] = res['TIMESTAMP'].apply(lambda x: x[:10])
        res = res.drop_duplicates(subset=['TIME'], keep='last')
        return res[return_col_name].values.tolist()


    def get_filtered_by_lng(self, lngs:list):
        return self.__get_filtered_by_lng(lngs)


    def __get_filtered_by_lng(self, lngs:list):
        # filters out all not-matching lngs from the DB by SIGNATURE
        # contains can be used with regex
        if not isinstance(lngs, list): lngs = [lngs]  
        res = pd.DataFrame(columns=self.db.columns)
        for l in lngs:
            l_df = self.db.loc[self.db.iloc[:, 1].str.contains(l)]
            res = pd.concat([res, l_df], ignore_index=True, sort=False)
        return res


    def filter_where_positives_not_zero(self):
        # modifies self.db to contain only revision with POSITIVES != 0
        self.db = self.db.loc[self.db['POSITIVES'] != 0]
        self.filters['POS_NOT_ZERO'] = True


    def filter_where_signature_is_equal_to(self, signature):
        self.db = self.db.loc[self.db['SIGNATURE'] == signature]
        self.filters['BY_SIGNATURE'] = signature


    def filter_where_lng(self, lngs:list=[]):
        self.db = self.__get_filtered_by_lng(lngs)
        self.filters['BY_LNG'] = lngs

    
    def get_avg_cpm(self):
        return self.db['TOTAL'].sum() / ( self.db['SEC_SPENT'].sum() / 60 )
    

    def get_avg_score(self):
        return self.db['POSITIVES'].sum() / self.db['TOTAL'].sum()

    
    def get_all(self):
        return self.db
