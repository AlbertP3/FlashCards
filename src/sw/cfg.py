import os
import json
import re
from copy import deepcopy
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import Qt
from data_types import HIDE_TIPS_POLICIES
from widgets import CheckableComboBox, ScrollableOptionsWidget
from utils import fcc_queue, Caliper, LogLvl
from cfg import config, validate
from typing import Callable
import logging

log = logging.getLogger("GUI")


class ConfigSideWindow:

    def __init__(self):
        self.side_window_titles["config"] = "Settings"
        self.config = config
        self.funcs_to_restart = list()
        self.config_button = self.create_button(
            self.config["icons"]["config"], self.get_config_sidewindow
        )
        self.layout_third_row.addWidget(self.config_button, 2, 5)
        self.add_shortcut("config", self.get_config_sidewindow, "main")

    def get_config_sidewindow(self):
        self.themes_dict = self.load_themes()
        self.arrange_config_sidewindow()
        self.open_side_window(self.config_layout, "config")

    def arrange_config_sidewindow(self):
        self.config_layout = widget.QGridLayout()
        self.opt_scroll_area = widget.QScrollArea()
        self.opt_scroll_area.setWidgetResizable(True)
        self.opt_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.opt_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.opt_scroll_area.setVerticalScrollBar(self.get_scrollbar())
        self.opts_layout = ScrollableOptionsWidget()
        self.opt_scroll_area.setWidget(self.opts_layout)
        self.config_layout.addWidget(self.opt_scroll_area)
        self.db.update_fds()
        self.fill_config_list()

    def _init_submit_btn(self) -> widget.QPushButton:
        if self.funcs_to_restart:
            self.submit_btn = self.create_button(
                "Click to restart",
                lambda: self.__on_config_commit_restart(self.funcs_to_restart),
            )
        else:
            self.submit_btn = self.create_button(
                "Confirm changes", self.commit_config_update
            )
        self.submit_btn.setStyleSheet(self.config["theme"]["label_stylesheet"])

    def fill_config_list(self):
        self._init_submit_btn()

        self.opts_layout.add_label("Main")
        self.card_default_cbx = self.cfg_cbx(
            self.config["card_default_side"],
            ["0", "1", "Random"],
            multi_choice=False,
            text="Card default side",
        )
        self.languages_cbx = self.cfg_cbx(
            self.config["languages"],
            self.db.get_available_languages(),
            text="Languages",
        )
        self.optional_featuers_cbx = self.cfg_cbx(
            self.config["opt"],
            list(self.config["opt"].keys()),
            text="Optional features",
        )
        self.final_actions_cbx = self.cfg_cbx(
            self.config["final_actions"],
            list(self.config["final_actions"].keys()),
            multi_choice=True,
            text="Final actions",
        )
        self.pace_card_qle = self.cfg_qle(
            self.config["pace_card_interval"], text="Card pacing"
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Mistakes")
        self.mst_opts_cbx = self.cfg_cbx(
            self.config["mst"]["opt"],
            list(self.config["mst"]["opt"].keys()),
            text="Optional features",
        )
        self.mistakes_part_size_qle = self.cfg_qle(
            self.config["mst"]["part_size"], text="Mistakes part size"
        )
        self.mistakes_part_cnt_qle = self.cfg_qle(
            self.config["mst"]["part_cnt"], text="Mistakes parts count"
        )
        self.mst_rev_int_qle = self.cfg_qle(
            self.config["mst"]["interval_days"],
            text="Days between reviews",
        )
        self.popup_trigger_unrevmistakes_qle = self.cfg_qle(
            self.config["popups"]["triggers"]["unreviewed_mistakes_percent"],
            text="Popup trigger mistakes cnt",
        )
        self.min_eph_cards_qle = self.cfg_qle(
            self.config["min_eph_cards"],
            text="Ephemeral min cards",
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Theme")
        self.theme_cbx = self.cfg_cbx(
            self.config["active_theme"],
            self.themes_dict.keys(),
            multi_choice=False,
            text="Theme",
        )
        self.font_qle = self.cfg_qle(
            self.config["theme"]["font"],
            text="Font",
        )
        self.font_size_qle = self.cfg_qle(
            self.config["dim"]["font_textbox_size"],
            text="Font size",
        )
        self.console_font_qle = self.cfg_qle(
            self.config["theme"]["console_font"],
            text="Console font",
        )
        self.console_font_size_qle = self.cfg_qle(
            self.config["dim"]["console_font_size"],
            text="Console font size",
        )
        self.button_font_size_qle = self.cfg_qle(
            self.config["dim"]["font_button_size"],
            text="Button font size",
        )
        self.default_suffix_qle = self.cfg_qle(
            self.config["theme"]["default_suffix"],
            text="Default suffix",
        )
        self.spacing_qle = self.cfg_qle(
            self.config["dim"]["spacing"],
            text="Spacing",
        )
        self.cell_alignment_cbx = self.cfg_cbx(
            self.config["cell_alignment"],
            ["left", "right", "center"],
            multi_choice=False,
            text="Cell alignment",
        )
        self.synopsis_qle = self.cfg_qle(self.config["synopsis"], text="Synopsis")

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("EFC")
        self.efc_threshold_qle = self.cfg_qle(
            self.config["efc"]["threshold"], text="Threshold"
        )
        self.efc_cache_exp_qle = self.cfg_qle(
            self.config["efc"]["cache_expiry_hours"], text="Cache expiry (hours)"
        )
        self.efc_policy_cbx = self.cfg_cbx(
            self.config["efc"]["opt"],
            list(self.config["efc"]["opt"].keys()),
            text="Next policy",
        )
        self.efc_primary_sort_cbx = self.cfg_cbx(
            self.config["efc"]["sort"]["key_1"],
            content=["fp", "disp", "score", "is_init"],
            text="Primary sort key",
            multi_choice=False,
        )
        self.efc_secondary_sort_cbx = self.cfg_cbx(
            self.config["efc"]["sort"]["key_2"],
            content=["fp", "disp", "score", "is_init"],
            text="Secondary sort key",
            multi_choice=False,
        )
        self.days_to_new_rev_qle = self.cfg_qle(
            self.config["days_to_new_rev"], text="Days between new revisions"
        )
        self.init_rep_qle = self.cfg_qle(
            self.config["init_revs_cnt"], text="Initial revision count"
        )
        self.init_revh_qle = self.cfg_qle(
            self.config["init_revs_inth"], text="Initial revision interval"
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("SOD")
        self.sod_init_lng_cbx = self.cfg_cbx(
            self.config["SOD"]["std_src_lng"],
            ["auto", "native", "foreign"],
            multi_choice=False,
            text="Default language",
        )
        self.sod_files_cbx = self.cfg_cbx(
            self.config["SOD"]["files_list"],
            multi_choice=True,
            content=sorted(self.db.get_all_files(dirs={self.db.LNG_DIR})),
            text="Files list",
        )
        self.sod_cell_alignment_cbx = self.cfg_cbx(
            self.config["SOD"]["cell_alignment"],
            multi_choice=False,
            content=["left", "right", "center"],
            text="Cell alingment",
        )
        self.lookup_mode_cbx = self.cfg_cbx(
            self.config["lookup"]["mode"],
            multi_choice=False,
            content=["quick", "full", "auto"],
            text="Lookup mode",
        )
        self.lookup_pattern_qle = self.cfg_qle(
            self.config["lookup"]["pattern"], text="Lookup pattern"
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("CRE")
        self.cre_settings_cbx = self.cfg_cbx(
            self.config["CRE"]["opt"],
            list(self.config["CRE"]["opt"].keys()),
            multi_choice=True,
            text="CRE options",
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Hide Tips")
        self.hide_tips_policy_rev_cbx = self.cfg_cbx(
            self.config["hide_tips"]["policy"][self.db.KINDS.rev],
            [
                *HIDE_TIPS_POLICIES.get_common(),
                HIDE_TIPS_POLICIES.reg_rev,
            ],
            multi_choice=True,
            text="Hide tips policy: Rev",
        )
        self.hide_tips_policy_lng_cbx = self.cfg_cbx(
            self.config["hide_tips"]["policy"][self.db.KINDS.lng],
            [*HIDE_TIPS_POLICIES.get_common()],
            multi_choice=True,
            text="Hide tips policy: Lng",
        )
        self.hide_tips_policy_mst_cbx = self.cfg_cbx(
            self.config["hide_tips"]["policy"][self.db.KINDS.mst],
            [*HIDE_TIPS_POLICIES.get_common()],
            multi_choice=True,
            text="Hide tips policy: Mst",
        )
        self.hide_tips_policy_eph_cbx = self.cfg_cbx(
            self.config["hide_tips"]["policy"][self.db.KINDS.eph],
            [*HIDE_TIPS_POLICIES.get_common()],
            multi_choice=True,
            text="Hide tips policy: Eph",
        )
        self.hide_tips_pattern_qle = self.cfg_qle(
            self.config["hide_tips"]["pattern"], text="Hide tips pattern"
        )
        self.hide_tips_connector_cbx = self.cfg_cbx(
            self.config["hide_tips"]["connector"],
            ["and", "or"],
            multi_choice=False,
            text="Hide tips connector",
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("EMO")
        self.emo_discretizer_cbx = self.cfg_cbx(
            self.config["EMO"]["discretizer"],
            ["yeo-johnson", "decision-tree"],
            multi_choice=False,
            text="EMO discretizer",
        )
        self.emo_lngs_cbx = self.cfg_cbx(
            self.config["EMO"]["languages"],
            self.db.get_available_languages(),
            multi_choice=True,
            text="EMO languages",
        )
        self.emo_approach_cbx = self.cfg_cbx(
            self.config["EMO"]["approach"],
            ["Universal", "Language-Specific"],
            multi_choice=False,
            text="EMO approach",
        )
        self.emo_cap_fold_qle = self.cfg_qle(
            self.config["EMO"]["cap_fold"], text="EMO cap fold"
        )
        self.emo_min_records_qle = self.cfg_qle(
            self.config["EMO"]["min_records"], text="EMO min records"
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Notifications")
        self.popups_enabled_cbx = self.cfg_cbx(
            self.config["popups"]["enabled"],
            content=["True", "False"],
            text="Allow notifications",
            multi_choice=False,
        )
        self.popup_allowed_cbx = self.cfg_cbx(
            self.config["popups"]["allowed"],
            list(self.config["popups"]["allowed"].keys()),
            text="Allowed popups",
        )
        self.popup_lvl_cbx = self.cfg_cbx(
            LogLvl.get_field_name_by_value(self.config["popups"]["lvl"]),
            multi_choice=False,
            content=LogLvl.get_fields(),
            text="Popup level threshold",
        )
        self.popup_timeout_qle = self.cfg_qle(
            self.config["popups"]["timeout_ms"], text="Popup timeout (msec)"
        )
        self.popup_showani_qle = self.cfg_qle(
            self.config["popups"]["show_animation_ms"], text="Popup enter (msec)"
        )
        self.popup_hideani_qle = self.cfg_qle(
            self.config["popups"]["hide_animation_ms"], text="Popup hide (msec)"
        )
        self.popup_actint_qle = self.cfg_qle(
            self.config["popups"]["active_interval_ms"],
            text="Popup active interval (msec)",
        )
        self.popup_idleint_qle = self.cfg_qle(
            self.config["popups"]["idle_interval_ms"],
            text="Popup idle interval (msec)",
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Signature Generation Patterns")
        self.sigenpat_qle_group = {
            lng: self.cfg_qle(
                self.config["sigenpat"].get(lng, ""),
                text=f"Signature gen pattern: {lng}",
            )
            for lng in self.config["languages"]
        }

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Tracker")
        self.tracker_statcols_active_group = dict()
        for k, v in self.config["tracker"]["stat_cols"].items():
            self.tracker_statcols_active_group[k] = self.cfg_cbx(
                v["active"],
                content=["True", "False"],
                multi_choice=False,
                text=f"Category {k} active",
            )
        self.tracker_dispfmt = self.cfg_qle(
            self.config["tracker"]["disp_datefmt"], text="Display date format"
        )
        self.tracker_incl_col_new = self.cfg_cbx(
            self.config["tracker"]["incl_col_new"],
            content=["True", "False"],
            multi_choice=False,
            text="Include %New column",
        )
        self.tracker_default_category = self.cfg_cbx(
            self.config["tracker"]["default_category"],
            content=("wrt", "rdg", "lst", "spk", "ent"),
            multi_choice=False,
            text="Default category",
        )
        self.tracker_init_tab = self.cfg_cbx(
            self.config["tracker"]["initial_tab"],
            content=["TimeTable", "TimeChart", "Progress", "Duo", "StopWatch", "Notes"],
            multi_choice=False,
            text="Initial tab",
        )
        self.tracker_duo_active = self.cfg_cbx(
            self.config["tracker"]["duo"]["active"],
            content=["True", "False"],
            multi_choice=False,
            text="Duo tab active",
        )
        self.tracker_avg_n = self.cfg_qle(
            self.config["tracker"]["duo"]["prelim_avg"], text="Duo avg window size"
        )

        self.opts_layout.add_spacer()
        self.opts_layout.add_label("Miscellaneous")
        self.check_file_monitor_cbx = self.cfg_cbx(
            self.config["allow_file_monitor"],
            ["True", "False"],
            multi_choice=False,
            text="File monitor",
        )
        self.csv_sniffer_qle = self.cfg_cbx(
            self.config["csv_sniffer"],
            ["off", ",", ";"],
            multi_choice=False,
            text="CSV sniffer",
        )
        self.timespent_len_qle = self.cfg_qle(
            self.config["timespent_len"], text="Timespent display length"
        )
        self.cache_hist_size_qle = self.cfg_qle(
            self.config["cache_history_size"],
            text="Cache history size",
        )
        self.opts_layout.add_spacer()
        self.config_layout.addWidget(self.submit_btn)

    def collect_settings(self) -> dict:
        new_cfg = deepcopy(self.config)
        new_cfg["card_default_side"] = self.card_default_cbx.currentDataList()[0]
        new_cfg["languages"] = self.languages_cbx.currentDataList()
        new_cfg["efc"]["threshold"] = int(self.efc_threshold_qle.text())
        new_cfg["efc"]["cache_expiry_hours"] = int(self.efc_cache_exp_qle.text())
        new_cfg["efc"]["opt"] = self.efc_policy_cbx.currentDataDict()
        new_cfg["efc"]["sort"]["key_1"] = self.efc_primary_sort_cbx.currentDataList()[0]
        new_cfg["efc"]["sort"]["key_2"] = self.efc_secondary_sort_cbx.currentDataList()[
            0
        ]
        new_cfg["days_to_new_rev"] = int(self.days_to_new_rev_qle.text())
        new_cfg["opt"] = self.optional_featuers_cbx.currentDataDict()
        new_cfg["init_revs_cnt"] = int(self.init_rep_qle.text())
        new_cfg["init_revs_inth"] = int(self.init_revh_qle.text())
        new_cfg["allow_file_monitor"] = (
            self.check_file_monitor_cbx.currentDataList()[0] == "True"
        )
        new_cfg["mst"]["opt"] = self.mst_opts_cbx.currentDataDict()
        new_cfg["mst"]["part_size"] = int(self.mistakes_part_size_qle.text())
        new_cfg["mst"]["part_cnt"] = int(self.mistakes_part_cnt_qle.text())
        new_cfg["mst"]["interval_days"] = int(self.mst_rev_int_qle.text())
        new_cfg["active_theme"] = self.theme_cbx.currentDataList()[0]
        new_cfg["final_actions"] = self.final_actions_cbx.currentDataDict()
        new_cfg["pace_card_interval"] = int(self.pace_card_qle.text())
        new_cfg["csv_sniffer"] = self.csv_sniffer_qle.currentDataList()[0]
        new_cfg["SOD"]["std_src_lng"] = self.sod_init_lng_cbx.currentDataList()[0]
        new_cfg["SOD"]["files_list"] = self.sod_files_cbx.currentDataList()
        new_cfg["SOD"][
            "cell_alignment"
        ] = self.sod_cell_alignment_cbx.currentDataList()[0]
        new_cfg["lookup"]["mode"] = self.lookup_mode_cbx.currentDataList()[0]
        new_cfg["lookup"]["pattern"] = self.lookup_pattern_qle.text()
        new_cfg["CRE"]["opt"].update(self.cre_settings_cbx.currentDataDict())
        new_cfg["hide_tips"]["policy"][
            self.db.KINDS.rev
        ] = self.hide_tips_policy_rev_cbx.currentDataList()
        new_cfg["hide_tips"]["policy"][
            self.db.KINDS.lng
        ] = self.hide_tips_policy_lng_cbx.currentDataList()
        new_cfg["hide_tips"]["policy"][
            self.db.KINDS.mst
        ] = self.hide_tips_policy_mst_cbx.currentDataList()
        new_cfg["hide_tips"]["policy"][
            self.db.KINDS.eph
        ] = self.hide_tips_policy_eph_cbx.currentDataList()
        new_cfg["hide_tips"]["pattern"] = self.hide_tips_pattern_qle.text()
        new_cfg["hide_tips"][
            "connector"
        ] = self.hide_tips_connector_cbx.currentDataList()[0]
        new_cfg["timespent_len"] = int(self.timespent_len_qle.text())
        new_cfg["synopsis"] = self.synopsis_qle.text()
        new_cfg["cell_alignment"] = self.cell_alignment_cbx.currentDataList()[0]
        new_cfg["EMO"]["discretizer"] = self.emo_discretizer_cbx.currentDataList()[0]
        new_cfg["EMO"]["languages"] = self.emo_lngs_cbx.currentDataList()
        new_cfg["EMO"]["approach"] = self.emo_approach_cbx.currentDataList()[0]
        new_cfg["EMO"]["cap_fold"] = float(self.emo_cap_fold_qle.text())
        new_cfg["EMO"]["min_records"] = int(self.emo_min_records_qle.text())
        new_cfg["popups"]["enabled"] = (
            self.popups_enabled_cbx.currentDataList()[0] == "True"
        )
        new_cfg["popups"]["timeout_ms"] = int(self.popup_timeout_qle.text())
        new_cfg["popups"]["show_animation_ms"] = int(self.popup_showani_qle.text())
        new_cfg["popups"]["hide_animation_ms"] = int(self.popup_hideani_qle.text())
        new_cfg["popups"]["active_interval_ms"] = int(self.popup_actint_qle.text())
        new_cfg["popups"]["idle_interval_ms"] = int(self.popup_idleint_qle.text())
        new_cfg["popups"]["lvl"] = getattr(
            LogLvl, self.popup_lvl_cbx.currentDataList()[0]
        )
        new_cfg["popups"]["triggers"]["unreviewed_mistakes_percent"] = float(
            self.popup_trigger_unrevmistakes_qle.text()
        )
        new_cfg["popups"]["allowed"] = self.popup_allowed_cbx.currentDataDict()
        for k, v in self.sigenpat_qle_group.items():
            new_cfg["sigenpat"][k] = v.text()
        new_cfg["cache_history_size"] = int(self.cache_hist_size_qle.text())
        new_cfg["min_eph_cards"] = int(self.min_eph_cards_qle.text())
        new_cfg["theme"]["font"] = self.font_qle.text()
        new_cfg["theme"]["console_font"] = self.console_font_qle.text()
        new_cfg["dim"]["font_textbox_size"] = int(self.font_size_qle.text())
        new_cfg["dim"]["console_font_size"] = int(self.console_font_size_qle.text())
        new_cfg["dim"]["font_button_size"] = int(self.button_font_size_qle.text())
        new_cfg["theme"]["default_suffix"] = self.default_suffix_qle.text()
        new_cfg["dim"]["spacing"] = int(self.spacing_qle.text())

        for k, v in self.tracker_statcols_active_group.items():
            new_cfg["tracker"]["stat_cols"][k]["active"] = (
                v.currentDataList()[0] == "True"
            )
        new_cfg["tracker"]["disp_datefmt"] = self.tracker_dispfmt.text()
        new_cfg["tracker"]["incl_col_new"] = (
            self.tracker_incl_col_new.currentDataList()[0] == "True"
        )
        new_cfg["tracker"][
            "default_category"
        ] = self.tracker_default_category.currentDataList()[0]
        new_cfg["tracker"]["initial_tab"] = self.tracker_init_tab.currentDataList()[0]
        new_cfg["tracker"]["duo"]["active"] = (
            self.tracker_duo_active.currentDataList()[0] == "True"
        )
        new_cfg["tracker"]["duo"]["prelim_avg"] = int(self.tracker_avg_n.text())

        if new_cfg["active_theme"] != self.config["active_theme"]:
            new_cfg["theme"].update(self.themes_dict[new_cfg["active_theme"]])
            self.funcs_to_restart.append(self.set_theme)
        elif new_cfg["theme"] != self.config["theme"]:
            self.funcs_to_restart.append(self.set_theme)
        elif new_cfg["dim"] != self.config["dim"]:
            self.funcs_to_restart.append(self.set_theme)

        if new_cfg["allow_file_monitor"] != self.config["allow_file_monitor"]:
            self.funcs_to_restart.append(self._modify_file_monitor)

        return new_cfg

    def commit_config_update(self):
        try:
            modified_config = self.collect_settings()
            is_valid, errs = validate(modified_config)
        except Exception as e:
            log.error(e, exc_info=True)
            is_valid, errs = False, {f"{type(e).__name__}: {e}"}

        if is_valid:
            if (
                not self.config["opt"]["side_by_side"]
                and modified_config["opt"]["side_by_side"]
            ):
                self.toggle_primary_widgets_visibility(True)
            else:
                self.unfix_size(self)
                self.unfix_size(self.textbox)
            self.config.update(modified_config)
            self.config_manual_update()
            self.display_text(self.get_current_card().iloc[self.side])
        else:
            fcc_queue.put_notification(
                f"Invalid configuration provided!",
                lvl=LogLvl.err,
                func=lambda: self.get_logs_sidewindow(),
            )
            log.warning("\n".join(errs))
            self.funcs_to_restart.clear()
            return

        # Reload config window
        if not self.funcs_to_restart:
            fcc_queue.put_notification("Config saved", lvl=LogLvl.important)
        else:
            self.submit_btn.setText("Click to restart")
            self.submit_btn.clicked.disconnect()
            self.submit_btn.clicked.connect(
                lambda: self.__on_config_commit_restart(self.funcs_to_restart)
            )

    def __on_config_commit_restart(self, funcs: list[Callable]):
        for f in funcs:
            f()
        self.funcs_to_restart.clear()
        self.submit_btn.clicked.disconnect()
        fcc_queue.put_notification("Config saved", lvl=LogLvl.important)
        self.del_side_window()

    def _modify_file_monitor(self):
        self.initiate_file_monitor()
        if not self.active_file.tmp:
            self.file_monitor_add_path(self.active_file.filepath)
        self.file_monitor_add_path(self.config["SOD"]["last_file"])

    def cfg_cbx(self, value, content: list, text: str, multi_choice: bool = True):
        cb = CheckableComboBox(
            self,
            allow_multichoice=multi_choice,
            width=self.config.get_geo("config")[0] // 2,
        )
        cb.setStyleSheet(self.button_stylesheet)
        cb.setFont(self.BUTTON_FONT)
        if isinstance(value, dict):
            value = [k for k, v in value.items() if v is True]
        for i in content:
            try:
                cb.addItem(i, is_checked=i in value)
            except TypeError:
                cb.addItem(i, is_checked=i == str(value))
        self.opts_layout.add_widget(cb, self.create_label(text))
        return cb

    def cfg_qle(self, value: str, text: str) -> widget.QLineEdit:
        qle = widget.QLineEdit(self)
        qle.setText(str(value))
        qle.setFont(self.BUTTON_FONT)
        qle.setStyleSheet(self.button_stylesheet)
        self.opts_layout.add_widget(qle, self.create_label(text))
        return qle

    def create_blank_widget(self):
        blank = widget.QLabel(self)
        blank.setStyleSheet("border: 0px")
        return blank

    def load_themes(self) -> dict:
        themes_dict = dict()
        themes_path = os.path.join(self.db.RES_PATH, "themes")
        theme_files = [f for f in os.listdir(themes_path) if f.endswith(".json")]
        for f in theme_files:
            theme = json.load(open(os.path.join(themes_path, f), "r"))
            theme_name = f.split(".")[0]
            themes_dict[theme_name] = theme
        return themes_dict

    def config_manual_update(self, key: str = None, subdict: str = None):
        if subdict == "theme":
            if key in {"console_font_size", "default_suffix"}:
                self.init_font()
                self.console.setFont(self.CONSOLE_FONT)
                self.caliper = Caliper(self.CONSOLE_FONT)
        elif not (key or subdict):
            self._efc_last_calc_time = 0
            self.db.update_fds()
            self.update_default_side()
            self.revtimer_hide_timer = self.config["opt"]["hide_timer"]
            self.revtimer_show_cpm_timer = self.config["opt"]["show_cpm_timer"]
            self.set_append_seconds_spent_function()
            self.initiate_pace_timer()
            self.initiate_notification_timer()
            self.start_notification_timer()
            self.tips_hide_re = re.compile(self.config["hide_tips"]["pattern"])
            self.set_should_hide_tips()
