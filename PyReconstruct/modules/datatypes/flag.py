from datetime import datetime

class Flag():

    def __init__(self, name : str, x : int, y : int, color : tuple, comments=None, resolved=False):
        """Create a flag object.
        
            Params:
                name (str): the name of the flag
                x (int): the x-coord for the flag
                y (int): the y-coord for the flag
                color (tuple): the the color of the flag
                comments (list): the list of flag comments
                resolved (bool): True if the flag is resolved
        """
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        if comments:
            self.comments = comments
        else:
            self.comments = []
        self.resolved = resolved
    
    def addComment(self, user : str, text : str):
        """Add a comment to the flag.
        
            Params:
                user (str): the user who created the comment
                text (str): the comment text
        """
        self.comments.append(Comment(user, text))
    
    def getList(self) -> list:
        """Returns the flag in a list representation."""
        return [self.name, self.x, self.y, self.color, [c.getList() for c in self.comments], self.resolved]
    
    def fromList(l : list):
        """Create a flag object from a list.
        
            Params:
                l (list): the list
        """
        (
            title,
            x,
            y,
            color,
            comments,
            resolved
        ) = tuple(l)
        comments = [Comment.fromList(c) for c in comments]
        return Flag(title, x, y, color, comments, resolved)
    
    def copy(self):
        """Returns a copy of the current flag."""
        return Flag(
            self.name, 
            self.x, 
            self.y, 
            self.color, 
            [c.copy() for c in self.comments],
            self.resolved
        )

    def __lt__(self, other):
        return self.name < other.name

    def equals(self, other):
        """Compare flag objects.
        
            Params:
                other (Flag): the flag to compare to
        """
        return (
            self.name == other.name and
            abs(self.x - other.x) < 1e-6 and
            abs(self.y - other.y) < 1e-6 and
            self.color == other.color and
            len(self.comments) == len(other.comments) and
            all([sc.equals(oc) for sc, oc in zip(self.comments, other.comments)]),
            self.resolved == other.resolved
        )

def getDateTime():
    dt = datetime.now()
    d = f"{dt.year % 1000}-{dt.month:02d}-{dt.day:02d}"
    t = f"{dt.hour:02d}:{dt.minute:02d}"
    return d, t

class Comment():

    def __init__(self, user : str, text : str, date : str = None, time : str = None):
        """Create the flag comment object.
        
            Params:
                user (str): the user who created the comment
                text (str): the text of the comment
                date (str): the date of the comment's creation
                time (str): the time of the comment's creation
        """
        self.user = user
        self.text = text
        if not date or not time:
            self.date, self.time = getDateTime()
        else:
            self.date = date
            self.time = time
    
    def getList(self) -> list:
        """Get the flag comment object as a list."""
        return [self.user, self.text, self.date, self.time]

    def fromList(l : list):
        """Create a flag comment object from a list.
        
            Params:
                l (list): the list
        """
        return Comment(*tuple(l))
    
    def copy(self):
        """Returns a copy of the current flag comment."""
        return Comment(self.user, self.text, self.date, self.time)

    def equals(self, other):
        """Compare flag comment objects.
        
            Params:
                other (Comment): the comment to compare to
        """
        return (
            self.user == other.user,
            self.text == other.text,
            self.date == other.date,
            self.time == other.time
        )

    
