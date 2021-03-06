import mimetypes
import os

local_mime = mimetypes.MimeTypes()

if os.name == 'nt':
    local_mime.read_windows_registry()
TYPES = [
    ('audio/mp4', '.m4b'),
    ('audio/mpeg', '.mp3'),
    ('application/x-mobipocket-ebook', '.mobi'),
    ('application/epub+zip', '.epub'),
    ('application/vnd.amazon.ebook', '.azw'),
    ('application/vnd.amazon.ebook', '.azw3'),
    ('application/x-cbr', '.cbr'),
    ('application/x-cbr', '.cbz'),
    ('audio/x-ms-wma', '.wma'),
    ('application/pdf', '.pdf'),
    ('video/x-matroska', '.mkv'),
]

for typ in TYPES:
    local_mime.add_type(*typ)

guess_type = local_mime.guess_type

INLINE_TYPES = set([
    'text/plain',
    'image/apng',
    'image/avif',
    'image/gif',
    'image/jpeg',
    'image/png',
    'image/svg+xml',
    'application/pdf'
])

def inline_type(mime):
    return mime in INLINE_TYPES