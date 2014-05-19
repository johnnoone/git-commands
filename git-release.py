#!/usr/bin/env python

"""
    git release
    ~~~~~~~~~~~

    Release the current revision.


    # 1. check the conf
    # 2. remote update origin (optionnal)
    # 3. tag the current release
    # 4. send diff email (optionnal)
    # 5. push to origin (optionnal)


    You can setup configuration into your .git/config, like this:

    [release]
    remote-update = True # do a remote update before tagging
    send-email = True # send email
    push-release = True # push the release to origin

"""

import logging
import subprocess
import smtplib
from collections import defaultdict
from email.mime.text import MIMEText


class ProcessException(Exception):
    pass


CONF_PREFIX = 'release'
CONF_SEND_EMAIL = True
CONF_REMOTE_UPDATE = True
CONF_PUSH_RELEASE = True

CONF_MESSAGE_TEMPLATE = '''
send from: {hostname}

changelog:
{changelog}

diff:
{diff}
'''.lstrip()


def execute(command, *args):
    command = ' '.join([command] + list(args))
    logging.info("execute %s", command)
    msg, err = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).communicate()
    if err:
        raise ProcessException(err)
    return msg


class Configuration(object):
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)

    def __iter__(self):
        return iter(self.__dict__.items())

    def __str__(self):
        """docstring for __str__"""
        attrs = ['{}={!r}'.format(k, v) for k, v in self.__dict__.items()]
        return '{}({})'.format(self.__class__.__name__,
                               ', '.join(sorted(attrs)))


def raw_conf(global_conf=False):
    """fetch the configuration"""

    if global_conf:
        raw = execute('git config --get-regexp --global ^' + CONF_PREFIX)
    else:
        raw = execute('git config --get-regexp ^' + CONF_PREFIX)

    data = Configuration()

    setattr(data, 'smtp_host', 'localhost')
    setattr(data, 'smtp_port', None)
    setattr(data, 'smtp_user', None)
    setattr(data, 'smtp_password', None)
    setattr(data, 'push_release', CONF_PUSH_RELEASE)
    setattr(data, 'remote_update', CONF_REMOTE_UPDATE)
    setattr(data, 'send_email', CONF_SEND_EMAIL)

    holder = defaultdict(set)

    for line in raw.splitlines():
        k, _, v = line.partition(' ')
        k = k.partition('.')[2].replace('-', '_')
        holder[k].add(v)

    for key, value in holder.items():
        if len(value) > 1 or key == 'recipient':
            setattr(data, key, value)
        else:
            setattr(data, key, value.pop())

    return data


if __name__ == '__main__':
    import argparse
    import sys
    import re
    import socket
    import datetime
    import itertools

    class Parser(argparse.ArgumentParser):
        def error(self, message):
            sys.stderr.write('error: %s\n' % message)
            self.print_help()
            sys.exit(2)

    parser = Parser(prog='git release',
                    description='Release the current merges')
    parser.add_argument('--show-conf',
                        action='store_const',
                        const='show_conf',
                        help='show the configuration and exit',
                        dest='command')
    parser.add_argument('--show-diff',
                        action='store_const',
                        const='show_diff',
                        help='only print the diff and exit',
                        dest='command')
    parser.add_argument('--global',
                        action='store_true',
                        dest='global_conf',
                        help="use the global conf only")

    # email parts
    parser.add_argument('--sender',
                        help="sender of this message")
    parser.add_argument('--recipient',
                        nargs='*',
                        help="send mail to this recipient only")
    parser.add_argument('--add-recipient',
                        nargs='*',
                        help="add recipient to the current list")
    parser.add_argument('--send-email',
                        action='store_true',
                        default=None,
                        help="send the changelog",
                        dest='send_email')
    parser.add_argument('--no-send-email',
                        action='store_false',
                        default=None,
                        help="do not send the changelog",
                        dest='send_email')
    parser.add_argument('--remote-update',
                        action='store_true',
                        default=None,
                        help="do a remote update before releasing",
                        dest='remote_update')
    parser.add_argument('--no-remote-update',
                        action='store_false',
                        default=None,
                        help="do not perform a remote update",
                        dest='remote_update')
    parser.add_argument('--push-release',
                        action='store_true',
                        default=None,
                        help="push the release",
                        dest='push_release')
    parser.add_argument('--no-push-release',
                        action='store_false',
                        default=None,
                        help="do not push the release",
                        dest='push_release')
    parser.add_argument('--gmail',
                        action='store_true',
                        help="send with gmail",
                        dest='use_gmail')
    parser.add_argument('--gmail-password',
                        help="gmail password",
                        dest='smtp_password')

    args = parser.parse_args()
    config = raw_conf(args.global_conf)

    logging.debug('args: %s', args)

    if args.command == 'show_conf':
        for name, value in config.__dict__.items():
            print('{} {}'.format(name, value))
        parser.exit()

    # prepare configuration
    try:
        for attr in ('push_release', 'remote_update', 'send_email'):
            value = getattr(args, attr, None)
            if value is None:
                value = getattr(config, attr)
            setattr(config, attr, value)

        if config.send_email and not args.command == 'show_diff':
            config.sender = args.sender or config.sender
            config.recipient = set(args.recipient or config.recipient)

            if args.add_recipient:
                config.recipient.update(args.add_recipient)

            if args.use_gmail:
                setattr(config, 'smtp_host', 'smtp.gmail.com')
                setattr(config, 'smtp_port', 587)
                config.smtp_user = config.sender
                config.smtp_password = args.smtp_password or config.smtp_password  # NOQA

    except AttributeError as error:
        attr = re.search('''([\w\d]+)'$''', error.message).groups()[0]
        parser.error('{!r} must be supplied'.format(attr))

    logging.debug('config: %s', config)

    if config.remote_update:
        # perform a local update
        print('remote update')
        try:
            execute('git fetch origin master --tags')
        except ProcessException as error:
            print(error.message)

    # get the current tags
    current_tags = set()
    for n in execute('git log --no-walk --pretty="format:%d"').strip(' ')[1:-1].split(', '):  # NOQA
        if n.startswith('tag:'):
            current_tags.add(n[4:].strip())

    # prepare changelog and diff
    changelog = execute('git log --graph --abbrev-commit',
                        '--pretty=oneline --no-merges origin/master..')
    diff = execute('git diff origin/master.. --stat --stat-width=80')

    logging.debug('changelog: %s', changelog)
    logging.debug('diff: %s', diff)

    if args.command == 'show_diff':
        # display changelog and diff then exits
        if current_tags:
            print('tagged: {}'.format(', '.join(current_tags)))
        print('changelog:')
        print(changelog)
        print('diff:')
        print(diff)
        parser.exit()

    # defines the next tag
    branch = execute('git symbolic-ref -q --short HEAD').strip()
    tagprefix = '{}-{}'.format(branch,
                               datetime.datetime.now().strftime('%Y%m%d'))

    for i in itertools.count(start=1):
        tag = '{}{}'.format(tagprefix, i)
        if tag in current_tags:
            # already tagged, continue
            print('already tagged {}'.format(tag))
            break
        try:
            execute('git rev-parse {}'.format(tag))
            # already taken...
        except ProcessException as error:
            # free!
            execute('git tag {}'.format(tag))
            print('tagged {}'.format(tag))
            break

    if config.send_email:
        # send mail before pushing the tag
        print('send mail to {}'.format(', '.join(config.recipient)))
        msg = CONF_MESSAGE_TEMPLATE.format(
            hostname=socket.gethostname(),
            changelog=changelog,
            diff=diff)

        msg = MIMEText(msg)
        msg['Subject'] = 'Release {}'.format(tag)
        msg['From'] = config.sender
        msg['To'] = ', '.join(config.recipient)

        s = smtplib.SMTP(config.smtp_host, config.smtp_port)
        if config.smtp_user:
            s.ehlo()
            s.starttls()
            s.ehlo
            s.login(config.smtp_user, config.smtp_password)

        s.sendmail(config.sender, config.recipient, msg.as_string())
        s.quit()

    if config.push_release:
        print('push to origin')
        try:
            execute('git push origin {} --tags'.format(branch))
        except ProcessException as error:
            print(error.message)
