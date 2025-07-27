from utils import *
from random import randint
from DBAC import db_conn
from cfg import config
from cfg import config


class SummaryGenerator:

    def __init__(self):
        pass

    def get_summary_text(self, positives, total, time_spent):
        db_conn.refresh()
        self.signature = db_conn.active_file.signature
        last_positives = db_conn.get_last_positives(
            self.signature, req_not_first=True
        )
        max_positives = db_conn.get_max_positives_count(self.signature)
        last_time_spent = db_conn.get_last_time_spent(
            self.signature, req_not_first=True
        )

        self.__setup_parameters()

        self.last_time_spent = last_time_spent
        self.score = positives / total
        self.diff = total - positives
        self.diff_last_record = positives - last_positives
        self.desc_diff_last_record = ["more", "less"][self.diff_last_record < 0]
        self.diff_to_record = max_positives - positives
        self.desc_diff_record = ["more", "less"][self.diff_to_record < 0]
        self.diff_time = time_spent - last_time_spent if self.last_time_spent else 0
        self.desc_diff_time = ["more", "less"][self.diff_time < 0]
        self.cpm_score = total / (time_spent / 60) if time_spent > 0 else 0
        self.last_cpm_score = (
            total / (last_time_spent / 60) if self.last_time_spent else 0
        )
        self.cpm_diff = self.cpm_score - self.last_cpm_score
        self.desc_cpm_diff = ["more", "less"][self.cpm_diff < 0]

        if last_positives in {0, None}:
            # revision not in DB
            progress = self.__get_summary_first_rev()
        elif self.diff_to_record < 0:
            # if a new record
            progress = self.__get_summary_new_record()
            progress += self.__get_summary_timespent()
        elif self.diff_to_record <= 2:
            # close to record
            progress = self.__get_summary_close_to_record()
            progress += self.__get_summary_timespent()
        elif self.diff <= 2:
            # close to max
            progress = self.__get_summary_close_to_max()
            progress += self.__get_summary_timespent()
        else:
            # standard cases
            progress = self.__get_summary_standard_case()
            progress += self.__get_summary_timespent()

        db_conn.refresh()
        return progress

    def __setup_parameters(self):
        db_conn.filter_where_lng([db_conn.active_file.lng])
        db_conn.filter_where_not_first()
        avg_cpm = db_conn.get_avg_cpm()
        avg_score = db_conn.get_avg_score()

        self.PERCENTAGE_IMPRESSIVE = avg_score * config["summary"]["astounding"]
        self.PERCENTAGE_MEDIOCRE = avg_score * config["summary"]["mediocre"]
        self.PERCENTAGE_BAD = avg_score * config["summary"]["awful"]
        self.CPM_ULTRA_FAST = avg_cpm * config["summary"]["astounding"]
        self.CPM_VERY_FAST = avg_cpm * config["summary"]["excellent"]
        self.CPM_PRETTY_FAST = avg_cpm * config["summary"]["impressive"]
        self.CPM_FAST = avg_cpm * config["summary"]["good"]
        self.CPM_MEDIUM = avg_cpm * config["summary"]["mediocre"]
        self.CPM_SLOW = avg_cpm * config["summary"]["bad"]
        self.CPM_ULTRA_SLOW = avg_cpm * config["summary"]["awful"]

    def __get_summary_first_rev(self):
        if self.score >= 0.8:
            prefix = "Impressive"
        elif self.score >= 0.6:
            prefix = "Not bad"
        else:
            prefix = "Terrible, even"
        return f"{prefix} for a first try."

    def __get_summary_new_record(self):
        if self.score == 1:
            suffix = "You guessed everything right!"
        elif self.score >= self.PERCENTAGE_IMPRESSIVE:
            suffix = "Congratulations!"
        elif self.score >= self.PERCENTAGE_MEDIOCRE:
            suffix = "But there is still a lot to improve."
        else:
            suffix = "However there is nothing to brag about - you scored only {:.0%}.".format(
                self.score
            )
        return f"That's a new record. {suffix}"

    def __get_summary_close_to_record(self):
        if self.diff_to_record == 0:
            incentive = (
                "Which is still completely pathetic."
                if self.score <= self.PERCENTAGE_BAD
                else "Way to go!"
            )
            progress = f"You matched all-time record for this revision! {incentive}"
        elif self.diff_to_record > 0:
            suffix = "" if self.diff_to_record == 1 else "s"
            incentive = (
                "But it's still entirely pathetic."
                if self.score <= self.PERCENTAGE_BAD
                else "But that's still an excellent score."
            )
            progress = f"You missed all-time record by only {self.diff_to_record} card{suffix}. {incentive}"
        return progress

    def __get_summary_close_to_max(self):
        t = "that" if self.diff == 1 else "those"
        suffix = "" if self.diff == 1 else "s"
        progress = f"Hadn't it been for {t} {self.diff} card{suffix} and you would have scored the max!"
        return progress

    def __get_summary_standard_case(self):
        suffix = "" if abs(self.diff_last_record) == 1 else "s"
        if self.diff_last_record > 0:
            incentive = (
                "Keep it up!"
                if self.score >= self.PERCENTAGE_MEDIOCRE
                else "However, there is still a lot to improve."
            )
            progress = f"You guessed {self.diff_last_record} card{suffix} more than last time. {incentive}"
        elif self.diff_last_record == 0:
            progress = "You guessed the exact same number of cards as last time."
        else:
            incentive = (
                "However, overall it's not that bad - you scored {:.0%}.".format(
                    self.score
                )
                if self.score >= self.PERCENTAGE_BAD
                else "Get your sh*t together."
            )
            comparison = ["last time", "previously", "in the previous attempt"][
                randint(0, 2)
            ]
            progress = f"You guessed {abs(self.diff_last_record)} card{suffix} less than {comparison}. {incentive}"
        return progress

    def __get_summary_timespent(self):

        if round(self.diff_time, 0) == 0:
            res = "Exactly the same time as before - what an uncanny happenstance!"
        elif self.last_time_spent == 0:
            res = f"CPM equalled to {self.cpm_score:.0f}."
        elif self.score >= 0.8:
            if self.diff_to_record > 0:
                if self.diff_time < 0:
                    res = (
                        f"And you reduced time spent by {abs(self.diff_time)} seconds."
                    )
                else:
                    res = f"At the cost of time however - you were {abs(self.diff_time)} seconds slower than last time."
            else:
                if self.cpm_score >= self.CPM_ULTRA_FAST:
                    res = f"Testing on production again?"
                elif self.cpm_score >= self.CPM_VERY_FAST:
                    res = f"{self.cpm_score:.0f} CPM - Faster than light!"
                elif self.cpm_score >= self.CPM_FAST:
                    res = f"{self.cpm_score:.0f} CPM - Astounding feat!!"
                elif self.cpm_score >= self.CPM_MEDIUM:
                    res = f"You made it in {self.cpm_score:.0f} CPM which is {abs(self.cpm_diff):.0f} {self.desc_cpm_diff} than last time."
                elif self.cpm_score >= self.CPM_ULTRA_SLOW:
                    res = f"Taking your time with {self.cpm_score:.0f} CPM, aren't you?"
                else:
                    res = f"However with {self.cpm_score:.0f} CPM you're slower than the Lagun."
        elif self.score >= self.PERCENTAGE_MEDIOCRE:
            if self.cpm_score >= self.CPM_PRETTY_FAST:
                res = f"{self.cpm_score:.0f} CPM - that will be $150 for speeding, sir."
            elif self.cpm_score >= self.CPM_MEDIUM:
                if self.cpm_diff >= 0:
                    res = f"{self.cpm_score:.0f} CPM - {abs(self.cpm_diff):.0f} {self.desc_cpm_diff} than last time, but focus more on accuracy next time, ok?"
                else:
                    suffix = (
                        "not only were you slower, but the % score dropped as well"
                        if self.diff_last_record < 0
                        else "at least the % score improved"
                    )
                    res = f"{abs(self.cpm_diff):.0f} CPM {self.desc_cpm_diff} than last time - {suffix}."
            elif self.cpm_score >= self.CPM_SLOW:
                res = f"{self.cpm_score:.0f} CPM - taking it easy"
            else:
                res = f"With {self.cpm_score:.0f} CPM even sloths are faster than you."
        else:
            if self.cpm_score >= self.CPM_PRETTY_FAST:
                res = f"But what's the point of going {self.cpm_score:.0f} CPM if you miss most of them!?"
            elif self.cpm_score >= self.CPM_MEDIUM:
                res = f"At least the pacing was reasonable."
            else:
                res = f"With embarrassing {self.cpm_score:.0f} CPM it makes you slower than a drunk turtle."

        return f" {res}"
