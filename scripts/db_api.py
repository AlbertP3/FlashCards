from time import monotonic
import pandas as pd
from utils import *


config = Config()
pd.options.mode.chained_assignment = None
REV_DB_PATH = config['db_path'] 
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
        self.DEFAULT_DATE = datetime(1900, 1, 1)
        self.db = pd.DataFrame()
        self.filters = dict(
            POS_NOT_ZERO = False,
            BY_LNG = False,
            BY_SIGNATURE = False, 
        )
        self.last_update:float = 0
        self.last_load:float = -1


    def create_record(self, signature, words_total, positives, seconds_spent):
        timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        with open(REV_DB_PATH, 'a') as fd:
            fd.write(';'.join([timestamp, signature, str(words_total), 
                                str(positives), str(seconds_spent)])+'\n')
        self.last_update = monotonic()
        post_dbapi(f'Recorded: {signature}|{positives}|{seconds_spent} @{str(timestamp)[-8:-3]}')
    

    def __reset_filters_flags(self):
        for key in self.filters.keys():
            self.filters[key] = False


    def __load_db(self):
        if self.last_load < self.last_update or any(self.filters): 
            self.db = pd.read_csv(REV_DB_PATH, encoding='utf-8', sep=';')
            self.last_load = monotonic()
            return True


    def refresh(self):
        if self.__load_db():
            self.__reset_filters_flags()
            return True


    def rename_signature(self, old_signature, new_signature):
        self.db = self.db.replace(old_signature, new_signature)
        self.db.to_csv(REV_DB_PATH, encoding='utf-8', sep=';', index=False)
        

    def get_unique_signatures(self):
        return self.db['SIGNATURE'].drop_duplicates()


    def get_sum_repeated(self, signature=None):
        repeated_times = self.get_filtered_db_if('SIGNATURE', signature)
        repeated_times = repeated_times.count()[0]
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
            today = make_todaytime()
            return today - first_date
        except:
            return 0


    def get_timedelta_from_last_rev(self, signature=None):
        try:
            last_date = self.get_last_datetime(signature)
            today = make_todaytime()
            return today - last_date
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
            res = res.append(l_df, ignore_index=True, sort=False)
        
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

    
    def get_all(self):
        return self.db
