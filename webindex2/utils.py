from functools import reduce


def partition(iterable, predicate):
    """I have no idea how this works, but it does
    """
    return reduce(
        lambda x, y: x[not predicate(y)].append(y) or x,
        iterable,
        ([], [])
    )


async def read_file(path):
    async with path.open('rb') as fp:
        while True:
            buf = await fp.read(1024 * 64)
            if not buf:
                break
            yield buf