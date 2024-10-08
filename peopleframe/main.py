from argparse import ArgumentParser
from configparser import ConfigParser
import dataclasses
import enum
import functools
import hashlib
import io
import logging
import os
import os.path
from pathlib import Path
from random import sample
from ssl import CERT_NONE, SSLContext
import subprocess
import sys
import tempfile
from typing import IO, List, Mapping, Optional

import certifi
from mixpanel import Mixpanel
import osxphotos
from pyxstar.api import API
import sentry_sdk

log = logging.getLogger("peopleframe")


class SelectionCriteria(enum.Enum):
    RANDOM = enum.auto()
    RECENT = enum.auto()


@dataclasses.dataclass
class Album:
    """An album to synchronize."""

    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    count: int = 10
    people: List[str] = dataclasses.field(default_factory=list)
    score: float = 0.5
    favorite: Optional[bool] = None
    selection_criteria = SelectionCriteria.RECENT

    def __str__(self) -> str:
        return (
            f'Album(name={self.name}, username="{self.username}", '
            f'count={self.count}, people={", ".join(self.people)}, '
            f"score={self.score}, "
            f"favorite={self.favorite}, "
            f"selection_criteria={self.selection_criteria})"
        )

@functools.cache
def agent_id() -> str:
    """
    Get a unique, stable, opaque identifier for this instance of the PeopleFrame
    agent process.
    """

    h = hashlib.sha256(b"peopleframe")
    # See https://apple.stackexchange.com/a/342043
    h.update(subprocess.check_output(r"ioreg -d2 -c IOPlatformExpertDevice | awk -F\" '/IOPlatformUUID/{print $(NF-1)}'", shell=True))
    return h.hexdigest()

def album_id(album_name: str) -> str:
    """
    Get a stable, opaque identifier for an album name.
    """

    h = hashlib.sha256(b"peopleframe")
    h.update(album_name.encode("utf-8"))
    return h.hexdigest()


def uuid_from_name(name: str) -> str:
    """Convert a Pix-Star filename into a UUID."""

    # Normalize case
    name = name.lower()

    # Strip the extension
    name, _ = os.path.splitext(name)

    # Strip the _NNN ordinal
    name, _ = name.rsplit("_", 1)

    return name


def export_photo(p: osxphotos.PhotoInfo, mime_type: str) -> IO:
    """Export a Photos photo as a file-like object."""

    assert mime_type == "image/jpeg"

    # We use a TemporaryDirectory here rather than a NamedTemporaryFile because
    # the latter does not expect you to write around it (e.g. by shelling out to
    # sips). It thinks you will write through it and no data has made it into
    # the file otherwise, attempting to read through the file after writing to
    # it out-of-band results in perceiving an "empty" file.
    with tempfile.TemporaryDirectory() as td:
        dir_path = Path(td)
        file_path = dir_path / "file.jpeg"

        # Convert with sips(1) because it ships with macOS
        subprocess.check_call(
            ["sips", "-s", "format", "jpeg", p.path, "--out", os.fspath(file_path)],
            stdout=subprocess.DEVNULL,
        )
        with open(file_path, mode="rb") as tf:
            body = tf.read()
        return io.BytesIO(body)


def album_pdb_photos(
    album: Album, pdb: osxphotos.PhotosDB
) -> Mapping[str, osxphotos.PhotoInfo]:
    """
    Select Photos photos for synchronization with the given album.
    """

    qo = osxphotos.QueryOptions()
    if album.people:
        qo.person = album.people
    if album.favorite is not None:
        qo.favorite = album.favorite

    # Grab all photos that match filter criteria
    pdb_photos = []
    for p in pdb.query(qo):
        if p.uti not in ["public.jpeg", "public.png", "public.heic"]:
            continue

        if not p.visible:
            continue

        if p.screenshot:
            continue

        # Allow explicit indication as a favorite to override
        # the score threshold
        if p.score.overall < album.score and not p.favorite:
            continue

        pdb_photos.append(p)

    # Apply selection criteria
    if album.selection_criteria is SelectionCriteria.RECENT:
        pdb_photos = sorted(pdb_photos, key=lambda p: p.date, reverse=True)
    elif album.selection_criteria is SelectionCriteria.RANDOM:
        pdb_photos = sample(pdb_photos, len(pdb_photos))
    else:
        raise Exception(f"unexpected selection criteria {album.selection_criteria}")

    # Take only the number of photos requested
    pdb_photos = pdb_photos[: album.count]

    # Return a map of UUIDs to photos
    return {p.uuid.lower(): p for p in pdb_photos}


def album_sync(
    album: Album,
    pdb_photos: Mapping[str, osxphotos.PhotoInfo],
    px: API,
    dry_run: bool,
    mp: Mixpanel,
) -> None:
    """
    Synchronize an Album with the Pix-Star service.
    """

    log.info(f"Synchronizing {album}")

    try:
        px_album = px.album(album.name)
    except KeyError:
        log.warning(f"Creating missing album {album.name}")
        px_album = px.album_create(album.name)

    px_photos = px.album_photos(px_album)
    px_photos = {uuid_from_name(p.name): p for p in px_photos}

    for pn in set(px_photos) - set(pdb_photos):
        log.info(f"Deleting {pn} from Pix-Star album")

    if not dry_run:
        px.album_photos_delete(
            px_album,
            [px_photos[pn] for pn in set(px_photos) - set(pdb_photos)],
        )
        mp.track(agent_id(), "photo_delete", {"album_id": album_id(album.name)})

    for pn in set(pdb_photos) - set(px_photos):
        log.info(f"Uploading {pn} to Pix-Star album")

        if dry_run:
            continue

        mime_type = "image/jpeg"
        with export_photo(pdb_photos[pn], mime_type) as f:
            px.album_photo_upload(px_album, f, f"{pn}.jpg", mime_type)
            mp.track(agent_id(), "photo_upload", {"album_id": album_id(album.name)})

def main():
    ap = ArgumentParser()
    ap.add_argument(
        "-f",
        dest="config_file",
        default=os.path.expanduser("~/.peopleframe.ini"),
        help="load values from the given config file",
    )
    ap.add_argument(
        "-v",
        dest="verbosity",
        action="count",
        default=0,
        help="increase logging verbosity; can be used multiple times",
    )

    ag = ap.add_argument_group(
        "Pix-Star options",
        description="""
Configure how to connect to the Pix-Star service
""",
    )
    ag.add_argument(
        "-k",
        dest="validate_https",
        action="store_false",
        default=True,
        help="disable HTTPS certificate checking",
    )
    ag.add_argument(
        "-n",
        dest="dry_run",
        action="store_true",
        default=False,
        help="dry-run; do not make changes to Pix-Star album",
    )
    ag.add_argument(
        "-u", dest="username", help="Pix-Star username, without @mypixstar.com"
    )
    ag.add_argument("-p", dest="password", help="Pix-Star password")

    ag = ap.add_argument_group(
        "Album options",
        description="""
Configure how specific albums are synchronized; override options specified
in the configuration file
""",
    )
    ag.add_argument(
        "-a",
        dest="album",
        help=(
            "name of the album to modify; required to use other options in "
            "this group unless the config file specifies an album"
        ),
    )
    ag.add_argument(
        "-c",
        dest="count",
        type=int,
        help="the photo album should be populated with this number of photos",
    )
    ag.add_argument(
        "-P",
        dest="people",
        action="append",
        help="include photos of the given person; can be used multiple times",
    )
    ag.add_argument(
        "-s",
        dest="score",
        type=float,
        help="minimum score for photos to include; range 0 to 1.0",
    )
    ag.add_argument(
        "-S",
        dest="selection_criteria",
        choices=[sc.name for sc in list(SelectionCriteria)],
        help="how to select images from the Photos library",
    )

    args = ap.parse_args()

    # Make sure logging is reset to its out-of-the-box state before we go about
    # configuring things. This can happen in module-level initialization code
    # either explicitly (by calling setup APIs) or implicitly (by triggering
    # logging which then does its own implicit init).
    if logging.getLogger().hasHandlers():
        root_logger = logging.getLogger()
        for h in root_logger.handlers:
            root_logger.removeHandler(h)

    logging.disable(logging.NOTSET)

    # Now apply the actual logging configuration that we want
    logging.basicConfig(
        style="{",
        stream=sys.stderr,
        format="{asctime} {levelname} {filename}:{lineno} - {message}",
        level=logging.ERROR - args.verbosity * 10,
    )

    # Set up SSL
    ssl_ctx = SSLContext()
    if not args.validate_https:
        ssl_ctx.verify_mode = CERT_NONE
    else:
        ssl_ctx.load_verify_locations(cafile=certifi.where())

    # Set up analytics
    mp = Mixpanel("7397236382725ae239671f29b8072054")

    # Set up Sentry monitoring
    sentry_sdk.init(
        dsn="https://628b59c6e71bb81715a4fe9ee1646f94@o4507999808323584.ingest.us.sentry.io/4507999818678272",
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

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
                if k in ["people"]:
                    v = [vv.strip() for vv in v.split(",")]
                elif k in ["score"]:
                    v = float(v)
                elif k in ["count"]:
                    v = int(v)
                elif k in ["selection_criteria"]:
                    v = SelectionCriteria.__members__[v]
                elif k in ["favorite"]:
                    v = bool(v)

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
            albums = [a for a in albums if a.name == args.album]

    # Apply per-album options to our set of albums to sync
    for a in albums:
        if args.count is not None:
            a.count = args.count

        if args.username is not None:
            a.username = args.username

        if args.password is not None:
            a.password = args.password

        if args.people is not None:
            a.people = args.people

        if args.score is not None:
            a.score = args.score

        if args.selection_criteria is not None:
            a.selection_criteria = SelectionCriteria.__members__[
                args.selection_criteria
            ]

    log.info("Connecting to Photos database")

    pdb = osxphotos.PhotosDB()

    # Pre-authenticated API objects so that we don't prompt users multiple times
    # for the same set of credentials
    px_apis = {}

    for a in albums:
        # Get the Pix-Star API object to use, creating one if necessary
        px = px_apis.get(a.username)
        if not px:
            username = a.username
            if not username:
                sys.stderr.write(f"Username for {a.name}: ")
                username = input().strip()

            password = a.password
            if not password:
                sys.stderr.write(f"Password for {a.name}: ")
                password = input().strip()

            px = API(ssl_context=ssl_ctx)
            px.login(username, password)
            px_apis[a.username] = px

        # Select which photos should be in the album
        pdb_photos = album_pdb_photos(a, pdb)

        album_sync(a, pdb_photos, px, args.dry_run, mp)

    log.info("Done")


if __name__ == "__main__":
    main()
