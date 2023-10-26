class Flag():

    def __init__(self, name, x, y, color, comments=[]):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.comments = [tuple(c) for c in comments]
    
    def getList(self):
        return [self.name, self.x, self.y, self.color, self.comments]
    
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
        return Flag(self.name, self.x, self.y, self.color, self.comments.copy())

    def __lt__(self, other):
        return self.name < other.name

    def equals(self, other):
        return (
            self.name == other.name and
            abs(self.x - other.x) < 1e-6 and
            abs(self.y - other.y) < 1e-6 and
            self.color == other.color and
            self.comments == other.comments
        )
    
