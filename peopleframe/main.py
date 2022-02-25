from argparse import ArgumentParser
from io import BytesIO
import logging
import os.path
from ssl import CERT_NONE, SSLContext
import sys

import osxphotos
from pyxstar.api import API
from wand.image import Image


# Turn a Pix-Star filename into a UUID
def uuid_from_name(name):
    # Normalize case
    name = name.lower()

    # Strip the extension
    name, _ = os.path.splitext(name)

    # Strip the _NNN ordinal
    name, _ = name.rsplit('_', 1)

    return name


# Export a Photos photo
def export_photo(p, mime_type):
    assert mime_type == 'image/jpeg'

    wio = BytesIO()
    with Image(filename=p.path) as img:
        img.format = 'jpeg'
        img.save(file=wio)

    return BytesIO(bytes(wio.getbuffer()))


def main():
    ap = ArgumentParser()
    ap.add_argument(
        '-a', dest='album', default='Photoframe',
        help='name of the Pix-Star album to modify')
    ap.add_argument(
        '-c', dest='count', type=int, default=10,
        help='the photo album should be populated with this number of photos')
    ap.add_argument(
        '-k', dest='validate_https', action='store_false', default=True,
        help='disable HTTPS certificate checking')
    ap.add_argument(
        '-n', dest='dry_run', action='store_true', default=False,
        help='dry-run; do not make changes to Pix-Star album')
    # TODO: Get from Keychain
    ap.add_argument('-p', dest='password', help='Pix-Star password')
    ap.add_argument(
        '-P', dest='people', action='append', default=None,
        help='include photos of the given person; can be used multiple times')
    ap.add_argument(
        '-u', dest='username', help='Pix-Star username, without @mypixstar.com')
    ap.add_argument(
        '-v', dest='verbosity', action='count', default=0,
        help='increase logging verbosity; can be used multiple times')

    args = ap.parse_args()

    logging.basicConfig(
        style='{', format='{message}', stream=sys.stderr,
        level=logging.ERROR - args.verbosity * 10)

    pdb = osxphotos.PhotosDB()
    pdb_photos = []
    for p in sorted(pdb.photos(persons=args.people), key=lambda p: p.date):
        if p.uti not in ['public.jpeg', 'public.png', 'public.heic']:
            continue

        if not p.visible:
            continue

        pdb_photos.append(p)

    pdb_photos = pdb_photos[-1 * args.count:]
    pdb_photos = {p.uuid.lower(): p for p in pdb_photos}

    ctx = None
    if not args.validate_https:
        ctx = SSLContext()
        ctx.verify_mode = CERT_NONE

    if not args.username:
        sys.stderr.write('Username: ')
        args.username = input().strip()

    if not args.password:
        sys.stderr.write('Password: ')
        args.password = input().strip()

    api = API(ssl_context=ctx)
    api.login(args.username, args.password)

    px_album = api.album(args.album)
    assert px_album

    px_photos = api.album_photos(px_album)
    px_photos = {uuid_from_name(p.name): p for p in px_photos}

    for pn in set(px_photos) - set(pdb_photos):
        logging.info(f'Deleting {pn} from Pix-Star album')

        if args.dry_run:
            continue

        api.album_photos_delete(px_album, [px_photos[pn]])

    for pn in set(pdb_photos) - set(px_photos):
        logging.info(f'Uploading {pn} to Pix-Star album')

        if args.dry_run:
            continue

        mime_type = 'image/jpeg'
        with export_photo(pdb_photos[pn], mime_type) as f:
            api.album_photo_upload(px_album, f, f'{pn}.jpg', mime_type)


if __name__ == '__main__':
    main()
