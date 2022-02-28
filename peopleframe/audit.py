from argparse import ArgumentParser
import logging
import subprocess
import sys

import osxphotos

def faces():
    ap = ArgumentParser()
    ap.add_argument(
        '-v', dest='verbosity', action='count', default=0,
        help='increase logging verbosity; can be used multiple times')

    args = ap.parse_args()

    logging.basicConfig(
        style='{', format='{message}', stream=sys.stderr,
        level=logging.ERROR - args.verbosity * 10)

    pdb = osxphotos.PhotosDB()
    person_infos = sorted(
        [pi for pi in pdb.person_info if pi.name =='_UNKNOWN_' and pi.facecount > 0],
        key=lambda pi: pi.facecount,
        reverse=True)
    for pi in person_infos:
        subprocess.check_call(args=['/Users/pg/src/pgriess-peopleframe/finder_reveal.osa', pi.keyphoto.path])
        input('asdfsadf')


if __name__ == '__main__':
    faces()
