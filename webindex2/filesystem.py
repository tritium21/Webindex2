from dataclasses import dataclass
from datetime import datetime
from mimetypes import guess_type
from pathlib import Path as PLPath

from aiopath import AsyncPath, AsyncPurePosixPath
from async_property import async_property

@dataclass
class Mount:
    mount: str
    root: AsyncPath
    accel: str = ''

    def __post_init__(self):
        self.root = AsyncPath(PLPath(self.root).resolve())


@dataclass
class Path:
    name: str
    url: str
    x_accel_redirect_url: str
    is_dir: bool
    mimetype: str
    mimeclass: str
    modified: datetime
    size: int
    os_path: AsyncPath
    mount: Mount

    async def iterdir(self):
        async for item in self.os_path.iterdir():
            yield await self.with_path(item)

    async def with_path(self, path=None):
        if path is None:
            return self.from_mount(self.mount)
        return await self.from_path(path, self.mount)

    @async_property
    async def parents(self):
        return [await self.with_path(p) for p in self.os_path.parents if p.is_relative_to(self.mount.root)][:-1]

    @async_property
    async def crumbs(self):
        if self.name == '':
            return [self.home()]
        result = [r for r in await self.parents]
        result += [await self.with_path(), self.home()]
        if self.os_path != self.mount.root:
            result = [self] + result
        return list(reversed(result))

    async def rglob(self, *p, **kw):
        return await self.os_path.rglob(*p, **kw)

    def relative_to(self, other):
        return self.os_path.relative_to(other)

    def is_relative_to(self, other):
        return self.path.is_relative_to(other)

    @classmethod
    async def from_path(cls, path, mount):
        path = AsyncPath(path)
        name = path.name
        is_dir = await path.is_dir()
        url = str(AsyncPurePosixPath(mount.mount) / path.relative_to(mount.root))
        _stat = await path.stat()
        modified = datetime.fromtimestamp(_stat.st_mtime)
        x_accel_redirect_url = ''
        if not is_dir:
            size = _stat.st_size
            mimetype = guess_type(name)[0]
            mimetype = mimetype if mimetype is not None else 'application/octet-stream'
            mimeclass = mimetype.split('/')[0]
            if mount.accel:
                x_accel_redirect_url = str(AsyncPurePosixPath(mount.accel) / path.relative_to(mount.root))
        else:
            size = 0
            mimetype = ''
            mimeclass = 'directory'
        return cls(
            name=name,
            size=size,
            modified=modified,
            is_dir=is_dir,
            mimetype=mimetype,
            mimeclass=mimeclass,
            url=url,
            x_accel_redirect_url=x_accel_redirect_url,
            os_path=path,
            mount=mount,
        )

    @classmethod
    def from_mount(cls, mount):
        path = mount.root
        name = mount.mount
        size = 0
        is_dir = True
        modified = datetime.now()
        mimetype = ''
        mimeclass = 'directory'
        url = mount.mount
        x_accel_redirect_url = ''
        return cls(
            name=name,
            size=size,
            modified=modified,
            is_dir=is_dir,
            mimetype=mimetype,
            mimeclass=mimeclass,
            url=url,
            x_accel_redirect_url=x_accel_redirect_url,
            os_path=path,
            mount=mount,
        )

    @classmethod
    def home(cls):
        return cls(
            name='',
            size=0,
            modified=datetime.now(),
            is_dir=True,
            mimetype='',
            mimeclass='directory',
            url='',
            x_accel_redirect_url='',
            os_path=None,
            mount=None,
        )


class Filesystem:
    name = ''
    url = ''
    x_accel_redirect_url = ''
    is_dir = True
    mimetype = ''
    mimeclass = 'directory'
    modified = datetime.now()
    size = 0
    os_path = None
    mount = None

    @async_property
    async def crumbs(self):
        return [Path.home()]

    def __init__(self, mounts=None):
        self.mounts = [] if mounts is None else mounts

    async def iterdir(self):
        for mount in self.mounts:
            yield Path.from_mount(mount)

    def add_mount(self, mount, root, accel):
        self.mounts.append(Mount(mount, root, accel))

    @classmethod
    def from_spec(cls, spec):
        if not spec:
            return cls()
        return cls([Mount(*(l.strip().split('|')[:3])) for l in spec.splitlines()])


    async def navigate(self, path):
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
        if not PLPath(path).resolve().is_relative_to(mount.root):
            raise FileNotFoundError()
        return await Path.from_path(path, mount)
