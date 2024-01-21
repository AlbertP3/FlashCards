from utils import *
import DBAC.api as api



class stats():

    def __init__(self):
        self.config = Config()
        self.db = api.db_interface()

    def get_data_for_current_revision(self, signature):
        self.db.refresh()
        self.db.filter_where_signature_is_equal_to(signature)

        # get data
        self.chart_values = self.db.get_chart_positives()
        self.chart_dates = self.db.get_chart_dates()
        self.total_words = self.db.get_total_words()
        self.total_seconds_spent = self.db.get_total_time_spent_for_signature()
        self.time_spent_seconds = self.db.get_chart_time_spent()
        self.missing_records_cnt = self.db.get_count_of_records_missing_time()
        self.time_spent_minutes = [datetime.fromtimestamp(x).strftime('%M:%S') for x in self.time_spent_seconds]
        self.formatted_dates = [f"{date.year}-{date.month}-{date.day}" for date in self.chart_dates]
        self.sum_repeated = self.db.get_sum_repeated(self.db.active_file.signature)
        self.days_ago = format_timedelta(self.db.get_timedelta_from_creation(self.db.active_file.signature))
        self.last_rev_days_ago = format_timedelta(self.db.get_timedelta_from_last_rev(self.db.active_file.signature))

        # Create Dynamic Chain Index
        if 'show_percent_stats' in self.config['optional']:
            self.create_dynamic_chain_percentages(tight_format=True)
        else:
            self.create_dynamic_chain_values(tight_format=True)


    def create_dynamic_chain_values(self, tight_format:bool=True):
        self.dynamic_chain_index = [self.chart_values[0] if len(self.chart_values)>=1 else '']
        tight_format = '\n' if tight_format else ' '
        [self.dynamic_chain_index.append('{main_val}{tf}({sign_}{dynamic})'.format(
            main_val = self.chart_values[x],
            tf = tight_format,
            sign_ = get_sign(self.chart_values[x] -  self.chart_values[x-1], neg_sign=''), 
            dynamic = self.chart_values[x] - self.chart_values[x-1])) 
            for x in range(1, len( self.chart_values))]


    def create_dynamic_chain_percentages(self, tight_format:bool=True):
        self.dynamic_chain_index = ["{:.0%}".format(self.chart_values[0]/self.total_words) if len(self.chart_values)>=1 else '']
        tight_format = '\n' if tight_format else ' '
        [self.dynamic_chain_index.append('{main_val:.0%}{tf}{sign_}{dynamic:.0f}pp'.format(
            main_val = self.chart_values[x]/self.total_words,
            tf = tight_format,
            sign_ = get_sign(self.chart_values[x] -  self.chart_values[x-1], neg_sign=''), 
            dynamic = 100*(self.chart_values[x] - self.chart_values[x-1])/self.total_words)) 
            for x in range(1, len( self.chart_values))]


    def get_data_for_progress(self, lngs:set, interval='monthly'):
        date_format_dict = {
            'monthly': '%m/%y',
            'daily': '%d/%m/%y',
        } 

        self.db.refresh()

        # filter for specifc lng - CASE SENSITIVE!
        filtered_db = self.db.get_filtered_by_lng(lngs)
        filtered_db = filtered_db[(filtered_db['POSITIVES'] != 0)]
        if filtered_db.empty:
            raise ValueError

        # format dates
        date_format = date_format_dict[interval]
        filtered_db['TIMESTAMP'] = pd.to_datetime(filtered_db['TIMESTAMP']).dt.strftime(date_format)
        unique_timestamps = filtered_db.drop_duplicates(subset=['TIMESTAMP'], keep='first', inplace=False)['TIMESTAMP'].to_frame()

        # transform data
        counted_db = filtered_db.groupby(filtered_db['TIMESTAMP'], as_index=False, sort=False).count()
        filtered_db.drop_duplicates(['SIGNATURE'], keep='first', inplace=True)
        filtered_db['LAST_POSITIVES'] = filtered_db['SIGNATURE'].apply(lambda x: self.db.get_last_positives(x))
        filtered_db['TOTAL'] = filtered_db['TOTAL'].astype('Int64')
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
