from argparse import ArgumentParser
import logging
import os.path
from ssl import CERT_NONE, SSLContext
import sys
from tempfile import TemporaryDirectory

import osxphotos
from pyxstar.api import API


def get_album(api, name):
    for a in api.albums():
        if a.name == name:
            return a

    return None


# Turn a Pix-Star filename into a UUID
def uuid_from_name(name):
    # Normalize case
    name = name.lower()

    # Strip the extension
    name, _ = os.path.splitext(name)

    # Strip the _NNN ordinal
    name, _ = name.rsplit('_', 1)

    return name


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
        # TODO: Convert other formats, e.g. public.heic
        if p.uti not in ['public.jpeg', 'public.png']:
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

    # TODO: Need API.album() method to get a specific album
    px_album = get_album(api, args.album)
    assert px_album

    px_photos = api.album_photos(px_album)
    px_photos = {uuid_from_name(p.name): p for p in px_photos}

    # TODO: Paging rather than deleting one-by-one 
    for pn in set(px_photos) - set(pdb_photos):
        logging.info(f'Deleting {pn} from Pix-Star album')

        if args.dry_run:
            continue

        api.album_photos_delete(px_album, [px_photos[pn]])

    with TemporaryDirectory() as dp:
        for pn in set(pdb_photos) - set(px_photos):
            p = pdb_photos[pn]
            ext = None
            mime_type = None
            if p.uti == 'public.jpeg':
                ext = 'jpg'
                mime_type = 'image/jpeg'
            elif p.uti == 'public.png':
                ext = 'png'
                mime_type = 'image/png'
            else:
                raise Exception(f'Unexpected URI {p.uti}')

            p.export(dp, f'{pn}.{ext}')
            assert os.path.isfile(os.path.join(dp, f'{pn}.{ext}'))

            logging.info(f'Uploading {pn} to Pix-Star album')

            if args.dry_run:
                continue

            with open(os.path.join(dp, f'{pn}.{ext}'), 'rb') as f:
                api.album_photo_upload(px_album, f, f'{pn}.{ext}', mime_type)


if __name__ == '__main__':
    main()
