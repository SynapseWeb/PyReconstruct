import os
from datetime import datetime

class TraceLog():

    def __init__(self, *args):
        """Create a new trace log.
        
            Params:
                (str): the message for the log
                OR
                (list): the dateimte, username, message for the log
        """
        if type(args[0]) is str:
            self.message = args[0]
            self.username = "user"
            t = datetime.now()
            self.dt = f"{t.year}{t.month:02d}{t.day:02d}_{t.hour:02d}{t.minute:02d}{t.second:02d}."
            self.dt += f"{t.microsecond:06d}"[0]
        elif type(args[0]) is list or type(args[0]) is tuple:
            self.dt = args[0][0]
            self.username = args[0][1]
            self.message = args[0][2]
    
    def __str__(self):
        return f"{self.dt} {self.username} {self.message}"
    
    def __iter__(self):
        return [self.dt, self.username, self.message].__iter__()
    
    def __gt__(self, other):
        """Sort by more recent."""
        return self.dt > other.dt
    
    def __lt__(self, other):
        """Sort by more remote."""
        return self.dt < other.dt
    
    def copy(self):
        return TraceLog(list(self).copy())
