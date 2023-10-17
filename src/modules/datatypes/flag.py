class Flag():

    def __init__(self, x, y, color, comment):
        self.x = x
        self.y = y
        self.color = color
        self.comment = comment
    
    def getList(self):
        return [self.x, self.y, self.color, self.comment]
    
    def fromList(l):
        (
            x,
            y,
            color,
            comment
        ) = tuple(l)
        return Flag(x, y, color, comment)
    
    def copy(self):
        return Flag(self.x, self.y, self.color, self.comment)
    
