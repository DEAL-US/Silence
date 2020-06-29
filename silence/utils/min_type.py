# https://stackoverflow.com/questions/12971631/sorting-list-by-an-attribute-that-can-be-none
from functools import total_ordering

# An object that compares as less than anything else regardless of their type
@total_ordering
class MinType(object):
    
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return (self is other)

Min = MinType()
