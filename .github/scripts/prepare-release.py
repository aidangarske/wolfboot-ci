#!/usr/bin/env python3
"""Create the next vMAJOR.MINOR tag for a master push, or reuse its tag."""

import os
from pathlib import Path
import re
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def prepare_release():
    event = os.environ['GITHUB_EVENT_NAME']
    if event not in ('push', 'workflow_dispatch'):
        raise ValueError('Only push and workflow_dispatch events can publish images')
    version = os.environ['GITHUB_REF_NAME']
    if event == 'push' and os.environ['GITHUB_REF'] == 'refs/heads/master':
        sha = os.environ['GITHUB_SHA']
        if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
            raise ValueError('GITHUB_SHA must identify the commit being released')
        commit = git('rev-parse', '--verify', sha + '^{commit}')
        git('fetch', '--tags', 'origin')
        versions = {}
        for tag in git('tag', '--list').splitlines():
            match = re.fullmatch(r'v(\d+)\.(\d+)', tag)
            if match:
                versions[tag] = tuple(map(int, match.groups()))
        existing = set(git('tag', '--points-at', commit).splitlines()) & versions.keys()
        if existing:
            version = max(existing, key=versions.get)
        else:
            major, minor = max(versions.values(), default=(1, -1))
            version = f'v{major}.{minor + 1}'
            git('tag', version, commit)
        # No force: an existing tag for a different commit must never be moved.
        git('push', 'origin', 'refs/tags/' + version)
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', version):
        raise ValueError('The selected ref cannot be used as an image tag')
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write(f'version={version}\n')
    print(f'Publishing image version: {version}')


if __name__ == '__main__':
    prepare_release()
