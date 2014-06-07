#!/usr/bin/env python

"""
    git flake8
    ~~~~~~~~~~

    Check your python files before commiting with flake8.

    Before installing, be sure that flake8 is installed.
    for example:

        $ pip install flake8
"""

__all__ = ['flake8']

import fnmatch
import logging
import subprocess
import re


def stringify(text):
    if sys.version_info >= (3,) and isinstance(text, bytes):
        return text.decode('utf-8')


class ProcessException(Exception):
    pass


def execute(command, *args):
    command = ' '.join([command] + list(args))
    logging.debug("execute %s", command)

    msg, err = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()
    if err:
        raise ProcessException(stringify(err))

    return stringify(msg)


def flake8(only=None):
    patterns = set([re.compile(fnmatch.translate(k)) for k in only or []])
    def allowed(filename):
        if not filename.endswith('.py'):
            return False
        elif not only:
            return True
        elif any(pattern.match(filename) for pattern in patterns):  # noqa
            return True
        return False

    buffer = execute('git status -s')
    for line in buffer.splitlines():
        status, filename = line.split(None, 1)
        if status in ('D',):
            continue
        if allowed(filename):
            print('\033[92m{}\033[0m'.format(filename))
            print(execute('flake8', filename))

if __name__ == '__main__':
    import argparse
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    root.addHandler(ch)

    parser = argparse.ArgumentParser(prog='git flake8')
    parser.add_argument('patterns', metavar='PATTERN', nargs='*',
                        help='check only theses patterns')
    args = parser.parse_args()
    flake8(only=args.patterns)
