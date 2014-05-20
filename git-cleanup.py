#!/usr/bin/env python

"""
    git cleanup
    ~~~~~~~~~~~

    Cleanup merged branches
"""

__all__ = ['remote']

import logging
import subprocess
import fnmatch
import re

KEEP_DEFAULTS = [
    'master',
    'prod',
    'preprod',
    'stage',
    'dev'
]


class ProcessException(Exception):
    pass


def execute(command, *args):
    command = ' '.join([command] + list(args))
    logging.debug("execute %s", command)

    msg, err = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()
    if err:
        raise ProcessException(err)

    return msg


def remote(repository, master, keep, dry_run=None):
    if not dry_run:
        logging.debug('update local references')
        execute('git fetch', repository, ' --prune --quiet')

    logging.debug('compile keep')
    patterns = set([re.compile(fnmatch.translate(k)) for k in keep])

    def keepable(ref, branch):
        for pattern in patterns:
            if pattern.match(ref):
                logging.debug('%s matched by %r', ref, pattern.pattern)
                return True
            if pattern.match(branch):
                logging.debug('%s matched by %r', branch, pattern.pattern)
                return True
        return False

    logging.debug('clear remote references from %s', repository)
    for ref in execute('git branch -r --merged', master).splitlines():
        ref = ref.strip()
        repo, branch = ref.split('/', 1)
        if repo != repository:
            logging.debug('skip %s', ref)
            continue
        elif keepable(ref, branch):
            logging.info('keep %s', ref)
            continue
        else:
            logging.warn('delete %s', ref)
            if not dry_run:
                try:
                    execute('git push', repo, '--delete --quiet', branch)
                except ProcessException as error:
                    logging.error('%s cant be deleted: %s', ref, error.args[0])

if __name__ == '__main__':
    import argparse
    import sys

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    root.addHandler(ch)

    parser = argparse.ArgumentParser(prog='git cleanup')
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='do a dry run without deleting references')

    subparsers = parser.add_subparsers(description='configure the cleaning process',  # NOQA
                                       help='kind of cleaning')

    def parse_remote(args):
        master = args.merged_into.format(**args.__dict__)
        keep = [keep.format(**args.__dict__) for keep in args.keep] + [master]
        remote(args.repository, master, keep, args.dry_run)

    parser_remote = subparsers.add_parser('remote',
                                          help='cleanup a remote repository')
    parser_remote.set_defaults(func=parse_remote)
    parser_remote.add_argument('repository',
                               nargs='?',
                               default='origin',
                               help='choose the remote repository. default to origin')  # NOQA
    parser_remote.add_argument('--merged-into', '-m',
                               default='{repository}/master',
                               help='use this branch as reference. default to master')  # NOQA
    parser_remote.add_argument('--keep', '--k', action="append",
                               default=list(KEEP_DEFAULTS),
                               help='keep these references untouched')

    args = parser.parse_args()
    args.func(args)
