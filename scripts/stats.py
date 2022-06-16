from atexit import register
from utils import *
import db_api

class stats():

    def __init__(self):
        self.config = Config().get_instance()

    
    def get_data_for_current_revision(self, signature):
        db_interface = db_api.db_interface()
        db_interface.filter_where_signature_is_equal_to(signature)

        # get data
        self.chart_values = db_interface.get_chart_positives()
        self.chart_dates = db_interface.get_chart_dates()
        self.total_words = db_interface.get_total_words()
        self.total_seconds_spent = db_interface.get_total_time_spent_for_signature()
        self.time_spent_seconds = db_interface.get_chart_time_spent()
        self.missing_records_cnt = db_interface.get_count_of_records_missing_time()
        self.time_spent_minutes = [datetime.fromtimestamp(x).strftime('%M:%S') for x in self.time_spent_seconds]
        self.formatted_dates = [datetime.strftime(datetime.strptime(date, '%m/%d/%Y, %H:%M:%S'),'%d/%m\n%Y') for date in self.chart_dates]
        self.sum_repeated = int(db_interface.get_sum_repeated())
        self.days_ago = format_timedelta(db_interface.get_timedelta_from_creation())
        self.last_rev_days_ago = format_timedelta(db_interface.get_timedelta_from_last_rev())

        # Create Dynamic Chain Index
        self.dynamic_chain_index = [self.chart_values[0] if len(self.chart_values)>=1 else '']
        tight_format = '' if len(self.chart_values) < 9 else '\n'
        [self.dynamic_chain_index.append('{main_val}{tf}({sign_}{dynamic})'.format(
            main_val = self.chart_values[x],
            tf = tight_format,
            sign_ = get_sign(self.chart_values[x] -  self.chart_values[x-1], neg_sign=''), 
            dynamic = self.chart_values[x] - self.chart_values[x-1])) 
            for x in range(1, len( self.chart_values))]


    def get_data_for_progress(self, lng_gist, interval='monthly'):
        date_format_dict = {
            'monthly': '%m/%y',
            'daily': '%d/%m/%y',
        } 

        # get data
        db_interface = db_api.db_interface()

        # filter for specifc lng - CASE SENSITIVE!
        filtered_db = db_interface.get_filtered_by_lng(lng_gist)
        filtered_db = filtered_db[(filtered_db['POSITIVES'] != 0)]

        # format dates
        date_format = date_format_dict[interval]
        filtered_db['TIMESTAMP'] = pd.to_datetime(filtered_db['TIMESTAMP']).dt.strftime(date_format)
        unique_timestamps = filtered_db.drop_duplicates(subset=['TIMESTAMP'], keep='first', inplace=False)['TIMESTAMP'].to_frame()

        # transform data
        counted_db = filtered_db.groupby(filtered_db['TIMESTAMP'], as_index=False, sort=False).count()
        filtered_db.drop_duplicates(['SIGNATURE'], keep='first', inplace=True)
        filtered_db['LAST_POSITIVES'] = filtered_db['SIGNATURE'].apply(lambda x: db_interface.get_last_positives(x))
        grouped_db = filtered_db.groupby(filtered_db['TIMESTAMP'], as_index=False, sort=False).sum()

        # join dataframes
        grouped_db.set_index('TIMESTAMP', inplace=True)
        grouped_db = unique_timestamps.join(grouped_db, on='TIMESTAMP')
        grouped_db.fillna(0, inplace=True)

        # assign values
        self.chart_values = grouped_db['LAST_POSITIVES']
        self.second_chart_values = grouped_db['TOTAL']
        self.revision_count = counted_db['TOTAL']
        self.formatted_dates = grouped_db['TIMESTAMP']