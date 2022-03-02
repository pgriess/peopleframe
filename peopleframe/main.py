from argparse import ArgumentParser
from collections import namedtuple
from configparser import ConfigParser
from dataclasses import dataclass
from io import BytesIO
import logging
import os.path
from ssl import CERT_NONE, SSLContext
import sys

import osxphotos
from pyxstar.api import API
from wand.image import Image


@dataclass
class Album:
    name = None
    username = None
    password = None
    count = 10
    people = []
    score = 0.5


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


# Synchronize a single album
def album_sync(album, pdb, dry_run=True, ssl_context=None):
    logging.info(f'Synchronizing album {album.name}')

    pdb_photos = []
    for p in sorted(pdb.photos(persons=album.people), key=lambda p: p.date):
        if p.uti not in ['public.jpeg', 'public.png', 'public.heic']:
            continue

        if not p.visible:
            continue

        if p.screenshot:
            continue

        if p.score.overall < album.score:
            continue

        pdb_photos.append(p)

    pdb_photos = pdb_photos[-1 * album.count:]
    pdb_photos = {p.uuid.lower(): p for p in pdb_photos}

    username = album.username
    if not username:
        sys.stderr.write(f'Username for {album.name}: ')
        username = input().strip()

    password = album.password
    if not password:
        sys.stderr.write(f'Password for {album.name}: ')
        password = input().strip()

    api = API(ssl_context=ssl_context)
    api.login(username, password)

    px_album = api.album(album.name)
    assert px_album

    px_photos = api.album_photos(px_album)
    px_photos = {uuid_from_name(p.name): p for p in px_photos}

    for pn in set(px_photos) - set(pdb_photos):
        logging.info(f'Deleting {pn} from Pix-Star album')

        if dry_run:
            continue

        api.album_photos_delete(px_album, [px_photos[pn]])

    for pn in set(pdb_photos) - set(px_photos):
        logging.info(f'Uploading {pn} to Pix-Star album')

        if dry_run:
            continue

        mime_type = 'image/jpeg'
        with export_photo(pdb_photos[pn], mime_type) as f:
            api.album_photo_upload(px_album, f, f'{pn}.jpg', mime_type)


def main():
    ap = ArgumentParser()
    ap.add_argument(
        '-f', dest='config_file',
        default=os.path.expanduser('~/.peopleframe.ini'),
        help='load values from the given config file')
    ap.add_argument(
        '-v', dest='verbosity', action='count', default=0,
        help='increase logging verbosity; can be used multiple times')

    ag = ap.add_argument_group('Pix-Star options', description='''
configure how to connect to the Pix-Star service
''')
    ag.add_argument(
        '-k', dest='validate_https', action='store_false', default=True,
        help='disable HTTPS certificate checking')
    ag.add_argument(
        '-n', dest='dry_run', action='store_true', default=False,
        help='dry-run; do not make changes to Pix-Star album')
    ag.add_argument(
        '-u', dest='username', help='Pix-Star username, without @mypixstar.com')
    ag.add_argument('-p', dest='password', help='Pix-Star password')

    ag = ap.add_argument_group('album options', description='''
configure how specific albums are synchronized; override options specified
in the configuration file
''')
    ag.add_argument(
        '-a', dest='album',
        help=('name of the album to modify; required to use other options in '
              'this group unless the config file specifies an album'))
    ag.add_argument(
        '-c', dest='count', type=int,
        help='the photo album should be populated with this number of photos')
    ag.add_argument(
        '-P', dest='people', action='append',
        help='include photos of the given person; can be used multiple times')
    ag.add_argument(
        '-s', dest='score', type=float,
        help='minimum score for photos to include; range 0 to 1.0')

    args = ap.parse_args()

    logging.basicConfig(
        style='{', format='{message}', stream=sys.stderr,
        level=logging.ERROR - args.verbosity * 10)

    ssl_ctx = None
    if not args.validate_https:
        ssl_ctx = SSLContext()
        ssl_ctx.verify_mode = CERT_NONE

    # Create the set of albums to sync
    albums = []

    # Populate initial albums from the config file (if it exists)
    if os.path.isfile(args.config_file):
        config = ConfigParser()
        config.read(args.config_file)

        for sn in config.sections():
            a = Album()
            a.name = sn
            for k, v in config[sn].items():
                if k in ['people']:
                    v = [vv.strip() for vv in v.split(',')]
                elif k in ['score']:
                    v = float(v)
                elif k in ['count']:
                    v = int(v)

                setattr(a, k.lower(), v)

            albums.append(a)

    # If the user specified an album, filter the existing set or create a new
    # one from scratch to match
    if args.album:
        if args.album not in {a.name for a in albums}:
            a = Album()
            a.name = args.album
            albums = [a]
        else:
            albums = [a for a in albums if args.name is None or a.name == args.name]

    # Apply per-album options to our set of albums to sync
    for a in albums:
        if args.count is not None:
            a.count = args.count

        if args.password is not None:
            a.password = args.password

        if args.people is not None:
            a.people = args.people

        if args.score is not None:
            a.score = args.score

    logging.info('Connecting to Photos database')
    pdb = osxphotos.PhotosDB()

    for a in albums:
        album_sync(a, pdb, dry_run=args.dry_run, ssl_context=ssl_ctx)

    logging.info('Done')


if __name__ == '__main__':
    main()
