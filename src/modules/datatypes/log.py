import os
from datetime import datetime

def getDateTime():
    dt = datetime.now()
    d = f"{dt.year % 1000}-{dt.month:02d}-{dt.day:02d}"
    t = f"{dt.hour:02d}:{dt.minute:02d}"
    return d, t


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
        return (
            self.date == other.date and
            self.time == other.time and
            self.user == other.user and
            self.obj_name == other.obj_name and
            self.section_ranges == other.section_ranges and
            self.event == other.event
        )
    
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
        
        return Log(date, time, user, obj_name, section_ranges, event)
    
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


class LogSet():

    def __init__(self):
        """Create the log set."""
        self.dyn_logs = {}  # organized by name and event
        self.all_logs = []
    
    def addLog(self, user : str, obj_name : str, snum : int, event : str):
        """Add a log to the set."""
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
                if self.all_logs and "Create trace(s)" in self.all_logs[-1].event:
                    self.all_logs.insert(len(self.all_logs)-1, log)
                else:
                    self.all_logs.append(log)
            elif event == "Delete object":
                # remove object from dynamic log
                if obj_name in self.dyn_logs:
                    del(self.dyn_logs[obj_name])
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
        """Add an existing log object to the set."""
        self.all_logs.append(log)
        if track_dyn:
            if log.section_ranges:
                obj_key = log.obj_name if log.obj_name else "-"
                if obj_key not in self.dyn_logs:
                    self.dyn_logs[obj_key] = {}
                self.dyn_logs[obj_key][log.event] = log
    
    def getLogList(self, as_str=False):
        """Return the stored logs as a list."""
        if as_str:
            logs_str = []
            for log in self.all_logs:
                logs_str.append(str(log))
            return "\n".join(logs_str)
        else:
            return self.all_logs.copy()
    
    def __str__(self):
        return self.getLogList(as_str=True)

    def getList(self):
        """Return log set as a list."""
        log_list = self.getLogList()
        for i, log in enumerate(log_list):
            log_list[i] = str(log)
        
        return log_list
    
    def fromList(log_list : list):
        """Get a log set from a list."""
        log_set = LogSet()
        for log_str in log_list:
            log = Log.fromStr(log_str)
            log_set.addExistingLog(log)
        
        return log_set


        


        
