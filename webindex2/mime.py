import os
import mimetypes

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
    ('pdf/pdf', '.pdf'),
]

for typ in TYPES:
    local_mime.add_type(*typ)

guess_type = local_mime.guess_type