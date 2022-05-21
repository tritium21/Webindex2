from dataclasses import dataclass
from pathlib import Path # bug in aiopath requires we use pathlib as a workaround

from aiopath import AsyncPath, AsyncPurePosixPath

class MappedPath:
    def __init__(self, mount, path=None):
        self._mount = mount
        self._path = mount.root if path is None else AsyncPath(path)

    def with_path(self, path):
        return MappedPath(self._mount, path)

    @property
    def os_path(self):
        return self._path

    @property
    def url(self):
        return AsyncPurePosixPath('/', self._mount.mount) / self._path.relative_to(self._mount.root)

    @property
    def name(self):
        return self._path.name

    def relative_to(self, other):
        return self._path.relative_to(other)

    def is_relative_to(self, other):
        return self._path.is_relative_to(other)

    async def is_file(self):
        return await self._path.is_file()

    async def is_dir(self):
        return await self._path.is_dir()

    async def exists(self):
        return await self._path.exists()

    async def iterdir(self):
        async for item in self._path.iterdir():
            yield self.with_path(item)

    def __repr__(self):
        return f"<MappedPath {self._path}>"



class Filesystem:
    def __init__(self, mounts=None):
        self.mounts = [] if mounts is None else mounts

    async def iterdir(self):
        for mount in self.mounts:
            yield MappedPath(*mount)
    
    async def is_dir(self):
        return True

    async def is_file(self):
        return False
    
    async def exists(self):
        return True

    @property
    def url(self):
        return AsyncPurePosixPath('/')

    def navigate(self, path):
        parts = AsyncPurePosixPath(path).parts[1:]
        if not parts:
            return self
        mount_name, *segments = parts
        for mount in self.mounts:
            if mount_name == mount.mount:
                break
        else:
            raise FileNotFoundError()
        path = mount.root.joinpath(*segments)
        # https://github.com/alexdelorenzo/aiopath/issues/4
        # in the future, assuming the bug is squashed, wont have to round trip through
        # pathlib to resolve ... which would be nice.
        # once per request, not THAT bad
        if not Path(path).resolve().is_relative_to(mount.root):
            raise FileNotFoundError()
        return MappedPath(mount, path)


@dataclass
class Mount:
    mount: str
    root: AsyncPath
    accel: str

    def __post_init__(self):
        self.root = AsyncPath(Path(self.root).resolve())


if __name__ == '__main__':
    from asyncio import run
    fs = Filesystem([Mount('books', r"x:\finished", 'books_protected')])
    async def navigate(path):
        leaf = fs.navigate(path)
        if not (await leaf.exists()):
            raise FileNotFoundError(f"Path does not exist: {leaf}")
        if (await leaf.is_dir()):
            return [
                (node, node.url)
                async for node in leaf.iterdir()
            ]

        return [(leaf, leaf.url)]

    async def main():
        for line in await navigate('/books/[C] Non-Fiction'):
            print(line)
    run(main())