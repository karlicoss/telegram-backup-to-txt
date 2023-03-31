#!/usr/bin/env python3
"""
Script to convert HTML output from [[https://github.com/fabianonline/telegram_backup][telegram_backup]] tool to plaintext with proper filenames.

I'm using it for quick search (e.g. =grep=) in messages without having to go to web interface/mobile app. You can read more about it [[https://beepb00p.xyz/pkm-search.html#other][here]].

* Usage

1. Read [[https://github.com/fabianonline/telegram_backup#usage][usage for telegram_backup]] to backup your account. Don't forget to run =--export html=!
2. Run this script with the same =--target= and =--account= arguments as for backup script, and pass =--output= directory.

Personally I've got all this set up as a daily Cron job.

** Dependencies

~apt install sqlite3 html2text~

"""

from pathlib import Path
from subprocess import check_call, check_output
from fnmatch import fnmatch
from typing import Optional

import re
import string
import sys


USER_RE = re.compile(r'user_(?P<id>\d+)(?P<page>_p\d+)?')
CHAT_RE = re.compile(r'chat_(?P<id>\d+)(?P<page>_p\d+)?')


def query(db: Path, what: str, from_: str, where: str):
    res = check_output([
        'sqlite3',
        str(db),
        f'SELECT {what} FROM {from_} WHERE id={where};',
    ]).decode('utf8').strip()

    # TODO maybe strip off emoji too just in case...
    table = str.maketrans({key: None for key in string.punctuation})
    res = res.translate(table)

    if len(res) == 0:
        res = where # TODO ugh
    return res


def get_output_name(*, db: Path, path: Path) -> str:
    print(f'processing: {path}', file=sys.stderr)
    um = USER_RE.match(path.name)
    cm = CHAT_RE.match(path.name)
    name: str
    if um is not None:
        id_ = um.group('id')
        page = um.group('page')
        if page is None:
            page = ""
        name = query(db, 'username', 'users', id_) + page
    elif cm is not None:
        id_ = cm.group('id')
        page = cm.group('page')
        if page is None:
            page = ""
        name = query(db, 'name', 'chats', id_) + page
    else:
        raise RuntimeError(f'Unexpected file name: {path}')
    return name


def run(*, export_dir: Path, output: Path, ignore: Optional[str]=None) -> None:
    output.mkdir(parents=True, exist_ok=True)

    htmls  = export_dir / 'files' / 'dialogs'
    db     = export_dir / 'database.sqlite'
    html_files = sorted(htmls.glob('*.html'))
    assert len(html_files) > 0, htmls
    for path in html_files:
        name = get_output_name(db=db, path=path)
        if ignore is not None and fnmatch(name, ignore):
            print(f'Ignoring {path} due to name: {name}', file=sys.stderr)
            continue

        out = output / (name + ".txt")
        check_call([
            'html2text',
            '-utf8',
            '-width', '500', # hopefully, enough..
            '-o', str(out),
            str(path),
        ])


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--target' , type=Path, help='same option as for telegram_backup tool', required=True)
    p.add_argument('--account', type=str , help='same option as for telegram_backup tool', required=True)
    p.add_argument('--output' , type=Path, help='path for txt outputs'                   , required=True)
    p.add_argument('--ignore' , type=str , help='glob for ignoring certain names'        , required=False)
    # TODO FIXME ignore targets?
    args = p.parse_args()

    export_dir = args.target / args.account
    run(export_dir=export_dir, output=args.output, ignore=args.ignore)


if __name__ == '__main__':
    main()
