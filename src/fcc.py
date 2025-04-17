import os
import re
import logging
from operator import methodcaller
from datetime import datetime
from random import shuffle
import pandas as pd
from PyQt5.QtWidgets import QTextEdit
from utils import flatten_dict, is_valid_filename, format_seconds_to, fcc_queue, LogLvl
from DBAC import db_conn
from CMG.init import CMGSpawn
from cfg import config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui import MainWindowGUI

log = logging.getLogger("FCC")


class FCC:
    # Flashcards console commands allows access to extra functionality

    def __init__(self, mw: "MainWindowGUI", sout: QTextEdit):
        self.mw = mw
        self.console = sout
        self.DOCS = {
            "help": "Gets Help",
            "mct": "Modify Cards Text - edits current side of the card both in current set and in the original file",
            "rcc": "Reverse Current Card - changes sides of currently displayed card and updates the source file",
            "mcr": "Modify Card Result - allows changing pos/neg for the current card",
            "dcc": "Delete Current Card - deletes card both in current set and in the file",
            "sis": "Show ILN Statistics",
            "efc": "Ebbinghaus Forgetting Curve - Optional *[SIGNATURES] else select active - shows table with revs, days from last rev and efc score and predicted time until the next revision",
            "mcp": "Modify Config Parameter - allows modifications of config file. Syntax: mcp *<sub_dict> <key> <new_value>",
            "sck": "Show Config Key: Syntax: sck *<sub_dict> <key>",
            "cfn": "Change File Name - changes currently loaded file_path, filename and all records in DB for this signature",
            "scs": "Show Current Signature",
            "lor": "List Obsolete Revisions - returns a list of revisions that are in DB but not in revisions folder.",
            "gwd": "Get Window Dimensions",
            "pcc": "Pull Current Card - load the origin file and updates the currently displayed card",
            "emo": "EFC Model Optimizer - employs regression and machine learning techniques to adjust efc model for the user needs",
            "err": "Raises an Exception",
            "add": "Add Card - appends a card to the current dataset. Does not modify the source file",
            "gcw": "Get Character Width - returns actual width in pixels for a given glyph",
            "pcd": "Print Current Dataset - pretty prints all cards in the current dataset",
            "cac": "Clear Application Cache - *key^help - runs cache_clear on an optional key",
            "ssf": "Show Scanned Files - presents a list of all relevant files",
            "clt": "Create Language Tree - creates a directory tree for a new language and an example file",
            "eph": "Create Ephemeral Mistakes - shows current mistakes as flashcards",
            "cre": "Comprehensive Review - creates a queue from all revisions that can be traversed via consecutive command calls. Optional args: flush, reversed|autosave|autonext <true,false>, stat",
            "cfg": "Config - manage the config file. Arguments: save, load, restart",
            "dbg": "Debug - display debug info",
            "dmp": "Dump Session Data - save config, update cache and create a tmpfcs file",
            "rmw": "Refresh Main Window GUI - adjust to system scaling",
        }

    def execute_command(self, parsed_input: list, followup_prompt: bool = True):
        if not parsed_input[0]:
            return
        elif self.is_allowed_command(parsed_input[0]):
            methodcaller(parsed_input[0], parsed_input)(self)
        else:
            self.post_fcc(f"{parsed_input[0]}: command not found...")
        if followup_prompt:
            self.post_fcc(self.mw.fcc.console_prompt)
        else:
            self.mw.fcc.move_cursor_to_end()

    def is_allowed_command(self, command):
        return command in self.DOCS.keys()

    def post_fcc(self, text: str = ""):
        self.console.append(text)
        self.mw.fcc.console_log.append(text)

    def help(self, parsed_cmd):
        lim = int(self.console.viewport().width())
        max_key_pixlen = (
            self.mw.fcc.caliper.strwidth(max(self.DOCS.keys(), key=len))
            + 2 * self.mw.fcc.caliper.scw
        )
        if len(parsed_cmd) == 1:
            printout = self.mw.fcc.caliper.make_table(
                data=[(k, v) for k, v in self.DOCS.items()],
                pixlim=[max_key_pixlen, lim - max_key_pixlen],
                align=["left", "left"],
                sep=" - ",
                keep_last_border=False,
            )
        else:
            command = parsed_cmd[1]
            if command in self.DOCS.keys():
                printout = self.mw.fcc.caliper.make_table(
                    data=[[command, self.DOCS[command]]],
                    pixlim=[max_key_pixlen, lim - max_key_pixlen],
                    align=["left", "left"],
                    sep=" - ",
                    keep_last_border=False,
                )
            else:  # regex search command descriptions
                try:
                    rp = re.compile(parsed_cmd[1], re.IGNORECASE)
                    matching = []
                    for k, v in self.DOCS.items():
                        if rp.search(v) or rp.search(k):
                            matching.append([k, v])
                    try:
                        printout = self.mw.fcc.caliper.make_table(
                            data=matching,
                            pixlim=[max_key_pixlen, lim - max_key_pixlen],
                            align=["left", "left"],
                            sep=" - ",
                            keep_last_border=False,
                        )
                    except IndexError:
                        printout = "Nothing matches the given phrase!"
                except re.error as e:
                    printout = f"Regex Error: {e}"

        self.post_fcc(printout)

    def require_regular_file(func):
        def verify_conditions(self, *args, **kwargs):
            if not self.mw.active_file.tmp:
                func(self, *args, **kwargs)
            else:
                self.post_fcc(f"{func.__name__} requires a real file.")

        return verify_conditions

    def mct(self, parsed_cmd):
        """Modify Current Card"""
        cmg = CMGSpawn(mw=self.mw)
        cmg.modify_current_card(parsed_cmd)

    def rcc(self, parsed_cmd):
        """Reverse Current Card"""
        cmg = CMGSpawn(mw=self.mw)
        cmg.reverse_current_card(parsed_cmd)

    def add(self, parsed_cmd):
        """Add Card"""
        cmg = CMGSpawn(mw=self.mw)
        cmg.add_card(parsed_cmd)

    def mcr(self, parsed_cmd):
        """Modify Card Result - allows modification of current score"""

        mistakes_one_side = [x[self.mw.side] for x in self.mw.mistakes_list]
        is_mistake = self.mw.get_current_card().iloc[self.mw.side] in mistakes_one_side
        is_wordsback_mode = self.mw.words_back != 0

        if not is_wordsback_mode:
            self.post_fcc("Card not yet checked")
        else:
            if is_mistake:
                mistake_index = mistakes_one_side.index(
                    self.mw.get_current_card().iloc[self.mw.side]
                )
                del self.mw.mistakes_list[mistake_index]
                self.mw.negatives -= 1
                self.mw.positives += 1
                self.post_fcc("Score modified to positive")
            else:
                self.mw.append_current_card_to_mistakes_list()
                self.mw.positives -= 1
                self.mw.negatives += 1
                self.post_fcc("Score modified to negative")

            self.mw.update_score_button()

    def dcc(self, parsed_cmd):
        """Delete current card - from set and from the file"""

        # check preconditions
        if self.mw.active_file.tmp or not self.mw.active_file.valid:
            self.post_fcc("Command available only for Valid Regular files")
            return

        # Get parameters before deletion
        current_word = self.mw.get_current_card().iloc[self.mw.side]
        self.mw.delete_current_card()
        dataset_ordered = db_conn.load_dataset(self.mw.active_file, do_shuffle=False)

        # modify source file
        dataset_ordered.drop(
            dataset_ordered.loc[
                dataset_ordered[dataset_ordered.columns[self.mw.side]] == current_word
            ].index,
            inplace=True,
        )
        if self.mw.active_file.kind == db_conn.KINDS.rev:
            db_conn.save_revision(dataset_ordered)
            self.post_fcc("Card removed from the set and from the file as well")
        elif self.mw.active_file.kind in {db_conn.KINDS.lng, db_conn.KINDS.mst}:
            msg = db_conn.save_language(dataset_ordered, self.mw.active_file)
            self.post_fcc("Card removed\n" + msg)

    def sis(self, parsed_cmd):
        """Show ILN Statistics"""
        self.post_fcc(f"{'File':^34} | New Cards")
        for k, v in config["ILN"].items():
            try:
                end = db_conn.get_lines_count(db_conn.files[k])
                nc = end - v
            except KeyError:
                nc = 0
            self.post_fcc(f"{k:<34} | {nc}")

    def efc(self, parsed_cmd):
        """Show EFC Table"""
        if self.mw.active_file.tmp:
            self.post_fcc("Unable to calculate EFC for a temporary file")
            return
        elif len(parsed_cmd) >= 2:
            signatures = parsed_cmd[1:]
        else:
            signatures = {self.mw.active_file.signature}
        db_conn.refresh()
        recommendations = self.mw.efc.get_efc_data(preds=True, signatures=signatures)
        efc_table = self.mw.efc.get_efc_table(recommendations)
        w = self.console.width() * 0.8
        printout = self.mw.fcc.caliper.make_table(
            data=efc_table,
            pixlim=[0.5 * w, 0.18 * w, 0.18 * w, 0.18 * w],
            align=["left", "right", "right", "right"],
        )
        db_conn.refresh()
        self.post_fcc(printout)

    def mcp(self, parsed_cmd):
        """Modify Config Parameter"""
        if len(parsed_cmd) == 3:
            key, new_val = parsed_cmd[1], parsed_cmd[2]
            if key in config.keys():
                if new_val.isnumeric():
                    new_val = float(new_val) if "." in new_val else int(new_val)
                elif isinstance(config[key], (list, set, tuple)):
                    new_val = config[key].__class__(new_val.split(","))
                config[key] = new_val
                self.mw.cft.config_manual_update(key=key, subdict=None)
                self.post_fcc(f"{key} set to {new_val}")
            else:
                self.post_fcc(
                    f"{key} not found in the config. Use 'sck' to list all available keys"
                )
        elif len(parsed_cmd) == 4:
            subdict, key, new_val = parsed_cmd[1], parsed_cmd[2], parsed_cmd[3]
            if isinstance(config.get(subdict), dict) and key in config[subdict].keys():
                if new_val.isnumeric():
                    new_val = float(new_val) if "." in new_val else int(new_val)
                elif isinstance(config[subdict][key], (list, set, tuple)):
                    new_val = config[subdict][key].__class__(new_val.split(","))
                config[subdict][key] = new_val
                self.mw.cft.config_manual_update(key=key, subdict=subdict)
                self.post_fcc(f"{key} of {subdict} set to {new_val}")
            else:
                self.post_fcc(
                    f"{subdict} not found in the config. Use 'sck' to list all available keys"
                )
        else:
            self.post_fcc(
                "mcp function expected following syntax: mcp *<dict> <key> <new_value>"
            )

    def sck(self, parsed_cmd):
        """Show Config Key"""
        headers = ["Dict", "Key", "Value"]
        content = flatten_dict(config, lim_chars=30)
        if len(parsed_cmd) == 1:
            msg = self.mw.fcc.caliper.make_table(
                data=content,
                pixlim=int(self.console.viewport().width()),
                headers=headers,
                align=["left", "left", "left"],
            )
        elif len(parsed_cmd) in (2, 3):
            if isinstance(config.get(parsed_cmd[1]), dict):
                content = [
                    i for i in content if re.search(parsed_cmd[1], i[0], re.IGNORECASE)
                ]
                if len(parsed_cmd) == 3:
                    content = [
                        i
                        for i in content
                        if re.search(parsed_cmd[2], i[1], re.IGNORECASE)
                    ]
            else:
                content = [
                    i for i in content if re.search(parsed_cmd[1], i[1], re.IGNORECASE)
                ]
            if content:
                msg = self.mw.fcc.caliper.make_table(
                    data=content,
                    pixlim=int(self.console.viewport().width()),
                    headers=headers,
                    align=["left", "left", "left"],
                )
            else:
                suffix = f" in dict {parsed_cmd[1]}" if len(parsed_cmd) == 3 else ""
                msg = f"Key {parsed_cmd[-1]} does not exist{suffix}"
        else:
            msg = "Invalid syntax. Expected: sck *<dict> <key>"
        self.post_fcc(msg)

    @require_regular_file
    def cfn(self, parsed_cmd):
        """Change File Name"""
        if len(parsed_cmd) < 2:
            self.post_fcc("cfn requires a filename arg")
            return
        new_filename = " ".join(parsed_cmd[1:])
        if not is_valid_filename(new_filename):
            self.post_fcc(f"Invalid filename: {new_filename}")
            return
        if new_filename in db_conn.get_all_files(use_basenames=True, excl_ext=True):
            self.post_fcc(f"File {new_filename} already exists!")
            return
        old_filepath = self.mw.active_file.filepath
        new_filepath = os.path.join(
            os.path.dirname(old_filepath), f"{new_filename}{self.mw.active_file.ext}"
        )
        self.mw.file_monitor_del_protected_path(old_filepath)
        os.rename(old_filepath, new_filepath)
        if self.mw.active_file.kind in db_conn.GRADED:
            db_conn.rename_signature(self.mw.active_file.signature, new_filename)
        if iln := config["ILN"].get(old_filepath):
            config["ILN"][new_filepath] = iln
            del config["ILN"][old_filepath]
        db_conn.update_fds()
        if old_filepath == config["SOD"]["last_file"]:
            if old_filepath in config["SOD"]["files_list"]:
                config["SOD"]["files_list"].remove(old_filepath)
                config["SOD"]["files_list"].append(new_filepath)
            self.mw.sod.sod.cli.update_file_handler(new_filepath)
        self.mw.initiate_flashcards(db_conn.files[new_filepath])
        fcc_queue.put_notification(
            "Filename and Signature changed successfully", lvl=LogLvl.important
        )

    def scs(self, parsed_cmd):
        """Show Current Signature"""
        self.post_fcc(self.mw.active_file.signature)

    def lor(self, parsed_cmd):
        """List Obsolete Revisions"""
        unique = set(db_conn.get_unique_signatures().values.tolist())
        available = set(s.signature for s in db_conn.files.values())
        for i, v in enumerate(available.difference(unique)):
            self.post_fcc(f"{i+1}. {v}")

    def gwd(self, parsed_cmd):
        """Get Window Dimensions"""
        w = self.mw.frameGeometry().width()
        h = self.mw.frameGeometry().height()
        self.post_fcc(f"W:{int(w)} H:{int(h)}")

    def pcc(self, parsed_cmd):
        """Pull Current Card"""
        new_data = db_conn.load_dataset(
            self.mw.active_file, seed=config["pd_random_seed"]
        )
        self.mw.active_file.data.iloc[self.mw.current_index, :2] = new_data.iloc[
            self.mw.current_index, :2
        ]
        self.mw.display_text(self.mw.get_current_card()[self.mw.side])

    def emo(self, parsed_cmd: list):
        """EFC Model Optimizer"""
        from EMO.init import EMOSpawn
        EMOSpawn(mw=self.mw)

    def err(self, parsed_cmd: list):
        """Raise an Exception"""
        raise Exception(f"{' '.join(parsed_cmd[1:])}")

    def gcw(self, parsed_cmd: list):
        """Get Character Width"""
        if len(parsed_cmd) < 2:
            self.post_fcc("GCL requires at least one character")
            return
        text = "".join(parsed_cmd[1:])
        if text == "space":
            text = "\u0020"
        elif text == "half-space":
            text = "\u2009"
        elif text == "ideographic-space":
            text = "\u3000"
        self.post_fcc((f"Pixel Length: {self.mw.fcc.caliper.strwidth(text)}"))

    def pcd(self, parsed_cmd: list):
        """Print Current Dataset"""
        if len(parsed_cmd) >= 2 and parsed_cmd[1].isnumeric():
            lim = min(int(parsed_cmd[1]), self.mw.active_file.data.shape[0])
            gsi = 2
        else:
            lim = self.mw.active_file.data.shape[0]
            gsi = 1
        if len(parsed_cmd) > gsi:
            grep = re.compile(
                " ".join(parsed_cmd[gsi:]).strip("'").strip('"'), re.IGNORECASE
            )
        else:
            grep = None
        out, sep = list(), " | "
        cell_args = {
            "pixlim": (
                0.94 * (config["geo"][0] - self.mw.fcc.caliper.strwidth(sep)) / 2
            ),
            "align": "left",
        }
        rng = (
            range(lim)
            if lim >= 0
            else range(
                self.mw.active_file.data.shape[0] - 1,
                self.mw.active_file.data.shape[0] + lim - 1,
                -1,
            )
        )
        for i in rng:
            c1 = self.mw.fcc.caliper.make_cell(
                self.mw.active_file.data.iloc[i, 0], **cell_args
            )
            c2 = self.mw.fcc.caliper.make_cell(
                self.mw.active_file.data.iloc[i, 1], **cell_args
            )
            out.append(f"{c1}{sep}{c2}")
        if lim < 0:
            out.reverse()
        if grep:
            out = [card for card in out if grep.search(card)]
        self.post_fcc("\n".join(out))

    def cac(self, parsed_cmd: list):
        """Clear Application Cache"""
        if len(parsed_cmd) == 2 and parsed_cmd[1] == "help":
            self.post_fcc("Available keys: files, fonts")
            return
        run_all = len(parsed_cmd) == 1
        key = parsed_cmd[1] if len(parsed_cmd) == 2 else None
        if run_all or key == "files":
            db_conn.update_fds()
            db_conn.refresh()
        if run_all or key == "fonts":
            self.mw.fcc.caliper.pixlen.cache_clear()
        if run_all or key == "efc":
            self.mw.efc._efc_last_calc_time = 0
        self.post_fcc("Reloaded cache")

    def ssf(self, parsed_cmd: list):
        """Show Scanned Files"""
        for fd in db_conn.files.values():
            self.post_fcc(
                (
                    "\n"
                    f"Filepath:  {fd.filepath}" + "\n"
                    f"Signature: {fd.signature}" + "\n"
                    f"Language:  {fd.lng}" + "\n"
                    f"Kind:      {fd.kind}"
                )
            )
        self.post_fcc("\n" + f"Files total: {len(db_conn.files)}")

    def clt(self, parsed_cmd: list):
        """Create Language Tree"""
        if len(parsed_cmd) < 3:
            self.post_fcc("Missing Arguments - new language id | native language id")
            return
        elif parsed_cmd[1] in config["languages"]:
            self.post_fcc(f"Language {parsed_cmd[1]} already exists")
            return
        db_conn.create_language_dir_tree(parsed_cmd[1])
        config["languages"].append(parsed_cmd[1])
        pd.DataFrame(
            columns=[parsed_cmd[1].lower(), parsed_cmd[2].lower()], data=[["-", "-"]]
        ).to_csv(
            db_conn.make_filepath(
                parsed_cmd[1], db_conn.LNG_DIR, f"{parsed_cmd[1]}.csv"
            ),
            index=False,
            encoding="utf-8",
            header=True,
            mode="w",
        )
        for msg in fcc_queue.dump_logs():
            self.post_fcc(f"[{msg.timestamp.strftime('%H:%M:%S')}] {msg.message}")
        self.post_fcc(f"Created new Language file: {parsed_cmd[1]}.csv")
        db_conn.update_fds()

    def eph(self, parsed_cmd: list):
        """Create Ephemeral Mistakes"""
        if not self.mw.is_recorded:
            self.post_fcc("All cards must be reviewed before running this command")
            return
        elif not self.mw.mistakes_list:
            self.post_fcc("No mistakes to save")
            return
        self.mw.switch_tab("main")
        self.mw.init_eph_from_mistakes()

    def cre(self, parsed_cmd: list):
        """Comprehensive Review"""
        if len(parsed_cmd) >= 2:
            if parsed_cmd[1] == "flush":
                self.mw._flush_cre()
                self.post_fcc("Flushed CRE queue")
            elif parsed_cmd[1].startswith("stat"):
                if config["CRE"]["count"]:
                    self.post_fcc(self.mw._get_cre_stat())
                else:
                    try:
                        diff_days = (
                            datetime.now()
                            - datetime.strptime(
                                config["CRE"]["prev"]["date"],
                                r"%Y-%m-%d %H:%M:%S",
                            )
                        ).days
                    except (TypeError, ValueError):
                        diff_days = "∞"
                    ld = config["CRE"]["prev"]["date"]
                    ts = format_seconds_to(
                        config["CRE"]["prev"]["time_spent"],
                        "hour",
                        sep=":",
                        int_name="hour",
                    )
                    rc = config["CRE"]["prev"]["count"]
                    try:
                        ac = (
                            config["CRE"]["prev"]["positives"]
                            / config["CRE"]["prev"]["cards_seen"]
                        )
                    except ZeroDivisionError:
                        ac = 0
                    self.post_fcc(
                        f"Last finished on {ld} ({diff_days} days ago) took {ts} to complete {rc} Revisions with {ac:.0%} accuracy"
                    )
            else:
                self.post_fcc("Unknown argument!")
        elif config["CRE"]["items"]:  # continue CRE queue
            next_rev = config["CRE"]["items"][-config["CRE"]["opt"]["reversed"]]
            self.mw.initiate_flashcards(db_conn.files[next_rev])
        else:  # initiate CRE queue
            revs = [fd.filepath for fd in db_conn.get_sorted_revisions()]
            if config["CRE"]["opt"]["random"]:
                shuffle(revs)
            config["CRE"]["items"] = revs
            config["CRE"]["count"] = len(revs)
            config["CRE"]["cards_seen"] = 0
            config["CRE"]["time_spent"] = 0
            config["CRE"]["positives"] = 0
            config["CRE"]["cards_total"] = db_conn.get_cards_total(
                [fd.signature for fd in db_conn.get_sorted_revisions()]
            )
            self.post_fcc(
                f"CRE initiated with {config['CRE']['cards_total']} cards in {config['CRE']['count']} revisions"
            )
            next_rev = config["CRE"]["items"][-config["CRE"]["opt"]["reversed"]]
            self.mw.initiate_flashcards(db_conn.files[next_rev])

    def cfg(self, parsed_cmd: list):
        """Configuration"""
        if len(parsed_cmd) < 2:
            self.post_fcc("cfg command requires at least 1 argument")
        elif parsed_cmd[1] == "save":
            config.save()
            self.post_fcc("Config saved")
        elif parsed_cmd[1] == "load":
            config.reload()
            self.post_fcc("Config reloaded")
        elif parsed_cmd[1] == "restart":
            self.mw.switch_tab("main")
            self.mw.cft._modify_file_monitor()
            self.mw.cft.config_manual_update()
            self.mw.restart_app()
            self.post_fcc("Application restarted")
            self.mw.fcc.open()
        else:
            self.post_fcc("Usage: cfg anyOf(save,load,restart)")

    def dbg(self, parsed_cmd: list):
        """Debug"""
        if len(parsed_cmd) > 1:
            text = " ".join(parsed_cmd[1:])
            self.mw.display_text(text)

    def dmp(self, parsed_cmd: list[str]):
        """Dump Session Data"""
        if self.mw.active_file.tmp and self.mw.active_file.data.shape[0] > 1:
            db_conn.create_tmp_file_backup()
        self.mw.create_session_snapshot()
        config.save()
        self.post_fcc("Dumped session data")
    
    def rmw(self, parsed_cmd: list):
        """Refresh Main Window"""
        self.mw.on_ldpi_change(96)
        self.post_fcc("GUI adjusted to system scaling")
