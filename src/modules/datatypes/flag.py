class Flag():

    def __init__(self, title, x, y, color, comments=[]):
        self.title = title
        self.x = x
        self.y = y
        self.color = color
        self.comments = [tuple(c) for c in comments]
    
    def getList(self):
        return [self.title, self.x, self.y, self.color, self.comments]
    
    def fromList(l):
        (
            title,
            x,
            y,
            color,
            comments
        ) = tuple(l)
        return Flag(title, x, y, color, comments)
    
    def copy(self):
        return Flag(self.title, self.x, self.y, self.color, self.comments.copy())

    def __lt__(self, other):
        return self.title < other.title

    def equals(self, other):
        return (
            self.title == other.title and
            abs(self.x - other.x) < 1e-6 and
            abs(self.y - other.y) < 1e-6 and
            self.color == other.color and
            self.comments == other.comments
        )
    
