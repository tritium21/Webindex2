import datetime
from dataclasses import dataclass
from pathlib import Path # bug in aiopath requires we use pathlib as a workaround

from aiopath import AsyncPath, AsyncPurePosixPath

from .mime import guess_type

class Home:
    def __init__(self):
        self.name = ''
        self.url = ''
        self.is_dir = True

class MappedPath:
    def __init__(self, mount, path=None, name=None):
        self._mount = mount
        self._path = mount.root if path is None else AsyncPath(path)
        self._name = self._path.name if name is None else name

    def with_path(self, path=None):
        name = None
        if path is None:
            name = self._mount.mount
        return MappedPath(self._mount, path, name)

    @property
    def os_path(self):
        return self._path

    @property
    def crumbs(self):
        parents = [self.with_path(p) for p in self._path.parents]
        result = [r for r in parents if r.is_relative_to(self._mount.root)][:-1] + [self.with_path(), Home()]
        if self._path != self._mount.root:
            result = [self] + result
        crumbs = list(reversed(result))
        print([(p.name, p) for p in crumbs])
        return crumbs

    @property
    def url(self):
        return str(AsyncPurePosixPath(self._mount.mount) / self._path.relative_to(self._mount.root))

    @property
    def x_accel_redirect_url(self):
        return AsyncPurePosixPath(self._mount.accel) / self._path.relative_to(self._mount.root)

    @property
    def name(self):
        return self._name

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

    async def stat(self):
        return await self._path.stat()

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
            yield MappedPath(mount, name=mount.mount)
    
    async def is_dir(self):
        return True

    async def is_file(self):
        return False
    
    async def exists(self):
        return True

    @property
    def url(self):
        return ''

    @property
    def crumbs(self):
        return [Home()]

    def navigate(self, path):
        parts = AsyncPurePosixPath(path.strip('/')).parts
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


@dataclass
class Item:
    name: str
    is_dir: bool
    size: int
    modified: datetime.datetime
    url: str
    mimetype: str
    mimeclass: str

    @classmethod
    async def from_path(cls, path):
        name = path.name
        is_dir = await path.is_dir()
        stat = (await path.stat())
        size = stat.st_size
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)
        url = path.url
        if not is_dir:
            mimetype = guess_type(name)[0]
            mimetype = mimetype if mimetype is not None else 'application/octet-stream'
            mimeclass = mimetype.split('/')[0]
        else:
            mimetype = ''
            mimeclass = 'directory'
        return cls(name, is_dir, size, modified, url, mimetype, mimeclass)