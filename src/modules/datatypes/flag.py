class Flag():

    def __init__(self, x, y, color, comment, user):
        self.x = x
        self.y = y
        self.color = color
        self.comment = comment
        self.user = user
    
    def getList(self):
        return [self.x, self.y, self.color, self.comment, self.user]
    
    def fromList(l):
        (
            x,
            y,
            color,
            comment,
            user
        ) = tuple(l)
        return Flag(x, y, color, comment, user)
    
    def copy(self):
        return Flag(self.x, self.y, self.color, self.comment, self.user)
    
