from io import RawIOBase
from time import localtime
from zipfile import ZipFile, ZipInfo

from aiopath import AsyncPath

from .utils import read_file


class Stream(RawIOBase):
    """An unseekable stream for the ZipFile to write to"""

    def __init__(self):
        self._buffer = bytearray()
        self._closed = False

    def close(self):
        self._closed = True

    def write(self, b):
        if self._closed:
            raise ValueError("Can't write to a closed stream")
        self._buffer += b
        return len(b)

    def readall(self):
        chunk = bytes(self._buffer)
        self._buffer.clear()
        return chunk


class AioZipInfo(ZipInfo):
    @classmethod
    async def from_file(cls, filename, arcname=None, *, strict_timestamps=True):
        filename = AsyncPath(filename)
        st = await filename.stat()
        isdir = await filename.is_dir()
        mtime = localtime(st.st_mtime)
        date_time = mtime[0:6]
        if not strict_timestamps and date_time[0] < 1980:
            date_time = (1980, 1, 1, 0, 0, 0)
        elif not strict_timestamps and date_time[0] > 2107:
            date_time = (2107, 12, 31, 23, 59, 59)
        if arcname is None:
            arcname = str(filename.relative_to(filename.anchor))
        if isdir:
            arcname += '/'
        zinfo = cls(arcname, date_time)
        zinfo.external_attr = (st.st_mode & 0xFFFF) << 16  # Unix attributes
        if isdir:
            zinfo.file_size = 0
            zinfo.external_attr |= 0x10  # MS-DOS directory flag
        else:
            zinfo.file_size = st.st_size
        return zinfo


async def zipstream(files):
    files = [
        (f, await AioZipInfo.from_file(f, a))
        for f, a in files
    ]
    stream = Stream()
    with ZipFile(stream, mode='w') as zf:
        for f, zinfo in files:
            with zf.open(zinfo, mode='w') as fp:
                if zinfo.is_dir():
                    continue
                async for buf in read_file(AsyncPath(f)):
                    fp.write(buf)
                    yield stream.readall()
    yield stream.readall()