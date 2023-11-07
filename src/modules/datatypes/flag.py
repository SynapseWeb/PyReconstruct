from datetime import datetime

class Flag():

    def __init__(self, name, x, y, color, comments=None, resolved=False):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        if comments:
            self.comments = comments
        else:
            self.comments = []
        self.resolved = resolved
    
    def addComment(self, user, text):
        self.comments.append(Comment(user, text))
    
    def getList(self):
        return [self.name, self.x, self.y, self.color, [c.getList() for c in self.comments], self.resolved]
    
    def fromList(l):
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

    def __init__(self, user, text, date=None, time=None):
        self.user = user
        self.text = text
        if not date or not time:
            self.date, self.time = getDateTime()
        else:
            self.date = date
            self.time = time
    
    def getList(self):
        return [self.user, self.text, self.date, self.time]

    def fromList(l):
        return Comment(*tuple(l))
    
    def copy(self):
        return Comment(self.user, self.text, self.date, self.time)

    def equals(self, other):
        return (
            self.user == other.user,
            self.text == other.text,
            self.date == other.date,
            self.time == other.time
        )

    
