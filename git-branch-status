#!/usr/bin/env python

"""
    git branch-status
    ~~~~~~~~~~~~~~~~~

    Expose the status of branch.

    for example, list all merged branches::

        git branch-status --behind

    mergeable branches::

        git branch-status --ahead

    duplicated branches::

        git branch-status --identical

"""

import subprocess
from collections import namedtuple
import logging
import datetime

Diff = namedtuple('Diff', 'local remote ahead behind date')

class ProcessException(Exception): pass


def execute(command, *args):
    command = ' '.join([command] + list(args))
    logging.info("execute %s", command)

    msg, err = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()
    if err:
        raise ProcessException(err)

    return msg


def branches(source, default_remote=None):
    raw = execute('git for-each-ref',
                  '--format="%(refname:short) %(upstream:short)"', source)
    for line in raw.splitlines():
        local, sep, remote = line.partition(' ')
        try:
            yield commits_diff(local, remote or default_remote)
        except:
            logging.warning('Unable to parse %s %s', local, remote)


def commits_diff(local, remote=None):
    comp = remote or "HEAD"
    ahead = execute('git rev-list {}..{} --count'.format(comp, local))
    behind = execute('git rev-list {}..{} --count'.format(local, comp))

    try:
        dt = execute('git log -1 --format=%ct', local).strip()
    except:
        dt = execute('git log -1 --format=%ct --', local).strip()
    dt = datetime.datetime.fromtimestamp(int(dt))

    return Diff(
        local, comp, int(ahead.strip()), int(behind.strip()), dt
    )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog='git branch-status',
                                     description='Display wich branches are mergeable')  # NOQA
    parser.add_argument('branch', nargs='?', help="compare this branch")
    parser.add_argument('--ahead',
                        action='store_const',
                        const=lambda x: x.ahead,
                        default=lambda x: x.ahead,
                        help="display ahead branchs",
                        dest='filter')
    parser.add_argument('--behind',
                        action='store_const',
                        const=lambda x: x.behind,
                        default=lambda x: x.ahead,
                        help="display behind branchs",
                        dest='filter')
    parser.add_argument('--identical',
                        action='store_const',
                        const=lambda x: not x.behind and not x.ahead,
                        default=lambda x: x.ahead,
                        help="display identical branchs",
                        dest='filter')
    parser.add_argument('--all',
                        action='store_const',
                        const=lambda x: x,
                        default=lambda x: x.ahead,
                        help="display all branchs",
                        dest='filter')
    parser.add_argument('--fresh',
                        action='store_true',
                        help="remote update before compare")
    parser.add_argument('--repository',
                        default='origin',
                        help="compare to this repository")
    parser.add_argument('--verbose',
                        '-v',
                        action='store_true',
                        help="verbose mode")

    args = parser.parse_args()

    level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=level, format='%(levelname)-8s: %(message)s')

    logging.info("using %s", args)

    try:
        if args.fresh:
            execute('git remote update', args.repository)

        branch, func = args.branch, args.filter
        for source in ('refs/heads', 'refs/remotes/{}'.format(args.repository)):
            stack = [diff for diff in branches(source, branch) if func(diff)]
            if not stack:
                continue

            print("branchs from {}:\n".format(source))

            for diff in sorted(stack, key=lambda x: x.date, reverse=True):
                    print("  {diff.local:45}" \
                          "  {diff.behind:>3}--{diff.ahead:<3}" \
                          "  {diff.date}".format(diff=diff))
            print("")
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logging.error(error)
