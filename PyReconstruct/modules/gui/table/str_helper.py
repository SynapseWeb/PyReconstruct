class SortStr():

    def __init__(self, s : str):
        self.s = s
    
    def __lt__(self, other):
        s_lower = self.s.lower()
        o_lower = other.s.lower()
        if s_lower == o_lower and self.s < other.s:
            return True
        elif s_lower < o_lower:
            return True
        return False
        
def lessThan(s1, s2):
    # check if the names are integers
    if s1.isnumeric() and s2.isnumeric():
        return int(s1) < int(s2)
    else:
        return SortStr(s1) < SortStr(s2)

def sortList(l):
    ls = [SortStr(s) for s in l]
    ls.sort()
    return [ss.s for ss in ls]