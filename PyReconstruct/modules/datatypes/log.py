import re
from datetime import datetime

from PyReconstruct.modules.constants import getDateTime

class Log():

    def __init__(self, date : str, time : str, user : str, obj_name : str, section, event : str):
        """Create a single log entry.
        
            Params:
                date (str): the date of the log creation YY-MM-DD
                time (str): the time of the log creation HHMM
                user (str): the username of the person making the log
                obj_name (str): the name of the object being modified
                section (int OR list): the section or section ranges of the log
                event (str): the description of what happened
        """
        self.date = date
        self.time = time
        self.user = user
        self.obj_name = obj_name
        if type(section) is int:
            self.section_ranges = [(section, section)]
        elif type(section) is list:
            self.section_ranges = section
        elif section is None:
            self.section_ranges = None
        self.event = event
    
    def __eq__(self, other):
        """Compare log objects.
        
            Params:
                other (Log): the log to compare to
        """
        return str(self) == str(other)
    
    def __str__(self):
        if not self.obj_name:
            obj_name = "-"
        else:
            obj_name = self.obj_name
        
        if not self.section_ranges:
            section_ranges = "-"
        else:
            section_ranges = []
            for srange in self.section_ranges:
                if srange[0] == srange[1]:
                    section_ranges.append(str(srange[0]))
                else:
                    section_ranges.append(f"{srange[0]}-{srange[1]}")
            section_ranges = " ".join(section_ranges)

        return f"{self.date}, {self.time}, {self.user}, {obj_name}, {section_ranges}, {self.event}"
    
    def fromStr(s : str):
        """Get a log object from a string.
        
            Params:
                s (str): the string
        """
        l = s.split(", ")

        # check for commas in event
        if len(l) > 6:
            l[5] = ", ".join(l[5:])
            l = l[:6]

        (
            date,
            time,
            user,
            obj_name,
            section_ranges,
            event
        ) = tuple(l)
        if obj_name == "-":
            obj_name = None

        if section_ranges == "-":
            section_ranges = None
        else:
            srs = section_ranges.split(" ")
            section_ranges = []
            for sr in srs:
                ends = sr.split("-")
                if len(ends) == 1:
                    section_ranges.append((int(sr), int(sr)))
                else:
                    section_ranges.append((int(ends[0]), int(ends[1])))
        
        return Log(date, time, user, obj_name, section_ranges, event.strip())
    
    def checkSectionRanges(self):
        """Iterate through the section ranges and combine adjacent ones."""
        i = 0
        while i < len(self.section_ranges) - 1:
            current = self.section_ranges[i]
            next = self.section_ranges[i+1]
            if current[1] >= next[0] - 1:
                new = (min(current + next), max(current + next))
                self.section_ranges[i] = new
                self.section_ranges.pop(i+1)
            else:
                i += 1
    
    def addSection(self, snum : int):
        """Add a section number to the section range.
        
            Params:
                snum (int) the section number to add
        """
        if self.section_ranges is None:
            raise Exception("Cannot add section number to non section-specific log.")
        loop_broken = True
        for i, srange in enumerate(self.section_ranges):
            loop_broken = True
            if snum < srange[0]:
                if snum == srange[0] - 1:
                    self.section_ranges[i] = (snum, srange[1])
                else:
                    self.section_ranges.insert(i, (snum, snum))
                break
            elif srange[0] <= snum <= srange[1]:
                break
            elif snum == srange[1] + 1:
                self.section_ranges[i] = (srange[0], snum)
                break
            loop_broken = False
        
        if not loop_broken:
            self.section_ranges.append((snum, snum))
        
        self.checkSectionRanges()
    
    def containsSection(self, snum : int):
        """Check if the logs section range contains the given section number.
        
            Params:
                snum (int): the section number
        """
        if not self.section_ranges:
            return False
        
        for n1, n2 in self.section_ranges:
            if snum in range(n1, n2+1):
                return True
        
        return False
    
    def trimSectionRange(self, srange):
        """Trim the section range of the log."""
        if not self.section_ranges:
            self.section_ranges = [(srange[0], srange[1]-1)]
            return True
        else:
            sections = range(*srange)
            new_section_ranges = []
            for s1, s2 in self.section_ranges.copy():
                if s1 and s2 in sections:
                    new_section_ranges.append((s1, s2))
                elif s1 in sections:
                    new_section_ranges.append((s1, srange[1]-1))
                elif s2 in sections:
                    new_section_ranges.append(srange[0], s2)
                elif s1 < srange[0] and s2 >= srange[1]:
                    new_section_ranges.append((srange[0], srange[1]-1))
            if new_section_ranges:
                self.section_ranges = new_section_ranges
                return True
            else:
                return False


class LogSet():

    def __init__(self):
        """Create the log set."""
        self.dyn_logs = {}  # organized by name and event
        self.all_logs = []
    
    def addLog(self, user : str, obj_name : str, snum : int, event : str):
        """Add a log to the set.
        
            Params:
                user (str): the user creating the log
                obj_name (str): the name of the object associated with the log
                snum (int): the section number associated with the log
                event (str): the description of the event
        """
        # compare the user to the last log
        if self.all_logs and user != self.all_logs[-1].user:
            # clear dynamic log if so
            self.dyn_logs = {}
        
        if snum is not None:  # dynamic log
            obj_key = obj_name if obj_name else "-"
            if obj_key in self.dyn_logs and event in self.dyn_logs[obj_key]:
                self.dyn_logs[obj_key][event].addSection(snum)
            else:
                if obj_key not in self.dyn_logs:
                    self.dyn_logs[obj_key] = {}
                d, t = getDateTime()
                l = Log(d, t, user, obj_name, snum, event)
                self.all_logs.append(l)
                self.dyn_logs[obj_key][event] = l
        else:  # static log
            d, t = getDateTime()
            log = Log(d, t, user, obj_name, snum, event)

            # special cases: creating or deleting an object
            if event == "Create object":
                # check the previous log to see if traces were created
                if (
                    self.all_logs and
                    self.all_logs[-1].obj_name == obj_name and 
                    "Create trace(s)" in self.all_logs[-1].event):
                    event = self.all_logs[-1].event
                    self.all_logs[-1].event = event.replace("trace(s)", "object")
                else:
                    self.all_logs.append(log)
            elif event == "Delete object":
                # remove object from dynamic log
                if obj_name in self.dyn_logs:
                    del(self.dyn_logs[obj_name])
                # remove all previous logs associated with the object
                for l in self.all_logs.copy():
                    if l.obj_name == obj_name and "Create object" not in l.event:
                        self.all_logs.remove(l)
                self.all_logs.append(log)
            # non-special cases
            else:
                self.all_logs.append(log)
        
        # # for debugging
        # # Clear console
        # if os.name == 'nt':  # Windows
        #     _ = os.system('cls')
        # else:  # Mac and Linux
        #     _ = os.system('clear')
        # print(str(self).replace(", ", "\t"))
    
    def addExistingLog(self, log : Log, track_dyn=False):
        """Add an existing log object to the set.
        
            Params:
                log (Log): the log to add to the set
                track_dyn (bool): True if log should be dynamically tracked
        """
        self.all_logs.append(log)
        if track_dyn:
            if log.section_ranges:
                obj_key = log.obj_name if log.obj_name else "-"
                if obj_key not in self.dyn_logs:
                    self.dyn_logs[obj_key] = {}
                self.dyn_logs[obj_key][log.event] = log
    
    def getLogList(self, as_str=False):
        """Return the stored logs as a list.
        
            Params:
                as_str (bool): True if the log should be returned in str format
            Returns:
                the log list in list or str format
        """
        if as_str:
            logs_str = []
            for log in self.all_logs:
                logs_str.append(str(log))
            return "\n".join(logs_str)
        else:
            return self.all_logs.copy()
    
    def __str__(self):
        return self.getLogList(as_str=True)

    def getList(self) -> list:
        """Return log set as a list"""
        log_list = self.getLogList()
        for i, log in enumerate(log_list):
            log_list[i] = str(log)
        
        return log_list
    
    def fromList(log_list : list):
        """Get a log set from a list.
        
            Params:
                log_list (list): the list representation of the logs
        """
        log_set = LogSet()
        i = 0
        while i < len(log_list):
            log_str = log_list[i]
            if log_str.strip():
                # check for corrupt log strings (return key in name)
                while len(log_str.split(",")) < 6:
                    log_str += log_list[i+1].strip()
                    i += 1
                log = Log.fromStr(log_str)
                log_set.addExistingLog(log)
            i += 1
        
        return log_set
    
    def removeCuration(self, obj_name : str):
        """Remove all curation logs in the session.
        
            Params:
                obj_name (str): the name of the object to remove curation for
        """
        for log in self.all_logs.copy():
            if (obj_name == log.obj_name and 
                ("curated" in log.event or "curation" in log.event)):
                self.all_logs.remove(log)
    
    def getLastIndex(self, snum : int, cname : str):
        """Scan the history and return the date for a contour on a given section.
        
            Params:
                snum (int): the section number
                cname (str): the contour name
        """
        i = len(self.all_logs) - 1
        for log in reversed(self.all_logs):
            if (
                log.obj_name == cname and 
                ("ztrace" not in log.event) and 
                (log.containsSection(snum) or (log.section_ranges is None))
            ):
                return i
            i -= 1
        return i

class LogSetPair():

    def __init__(self, logset0 : LogSet, logset1 : LogSet):
        """Create a logset pair (ideally when dealing with two series).
        
            Params:
                logset1 (LogSet): the first logset (usually self)
                logset2 (LogSet): the second logset (usually other)
        """
        self.logset0 = logset0
        self.logset1 = logset1

        # get the index for the diverge
        i = 0
        while (
            i < len(self.logset0.all_logs) and
            i < len(self.logset1.all_logs) and
            self.logset0.all_logs[i] == self.logset1.all_logs[i]
        ):
            i += 1
        
        self.last_shared_index = i-1

        self.complete_match = (
            i == len(self.logset0.all_logs) == len(self.logset1.all_logs)
        )
    
    def importLogs(
        self,
        series,
        traces=True,
        ztraces=True,
        srange=None,
        regex_filters=[],
    ):
        """
        Import the history data from the other logset into the series logset

            Params:
                series (Series): the series to modify the history for
                traces (bool): True if trace history should be imported
                ztraces (bool): True if the ztrace history should be imported
                srange (tuple): the range of sections (exclusive)
                regex_filters (list): the list of regex filters used to filter names
        """
        # filter out similar history
        for i in range(self.last_shared_index + 1, len(self.logset1.all_logs)):
            log = self.logset1.all_logs[i]

            # check for trace/ztrace status
            include_log = traces and ("ztrace" not in log.event)
            include_log |= ztraces and ("ztrace" in log.event)
            include_log &= bool(log.obj_name)
            if not include_log:
                continue  # skip if not desired status

            # check filters
            passes_filters = False if regex_filters else True
            for rf in regex_filters:
                if bool(re.fullmatch(rf, log.obj_name)):
                    passes_filters = True
            if not passes_filters: 
                continue # skip if does not pass filters

            # trim section range and check if contains sections within range
            if srange and not log.trimSectionRange(srange):
                continue

            # update both the self series logs
            series.log_set.addExistingLog(log)
            self.logset0.addExistingLog(log)
        
        if traces:
            # iterate through the series log and update the last users
            last_user_data = {}  # obj_name : (user, datetime)
            for log in self.logset0.all_logs[self.last_shared_index+1:]:
                log : Log
                if log.obj_name and ("ztrace" not in log.event):
                    user0, dt0 = log.user, (log.date + log.time)
                    # if obj name exists in data, check against date
                    if log.obj_name in last_user_data:
                        user1, dt1 = last_user_data[log.obj_name]
                        if dt0 >= dt1:
                            last_user_data[log.obj_name] = (user0, dt0)
                    # if it does not exist in data so far, store
                    else:
                        last_user_data[log.obj_name] = (user0, dt0)
            
            # update the series attributes
            for obj_name, (user, dt) in last_user_data.items():
                series.setAttr(obj_name, "last_user", user)
    
    def getModifiedSinceDiverge(self, cname : str, snum : int):
        """Get the information on which contours have been modified since diverge.
            Params:
                cname (str): the name of the contour to check
                snum (int): the section number of the contour
            Returns:
                (tuple): logset0 True/False, logset1 True/False
        """
        # determine which series have been modified since diverge
        modified_since_diverge = [False, False]
        for i, ls in enumerate((self.logset0, self.logset1)):
            last_index = ls.getLastIndex(snum, cname)
            if last_index > self.last_shared_index:
                modified_since_diverge[i] = True
        return tuple(modified_since_diverge)
