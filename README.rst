============
git-commands
============

Extends Git with custom commands.

git branch-status
    Show the status of branchs, if they are forward or ahead from master

git cleanup
    Cleanup merged branches, and old tags.

git flake8
    Check uncommited python files.

git release
    Tag and push current branch to origin and promote the release.

For each command, a complete description is available within source code.


Installation
~~~~~~~~~~~~

These commands relie on python 2.7 or python >= 3.2.
Copy each ``git-*`` scripts into /usr/local/bin/. For example::

    cp git-branch-status /usr/local/bin/git-branch-status


Regenerate manual
~~~~~~~~~~~~~~~~~

You can generate unix manual with ``help2man`` helper.

For example for the ``git-branch-status`` command::

    $ help2man git-branch-status > /usr/local/share/man/man1/git-branch-status.1
