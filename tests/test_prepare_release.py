"""Exercise release tagging against an isolated local Git remote."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / '.github/scripts/prepare-release.py'


class PrepareReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'checkout'
        subprocess.run(['git', 'init', '--bare', '-q', str(self.remote)], check=True)
        subprocess.run(['git', 'init', '-q', '-b', 'master', str(self.repo)], check=True)
        self.git('config', 'user.name', 'Release Test')
        self.git('config', 'user.email', 'release-test@example.invalid')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('commit', '-q', '--allow-empty', '-m', 'Initial fixture')
        self.git('push', '-q', 'origin', 'HEAD:master')
        self.output = self.root / 'output'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo,
                                       stderr=subprocess.PIPE, text=True).strip()

    def remote_tags(self):
        return self.git('ls-remote', '--tags', 'origin')

    def seed_tag(self, tag, annotated=False):
        if annotated:
            self.git('tag', '-a', tag, '-m', 'Fixture release')
        else:
            self.git('tag', tag)
        self.git('push', '-q', 'origin', 'refs/tags/' + tag)

    def next_commit(self):
        self.git('commit', '-q', '--allow-empty', '-m', 'Next fixture')
        self.git('push', '-q', 'origin', 'HEAD:master')

    def run_release(self, event='push', ref='refs/heads/master'):
        self.output.write_text('')
        env = dict(os.environ, GITHUB_EVENT_NAME=event, GITHUB_REF=ref,
                   GITHUB_REF_NAME=ref.split('/', 2)[2],
                   GITHUB_SHA=self.git('rev-parse', 'HEAD'), GITHUB_OUTPUT=str(self.output))
        return subprocess.run(['python3', str(SCRIPT)], cwd=self.repo, env=env,
                              capture_output=True, text=True)

    def assert_version(self, version):
        result = self.run_release()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.read_text(), f'version={version}\n')
        self.assertIn(self.git('rev-parse', 'HEAD') + '\trefs/tags/' + version,
                      self.remote_tags())

    def test_first_release(self):
        self.assert_version('v1.0')

    def test_numeric_increment_and_retry(self):
        self.seed_tag('v1.9')
        self.seed_tag('v1.28')
        self.seed_tag('unrelated')
        self.next_commit()
        self.assert_version('v1.29')
        before = self.remote_tags()
        self.assert_version('v1.29')
        self.assertEqual(before, self.remote_tags())
        self.next_commit()
        self.assert_version('v1.30')

    def test_existing_annotated_tag_is_reused(self):
        self.seed_tag('v1.29', annotated=True)
        before = self.remote_tags()
        self.assert_version('v1.29')
        self.assertEqual(before, self.remote_tags())

    def test_rejected_push_stops_publication_and_can_retry(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        result = self.run_release()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), '')
        self.assertEqual(self.remote_tags(), '')
        hook.unlink()
        self.assert_version('v1.0')

    def test_tag_and_manual_events_do_not_create_versions(self):
        for event, ref in [('push', 'refs/tags/v1.29'),
                           ('workflow_dispatch', 'refs/heads/master')]:
            with self.subTest(event=event):
                result = self.run_release(event, ref)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.output.read_text(), f'version={ref.split("/", 2)[2]}\n')
                self.assertEqual(self.remote_tags(), '')

    def test_pr_cannot_create_release(self):
        result = self.run_release('pull_request', 'refs/pull/3/merge')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), '')
        self.assertEqual(self.remote_tags(), '')


if __name__ == '__main__':
    unittest.main()
