from datetime import datetime
import random

from PyReconstruct.modules.constants import getDateTime

possible_chars = (
    [chr(n) for n in range(65, 91)] +
    [chr(n) for n in range(97, 123)] +
    [chr(n) for n in range(48, 58)]
)

class Flag():

    def __init__(self, name : str, x : int, y : int, section_number : int, color : tuple, comments=None, resolved=False, id=None):
        """Create a flag object.
        
            Params:
                name (str): the name of the flag
                x (int): the x-coord for the flag
                y (int): the y-coord for the flag
                section_number (int): the section number for the flag
                color (tuple): the the color of the flag
                comments (list): the list of flag comments
                resolved (bool): True if the flag is resolved
        """
        self.name = name
        self.x = x
        self.y = y
        self.snum = section_number
        self.color = color

        if comments:
            self.comments = comments
        else:
            self.comments = []
        self.resolved = resolved

        if not id:
            self.id = Flag.generateID()
        else:
            self.id = id
    
    def addComment(self, user : str, text : str):
        """Add a comment to the flag.
        
            Params:
                user (str): the user who created the comment
                text (str): the comment text
        """
        self.comments.append(Comment(user, text))
    
    def getList(self) -> list:
        """Returns the flag in a list representation."""
        return [
            self.id, 
            self.name, 
            self.x, 
            self.y, 
            self.color, 
            [c.getList() for c in self.comments], 
            self.resolved
        ]
    
    def fromList(l : list, snum : int):
        """Create a flag object from a list.
        
            Params:
                l (list): the list
                snum (int): the section containing the flag
        """
        (
            id,
            title,
            x,
            y,
            color,
            comments,
            resolved
        ) = tuple(l)
        comments = [Comment.fromList(c) for c in comments]
        return Flag(title, x, y, snum, color, comments, resolved, id)
    
    def copy(self):
        """Returns a copy of the current flag."""
        return Flag(
            self.name, 
            self.x, 
            self.y, 
            self.snum,
            self.color, 
            [c.copy() for c in self.comments],
            self.resolved,
            self.id
        )

    def __lt__(self, other):
        return self.name < other.name

    def equals(self, other):
        """Compare flag objects.
        
            Params:
                other (Flag): the flag to compare to
        """
        return self.id == other.id

    def resolve(self, user : str, resolved=True):
        """Resolve or unresolve the flag.
        
            Params:
                user (str): the user that is modifying the flag
                resolved (bool): the resolve status for the flag
        """
        # if no change, do nothing
        if resolved == self.resolved:
            return
        
        if resolved:
            self.addComment(user, "Marked as resolved")
        else:
            self.addComment(user, "Marked as unresolved")
        self.resolved = resolved
    
    def generateID():
        """Generate an ID for a flag."""
        id = ""
        for _ in range(6): id += random.choice(possible_chars)
        return id

    def magScale(self, prev_mag : float, new_mag : float):
        """Adjust the flag position to a new magnification.
        
            Params:
                prev_mag (float): the previous magnification
                new_mag (float): the new magnification being set
        """
        self.x *= new_mag / prev_mag
        self.y *= new_mag / prev_mag

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

    
