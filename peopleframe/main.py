from argparse import ArgumentParser
import logging
from ssl import CERT_NONE, SSLContext
import sys

import osxphotos
from pyxstar.api import API

def main():
    ap = ArgumentParser()
    ap.add_argument(
        '-k', dest='validate_https', action='store_false', default=True,
        help='disable HTTPS certificate checking')
    # TODO: Get from Keychain
    ap.add_argument('-p', dest='password', help='Pix-Star password')
    ap.add_argument(
        '-u', dest='username', help='Pix-Star username, without @mypixstar.com')
    ap.add_argument(
        '-v', dest='verbosity', action='count', default=0,
        help='increase logging verbosity; can be used multiple times')

    args = ap.parse_args()

    logging.basicConfig(
        style='{', format='{message}', stream=sys.stderr,
        level=logging.ERROR - args.verbosity * 10)

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

    pdb = osxphotos.PhotosDB()
    for p in pdb.photos(persons=["Ryder Griess"]):
        print(p.path)
