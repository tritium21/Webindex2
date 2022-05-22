from functools import reduce

def partition(iterable, predicate):
    """I have no idea how this works, but it does
    """
    return reduce(
        lambda x, y: x[not predicate(y)].append(y) or x,
        iterable,
        ([], [])
    )