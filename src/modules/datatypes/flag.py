class Flag():

    def __init__(self, x, y, color, comments=[]):
        self.x = x
        self.y = y
        self.color = color
        self.comments = comments
    
    def getList(self):
        return [self.x, self.y, self.color, self.comments]
    
    def fromList(l):
        (
            x,
            y,
            color,
            comments
        ) = tuple(l)
        return Flag(x, y, color, comments)
    
    def copy(self):
        return Flag(self.x, self.y, self.color, self.comments.copy())
    
