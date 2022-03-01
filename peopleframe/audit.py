# NOTES:
#
#   - You can run `automator -i /path/to/input/file /path/to/workflow` to runs
#     an Automator workflow that requires a File input; we have a `Display
#     referenced photo` in the root of the repository
#
#   - There are several PersonInfo objects with the name '_UNKNOWN_'; each
#     represents what is considered to be an independent person. Each of these
#     has several FaceInfo objects describing their different faces.
#
#   - Unknown if it is possible to find FaceInfo objects that represent faces
#     found in multiple photos, or if they are each single-photo and are
#     aggregated at the PersonInfo layer.
#
#   - The FaceInfo object has (x, y) coordinates for the face location in the
#     image. The range is [0, 1.0]
#
#   - The FaceInfo object has a quality(?) score q=[-1.0, 1.0]. There are some
#     PersonInfo objects with FaceInfo objects that are exclusively -1. One is
#     Mia. But this FaceInfo doesn't actually show up rendered in the Photos
#     application.
#
#       - TODO: Does this FaceInfo have coordinates?
#
#   - Each photo can have multiple FaceInfo associated with it, each with a
#     different PersonInfo.
#
#   - Tagging a single FaceInfo in a PersonInfo doesn't seem to update the rest
#     of the FaceInfos. At least not immediately. Maybe this happens in the
#     background?
#
#       - TODO: Test this
#
#   TODO:
#
#       - Need a way to mark people so that they don't show up in the tool
#         anymore, e.g. someone who we don't know or care about.
#
#       - Need a way to mark photos so that they don't show up in the tool
#         anymore, e.g. a photo that has ONLY people that we don't care about.

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
        print(f'{pi.uuid}')
        for fi in pi.face_info:
            print(f'  fi={fi.uuid}; q={fi.quality}; p={fi.photo.path}, c=({fi.center_x}, {fi.center_y})')


if __name__ == '__main__':
    faces()
