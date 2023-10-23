class Flag():

    def __init__(self, title, x, y, color, comments=[]):
        self.title = title
        self.x = x
        self.y = y
        self.color = color
        self.comments = comments
    
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
    
