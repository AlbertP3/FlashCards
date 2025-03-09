from collections import OrderedDict
from itertools import islice
import logging
import re
import os
from functools import cache
from SOD.dicts import Dict_Services
from SOD.file_handler import get_filehandler
from DBAC import db_conn
from utils import Caliper
from cfg import config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tabs.sod import SodTab

log = logging.getLogger("SOD")


class State:
    def __init__(self) -> None:
        self.SELECT_TRANSLATIONS_MODE = False
        self.RES_EDIT_SELECTION_MODE = False
        self.MODIFY_RES_EDIT_MODE = False
        self.MANUAL_MODE = False
        self.QUEUE_MODE = False
        self.QUEUE_SELECTION_MODE = False


class Message:
    def __init__(self) -> None:
        self.PHRASE_EXISTS_IN_DB = "⚐ Duplicate"
        self.SAVE_ABORTED = ""
        self.NO_TRANSLATIONS = "⚠ No Translations!"
        self.WRONG_EDIT = "⚠ Wrong Edit!"
        self.OK = "✅ OK"
        self.QUERY_UPDATE = "🔃 Updated Queue"
        self.QUERY_DONE = "✅ Queue Saved"
        self.RE_ERROR = "⚠ Regex Error!"
        self.RE_WARN = "⚠ Nothing Matched Regex!"
        self.UNSUP_EXT = "⚠ Unsupported File Extension"
        self.FILE_MISSING = "⛌ File Missing!"
        self.FILE_INVALID = "⛌ Invalid File!"
        self.CANNOT_DELETE = "⛌ Cannot Delete"
        self.DELETE_COMPLETE = "🗑️ Deleted Record"
        self.INVALID_INPUT = "⛌ Invalid Input!"
        self.DB_REFRESH = "🔃 Refreshed Database"


class Prompt:
    def __init__(self) -> None:
        self.SEARCH = "Search: "
        self.MATCH = "Match: "
        self.SELECT = "Select for {}: "
        self.MANUAL_PH = "Phrase: "
        self.MANUAL_TR = "Transl: "
        self.update_phrase_prompt()

    def update_phrase_prompt(self):
        self.PHRASE = self.MATCH if config["SOD"]["use_regex"] else self.SEARCH


class CLI:

    def __init__(self, tab: "SodTab") -> None:
        self.state = State()
        self.prompt = Prompt()
        self.msg = Message()
        self.transl = str()
        self.phrase = str()
        self.queue_dict = OrderedDict()
        self.tab = tab
        self.init_cli_args()
        self.re_excl_dirs = re.compile(config["SOD"]["exclude_pattern"], re.IGNORECASE)
        self.dicts = Dict_Services()
        self.init_file_handler()
        self.selection_queue = list()
        self.status_message = str()
        self.valid_cmd: re.Pattern = re.compile(r"^(\d+|a|m\d*|(d|r|e)\d+|)$")

    @property
    def caliper(self) -> Caliper:
        return self.tab.caliper

    @property
    @cache
    def pix_lim(self) -> int:
        return self.tab.console.viewport().width()

    @property
    @cache
    def lines_lim(self) -> int:
        # -1 excludes status bar
        return int(self.tab.console.viewport().height() // self.caliper.sch) - 1

    def init_file_handler(self):
        try:
            self.fh = get_filehandler(config["SOD"]["last_file"])
            self.tab.mw.file_monitor_add_protected_path(config["SOD"]["last_file"])
            self.init_set_languages()
            self.cls()
        except (FileNotFoundError, AttributeError) as e:
            self.fh = get_filehandler(".void")
            self.init_set_languages()
            err_msgs = {
                "FileNotFoundError": self.msg.FILE_MISSING,
                "AttributeError": self.msg.FILE_INVALID,
            }
            self.cls(err_msgs[type(e).__name__], keep_content=True)

    def init_cli_args(self):
        self.sep_manual = config["SOD"]["manual_mode_sep"]
        self.dict_arg = config["SOD"]["dict_change_arg"]
        self.queue_arg = config["SOD"]["queue_start_arg"]
        self.chg_db_arg = config["SOD"]["change_db_arg"]
        self.list_files_arg = config["SOD"]["list_files_arg"]
        self.regex_arg = config["SOD"]["regex_arg"]
        self.help_arg = config["SOD"]["help_arg"]

    def init_set_languages(self):
        if config["SOD"]["std_src_lng"] == "auto":
            ref = config["SOD"]["last_src_lng"]
        else:
            ref = config["SOD"]["std_src_lng"]
        r = 1 if ref == "native" else -1
        native, foreign = self.fh.get_languages()[::r]
        self.dicts.set_languages(native, foreign)
        config["SOD"]["last_src_lng"] = ref

    @property
    def is_from_native(self) -> bool:
        return self.dicts.source_lng == self.fh.native_lng

    @property
    def using_local_db(self) -> bool:
        return self.dicts.dict_service == "local"

    def refresh_file_handler(self):
        self.tab.mw.file_monitor_del_protected_path(self.fh.path)
        self.fh.close()
        self.fh = get_filehandler(config["SOD"]["last_file"])
        self.tab.mw.file_monitor_add_protected_path(self.fh.path)
        self.init_set_languages()

    def update_file_handler(self, filepath: str):
        """
        Searches for a matching file using regex.
        Uses files_list if available, else all language files
        """
        try:
            pattern = re.compile(filepath, re.IGNORECASE)
            if config["SOD"]["files_list"]:
                for f in config["SOD"]["files_list"]:
                    if pattern.search(f):
                        filepath = f
                        break
                else:
                    raise KeyError
            elif not os.path.exists(filepath):
                filepath = db_conn.match_from_all_languages(
                    repat=pattern, exclude_dirs=self.re_excl_dirs
                ).pop()
            fh = get_filehandler(filepath)
            if self.fh:
                self.fh.close()
                self.tab.mw.file_monitor_del_protected_path(self.fh.path)
            self.fh = fh
            self.tab.mw.file_monitor_add_protected_path(self.fh.path)
            self.init_set_languages()
            self.cls()
        except re.error:
            self.cls(self.msg.RE_ERROR, keep_content=True)
        except KeyError:
            self.cls(self.msg.RE_WARN, keep_content=True)
        except AttributeError:
            self.cls(
                self.msg.UNSUP_EXT + f' {filepath.split(".")[-1]}!', keep_content=True
            )

    def reset_state(self):
        self.state = State()

    def set_output_prompt(self, t):
        self.tab.console_prompt = t

    def send_output(self, text: str):
        self.tab.console.append(text)
        self.tab.console_log.extend(text.split("\n"))

    def execute_command(self, parsed_phrase: list):
        parsed_phrase = self.handle_prefix(parsed_phrase)
        if not parsed_phrase:
            return
        elif parsed_phrase.count(config["SOD"]["manual_mode_sep"]) == 2:
            self.insert_manual_oneline(parsed_phrase)
        elif parsed_phrase[0] == config["SOD"]["manual_mode_seq"]:
            self.insert_manual(parsed_phrase)
        elif parsed_phrase[0] == self.queue_arg:
            self.setup_queue()
        elif parsed_phrase[0] == self.list_files_arg:
            self.list_files()
        elif parsed_phrase[0] == self.help_arg:
            self.show_help()
        else:
            self.handle_single_entry(" ".join(parsed_phrase))

    def handle_prefix(self, parsed_cmd: list):
        src_lng, tgt_lng, capture = None, None, None
        for i in parsed_cmd:
            if capture:
                if capture == "change_db":
                    self.update_file_handler(i)
                elif capture == "change_dict":
                    self.set_dict(i)
                capture = None
            elif i in self.dicts.available_lngs:
                if not src_lng:
                    src_lng = i.lower()
                elif not tgt_lng:
                    tgt_lng = i.lower()
            elif i == self.chg_db_arg:
                capture = "change_db"
            elif i == self.dict_arg:
                capture = "change_dict"
            elif i == self.regex_arg:
                self.toggle_regex()
            else:
                break
            parsed_cmd = parsed_cmd[1:]
            if bool(src_lng) ^ bool(tgt_lng):
                self.dicts.switch_languages(src_lng, tgt_lng)
                self.update_last_source_lng()
                self.cls()
            elif src_lng and tgt_lng:
                self.dicts.set_languages(src_lng, tgt_lng)
                self.update_last_source_lng()
                self.cls()
        if capture:
            self.cls(self.msg.INVALID_INPUT)
            return ""
        else:
            return parsed_cmd

    def toggle_regex(self):
        config["SOD"]["use_regex"] = not config["SOD"]["use_regex"]
        self.prompt.update_phrase_prompt()
        self.set_output_prompt(self.prompt.PHRASE)
        self.cls()

    def list_files(self):
        """Send list of all available files to the console"""
        self.cls()
        self.send_output(
            "\n".join(
                db_conn.get_all_files(
                    dirs={
                        db_conn.LNG_DIR,
                    },
                    use_basenames=True,
                )
            )
        )

    def set_dict(self, new_dict):
        if new_dict in self.dicts.available_dicts_short:
            new_dict = {
                k for k, v in self.dicts.dicts.items() if v["shortname"] == new_dict
            }.pop()
        if new_dict in self.dicts.available_dicts:
            self.dicts.set_dict_service(new_dict)
            self.cls(keep_content=self.state.QUEUE_MODE, keep_cmd=self.state.QUEUE_MODE)
        else:
            self.cls(
                f"⚠ Wrong Dict!", keep_content=True, keep_cmd=self.state.QUEUE_MODE
            )

    def update_last_source_lng(self):
        lng = "native" if self.dicts.source_lng == self.fh.native_lng else "foreign"
        config["SOD"]["last_src_lng"] = lng

    def insert_manual(self, parsed_cmd):
        if not self.state.MANUAL_MODE:
            self.cls()
            self.set_output_prompt(
                self.prompt.MANUAL_TR if self.is_from_native else self.prompt.MANUAL_PH
            )
            self.state.MANUAL_MODE = "first"
            return
        elif self.state.MANUAL_MODE == "first":
            self.phrase = " ".join(parsed_cmd)
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                self.manual_duplicate_show()
                return
            self.set_output_prompt(
                self.prompt.MANUAL_PH if self.is_from_native else self.prompt.MANUAL_TR
            )
            self.state.MANUAL_MODE = "second"
            return
        elif self.state.MANUAL_MODE == "second":
            self.transl = " ".join(parsed_cmd)
        # Finalize
        if self.phrase and self.transl:
            self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False
        self.set_output_prompt(self.prompt.PHRASE)

    def manual_duplicate_show(self):
        """If manually entered phrase exists in db then print results from source"""
        prev_dict = self.dicts.dict_service
        self.dicts.dict_service = "local"
        self.translations, self.originals, _ = self.dicts.get_info_about_phrase(
            self.phrase
        )
        self.state.MANUAL_MODE = False
        self.state.SELECT_TRANSLATIONS_MODE = True
        self.set_output_prompt(f"Select for {self.phrase}: ")
        self.cls(self.msg.PHRASE_EXISTS_IN_DB)
        self.print_translations_table(self.translations, self.originals)
        self.dicts.dict_service = prev_dict

    def insert_manual_oneline(self, parsed_cmd):
        # if 2 delimiter signs are provided, treat the input as a complete card.
        self.state.MANUAL_MODE = True
        delim_index = parsed_cmd.index(self.sep_manual, 2)
        self.phrase = " ".join(parsed_cmd[1:delim_index])
        self.transl = " ".join(parsed_cmd[delim_index + 1 :])
        if self.phrase and self.transl:
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                prev_dict = self.dicts.dict_service
                self.dicts.dict_service = "local"
                tran, orig, _ = self.dicts.get_info_about_phrase(self.phrase)
                self.translations, self.originals = [self.transl, *tran], [
                    self.phrase,
                    *orig,
                ]
                self.state.SELECT_TRANSLATIONS_MODE = True
                self.set_output_prompt(f"Select for {self.phrase}: ")
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                self.print_translations_table(self.translations, self.originals)
                self.dicts.dict_service = prev_dict
            else:
                self.save_to_db(self.phrase, [self.transl])
        else:
            self.cls(self.msg.SAVE_ABORTED)
        self.state.MANUAL_MODE = False

    def handle_single_entry(self, phrase):
        self.phrase = phrase
        self.translations, self.originals, self.warnings = (
            self.dicts.get_info_about_phrase(self.phrase)
        )
        self.cls()
        if self.translations:
            if self.fh.is_duplicate(self.phrase, self.is_from_native):
                self.cls(self.msg.PHRASE_EXISTS_IN_DB)
                if not self.using_local_db:
                    tran, orig = self.fh.get_translations(
                        self.phrase, self.is_from_native
                    )
                    for i in range(len(tran)):
                        self.originals.insert(0, orig[i])
                        self.translations.insert(0, tran[i])
            self.state.SELECT_TRANSLATIONS_MODE = True
            self.set_output_prompt(f"Select for {self.phrase}: ")
            self.print_translations_table(self.translations, self.originals)
        else:
            if self.warnings:
                self.cls(self.warnings[0])
            else:
                self.cls(self.msg.NO_TRANSLATIONS)

    def lookup(self, phrase: str, src_lng: str, default: str = "") -> str:
        """Quick search for a phrase"""
        out = default
        prev_src_lng = self.dicts.source_lng
        prev_tgt_lng = self.dicts.target_lng
        self.dicts.set_languages(src_lng, None)

        translations, originals, warnings = self.dicts.get_info_about_phrase(phrase)
        found_cnt = 0
        if translations:
            pattern = re.compile(config["lookup"]["pattern"])
            found = False
            for r in originals:
                if p := pattern.findall(r):
                    if not found:
                        out = ", ".join(p)
                        found = True
                    found_cnt += 1
        if found_cnt > 1:
            out += " (?)"
        self.dicts.set_languages(prev_src_lng, prev_tgt_lng)
        return out

    def setup_queue(self):
        self.queue_dict = OrderedDict()
        self.queue_index = 1
        self.queue_page_counter = 0
        self.queue_visible_items = 0
        self.cls()
        self.state.QUEUE_MODE = True
        self.phrase = None
        self.translations = None
        self.set_output_prompt(f"{self.queue_index:>2d}. ")

    def setup_queue_unpacking(self):
        if self.queue_dict:
            self.state.QUEUE_MODE = False
            self.state.QUEUE_SELECTION_MODE = True
            self.unpack_translations_from_queue()
        if not self.queue_dict:
            self.cls("" if self.state.QUEUE_MODE else self.msg.QUERY_DONE)
            self.reset_state()
            self.set_output_prompt(self.prompt.PHRASE)

    def manage_queue(self, parsed_cmd: list):
        self.queue_builder(parsed_cmd)
        self.set_output_prompt(f"{self.queue_index:>2d}. ")

    def unpack_translations_from_queue(self, parsed_cmd=None):
        if self.queue_dict or self.state.MODIFY_RES_EDIT_MODE:
            self.__unpack_translations_from_queue()
        else:
            self.set_output_prompt(self.prompt.PHRASE)
            self.state.QUEUE_SELECTION_MODE = False

    def __unpack_translations_from_queue(self):
        while self.queue_dict:
            p, rs = self.queue_dict.popitem(last=False)
            self.queue_page_counter += 1
            self.phrase = p
            if "MANUAL" in rs[2]:
                self.save_to_db(p, rs[0])
            else:
                self.cls(f"➲ [{self.queue_page_counter}/{self.queue_index-1}]:")
                self.print_translations_table(rs[0], rs[1])
                self.translations = rs[0]
                self.originals = rs[1]
                self.set_output_prompt(self.prompt.SELECT.format(p))
                self.state.SELECT_TRANSLATIONS_MODE = True
                break

    def queue_builder(self, parsed_cmd: list):
        if parsed_cmd[0] == "del":
            self.del_from_queue(parsed_cmd[1:])
            return
        elif parsed_cmd[0] == "dict":
            self.set_dict(parsed_cmd[1])
            return

        p_lim = self.pix_lim - 4 * self.caliper.scw
        phrase: str = " ".join(self.handle_prefix(parsed_cmd))
        exists_in_queue = phrase in self.queue_dict.keys()
        if phrase.startswith(self.sep_manual):  # Manual Mode for Queue
            l2 = [""] * 3
            l1 = phrase.split(self.sep_manual)
            l2[: len(l1)] = l1
            phrase, translations = l2[1].strip(), l2[2].strip()
            self.queue_dict[phrase] = [[translations], [phrase], ["MANUAL"]]
            cleaned_text = (
                self.tab.console.toPlainText()
                .replace(f" {self.sep_manual} ", " ")
                .replace(translations, "")
            )
            self.tab.console.setText(cleaned_text)
            self.tab.console_log = cleaned_text.split("\n")
            transl = translations
            warnings = None
        else:  # Online Dictionary
            translations, originals, warnings = self.dicts.get_info_about_phrase(phrase)
            if (translations or originals) and not warnings:
                self.queue_dict[phrase] = [translations, originals, warnings]
                transl = "; ".join(translations[:2]).rstrip()
                if self.caliper.strwidth(transl) > p_lim:
                    transl = (
                        self.caliper.abbreviate(transl, p_lim - self.caliper.fillerlen)
                        + config["theme"]["default_suffix"]
                    )
            else:
                transl = ""
                warnings = warnings if warnings else [self.msg.NO_TRANSLATIONS]

        if exists_in_queue:
            self.cls(msg=self.msg.QUERY_UPDATE)
            self.print_queue()
        elif warnings:
            msg = warnings[0]
            self.cls(msg, keep_content=False, keep_cmd=True)
            self.print_queue()
        else:
            if self.fh.is_duplicate(phrase, self.is_from_native):
                msg = self.msg.PHRASE_EXISTS_IN_DB
                if not self.using_local_db:
                    tran, orig = self.fh.get_translations(phrase, self.is_from_native)
                    for i in range(len(tran)):
                        self.queue_dict[phrase][0].insert(0, orig[i])
                        self.queue_dict[phrase][1].insert(0, tran[i])
                self.queue_dict[phrase][2].append("DUPLICATE")
            else:
                msg = self.msg.OK

            lim_items = int(self.lines_lim / 2)
            if self.queue_visible_items + 1 > lim_items:
                self.cls(msg, keep_content=False, keep_cmd=True)
                self.print_queue(slice_=[len(self.queue_dict) - lim_items, 0])
            else:
                self.cls(msg, keep_content=True, keep_cmd=True)
                self.send_output(f" | {transl}")
                self.queue_index += 1
                self.queue_visible_items += 1

    def del_from_queue(self, indices: list):
        if indices:
            if not all([i.isnumeric() for i in indices]):
                return
        else:
            indices = [len(self.queue_dict.keys())]
        indices = [int(i) for i in indices if int(i) <= len(self.queue_dict.keys())]
        l_k = list(self.queue_dict.keys())
        for i in indices:
            self.queue_dict.pop(l_k[i - 1])
        self.queue_index = 1
        self.cls()
        self.print_queue()
        self.set_output_prompt(f"{self.queue_index:>2d}. ")

    def print_queue(self, slice_: list = [0, 0]):
        plim = self.pix_lim - 3 * self.caliper.scw
        if slice_[0] < 0:
            slice_[0] = len(self.queue_dict) + slice_[0]
        if slice_[1] == 0:
            slice_[1] = len(self.queue_dict)
        self.queue_index = slice_[0] + 1
        self.queue_visible_items = 0
        for phrase, info in islice(self.queue_dict.items(), slice_[0], slice_[1]):
            s1 = f"{self.queue_index:>2d}. {phrase}"
            transl = "; ".join(info[0][:2]).rstrip()
            if self.caliper.strwidth(transl) > plim:
                transl = (
                    self.caliper.abbreviate(transl, plim)
                    + config["theme"]["default_suffix"]
                )
            s2 = f" | {transl}"
            self.send_output(s1 + "\n" + s2)
            self.queue_index += 1
            self.queue_visible_items += 1

    def save_to_db(self, phrase: str, translations: list):
        translations: str = "; ".join([t for t in translations if t])
        if len(translations) > 0 and self.phrase:
            is_duplicate = self.fh.validate_dtracker(phrase)

            if self.is_from_native:
                phrase, translations = translations, phrase

            if is_duplicate:
                success, errs = self.fh.edit_content(phrase, translations)
            else:
                success, errs = self.fh.append_content(phrase, translations)

            if success:
                self.notify_on_save(phrase, translations, is_duplicate)
            else:
                self.cls(errs)
        else:
            self.cls(self.msg.SAVE_ABORTED)

        self.phrase = None
        self.res_edit = None

    def notify_on_save(self, phrase, res_edit, is_duplicate):
        icon = "🖉" if is_duplicate else "🖫"
        msg = f"{icon} {phrase}: {res_edit}"
        self.cls(msg)

    def delete_from_db(self, record0: str, record1: str):
        if self.fh.delete_record(record0, record1, self.is_from_native):
            self.cls(self.msg.DELETE_COMPLETE)
        else:
            self.cls(self.msg.CANNOT_DELETE)

    def print_translations_table(self, trans: list, origs: list):
        sep = "\u0020|\u0020"
        res_lim = self.lines_lim
        trans, origs = trans[:res_lim], origs[:res_lim]
        if any(origs):
            plim = self.pix_lim // 2
            if config["SOD"]["table_ext_mode"] == "fix":
                output = self.__ptt(origs, trans, plim, plim, sep)
            elif config["SOD"]["table_ext_mode"] == "flex":
                llim = min(
                    max(self.caliper.strwidth(c) for c in origs)
                    + self.caliper.strwidth(f"{len(origs)+1}. "),
                    plim,
                )
                rlim = 2 * plim - llim
                output = self.__ptt(origs, trans, llim, rlim, sep)
        else:
            output = self.__ptt(origs, trans, self.pix_lim, 0, "")
        self.send_output(output)

    def __ptt(self, c0: list, c1: list, llim: float, rlim: float, sep: str) -> str:
        output = list()
        for i, (c0r, c1r) in enumerate(zip(c0, c1)):
            i = f"{i+1}. "
            c0r = self.caliper.make_cell(
                c0r,
                llim - self.caliper.strwidth(i),
                config["SOD"]["cell_alignment"],
            )
            c1r = self.caliper.make_cell(
                c1r,
                rlim - self.caliper.strwidth(sep),
                config["SOD"]["cell_alignment"],
            )
            output.append(f"{i}{c0r}{sep}{c1r}")
        return "\n".join(output)

    def select_translations(self, parsed_cmd):
        if not self.selection_cmd_is_correct(parsed_cmd):
            return

        if self.state.SELECT_TRANSLATIONS_MODE:
            self.selection_queue = parsed_cmd
            self.res_edit = list()
            self.state.SELECT_TRANSLATIONS_MODE = False
            self.state.RES_EDIT_SELECTION_MODE = True

        if self.state.RES_EDIT_SELECTION_MODE:
            for _ in range(len(self.selection_queue)):
                v: str = self.selection_queue.pop(0)
                if not v:
                    break
                elif v.isnumeric():
                    self.res_edit.append(self.translations[int(v) - 1])
                elif v[0] == "r":
                    i = int(v[1:]) - 1
                    self.res_edit.append(self.originals[i])
                elif v[0] == "d":
                    self.delete_from_db(
                        self.originals[int(v[1:]) - 1],
                        self.translations[int(v[1:]) - 1],
                    )
                    self.state.RES_EDIT_SELECTION_MODE = False
                    self.set_output_prompt(self.prompt.PHRASE)
                    return
                else:
                    self.state.RES_EDIT_SELECTION_MODE = False
                    self.state.MODIFY_RES_EDIT_MODE = v
                    self.res_edit_set_prompt(v)
                    return
        elif self.state.MODIFY_RES_EDIT_MODE:
            self.res_edit_parse(parsed_cmd)
            self.state.MODIFY_RES_EDIT_MODE = False
            self.state.RES_EDIT_SELECTION_MODE = True
            if self.selection_queue:
                self.select_translations(None)
                return

        if not self.selection_queue:
            self.save_to_db(self.phrase, self.res_edit)
            self.state.RES_EDIT_SELECTION_MODE = False
            self.state.MODIFY_RES_EDIT_MODE = False

        if self.state.QUEUE_SELECTION_MODE:
            self.unpack_translations_from_queue()
        else:
            self.set_output_prompt(self.prompt.PHRASE)

    def selection_cmd_is_correct(self, parsed_cmd):
        result, all_args_match, index_out_of_range = True, False, False
        lim = len(self.translations)
        if (
            self.state.SELECT_TRANSLATIONS_MODE
            and str(self.state.MODIFY_RES_EDIT_MODE)[0] not in "ea"
        ):
            if len(parsed_cmd) == 1 and parsed_cmd[0].startswith("m"):
                all_args_match = False
            else:
                all_args_match = all({self.valid_cmd.match(c) for c in parsed_cmd})
                index_out_of_range = (
                    any(
                        int(re.sub(r"[a-zA-Z]", "", c)) > lim
                        for c in parsed_cmd
                        if c not in "amr"
                    )
                    if all_args_match
                    else True
                )
            if not all_args_match or index_out_of_range:
                result = False
                self.cls(self.msg.WRONG_EDIT, keep_content=True)
        return result

    def res_edit_parse(self, parsed_cmd):
        if self.state.MODIFY_RES_EDIT_MODE[0] == "m":
            c = self.tab.console.toPlainText()
            e_index = c.rfind("Modify: ") + 8
            self.phrase = c[e_index:]
            self.fh.update_dtracker(new_phrase=self.phrase)
        elif self.state.MODIFY_RES_EDIT_MODE[0] == "a":
            self.res_edit.append(" ".join(parsed_cmd))
        elif self.state.MODIFY_RES_EDIT_MODE[0] == "e":
            c = self.tab.console.toPlainText()
            e_index = c.rfind("Edit: ") + 6
            self.res_edit.append(c[e_index:])

    def res_edit_set_prompt(self, r):
        if r[0] == "m":
            new_prompt = "Modify: "
            extra = self.originals[int(r[1:]) - 1] if len(r) > 1 else self.phrase
        elif r[0] == "a":
            new_prompt = f"Add: "
            extra = ""
        elif r[0] == "e":
            new_prompt = f"Edit: "
            extra = self.translations[int(r[1:]) - 1]
        else:
            new_prompt = self.tab.console_prompt
            extra = ""
        self.set_output_prompt(new_prompt)
        self.tab.editable_output = extra

    def cls(self, msg="", keep_content=False, keep_cmd=False):
        if keep_content:
            content = self.tab.console.toPlainText().split("\n")[1:]
            if not keep_cmd and content:
                content.pop()
        self.tab.console.setText("")
        self.tab.console_log = []
        self.__post_status_bar(msg)
        if keep_content and content:
            self.send_output("\n".join(content))

    def __post_status_bar(self, msg=""):
        active_dict = self.dicts.dict_service
        source_lng = self.dicts.source_lng
        target_lng = self.dicts.target_lng
        len_db = self.fh.total_rows
        status = (
            f"{config['icons']['sod_dict']} {active_dict} | "
            f"{source_lng}{config['icons']['sod_lng_pointer']}{target_lng} | "
            f"{config['icons']['sod_db']} {self.fh.filename} | "
            f"{config['icons']['sod_card']} {len_db} | "
            f"{msg}"
        )
        self.send_output(
            self.caliper.make_cell(
                status,
                self.pix_lim,
                align="left",
            )
        )

    def show_help(self):
        available_dicts = " " + "\n ".join(
            [f"{k:<10} {v['shortname']}" for k, v in self.dicts.dicts.items()]
        )
        cmds = self.caliper.make_table(
            [
                [f" {self.chg_db_arg} <DB_NAME>", "change database file"],
                [f" {self.dict_arg} <DICT>", "switch current dictionary"],
                [
                    f' {config["SOD"]["manual_mode_seq"]}',
                    "enter the manual input mode",
                ],
                [
                    f" {self.sep_manual} <PHRASE> {self.sep_manual} <MEANING>",
                    "manual input",
                ],
                [f" {self.list_files_arg}", "list available files"],
                [f" {self.regex_arg}", f"toggle regex"],
                [" Q", "enter Queue mode"],
                [" (<SRC_LNG>^<TGT_LNG>)", "change source/target language"],
                [" <blank>", "exit SOD or finish Queue mode"],
            ],
            pixlim=self.pix_lim,
            sep=" --> ",
            align=["left", "left"],
            keep_last_border=False,
        )
        mods = self.caliper.make_table(
            [
                [" e<N>", "edit the N-th translation"],
                [" m*<N>", "modify searched phrase"],
                [" a", "add a new translation"],
                [" r<N>", "add a reversed translation"],
                [" d<N>", "remove record from source file"],
                [" <blank>", "abort"],
            ],
            pixlim=self.pix_lim,
            sep=" --> ",
            align=["left", "left"],
            keep_last_border=False,
        )
        msg = f"""Commands:\n{cmds}\nSearch results mods:\n{mods}\nAvailable dicts:\n{available_dicts}"""

        self.cls()
        self.send_output(msg)

    def close_wb(self):
        self.fh.close()
