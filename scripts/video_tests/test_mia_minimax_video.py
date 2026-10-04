import json
import base64
import tempfile
import sys
import io
from contextlib import redirect_stdout
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from scripts import mia_minimax_video as video


class MiniMaxVideoTests(unittest.TestCase):
    def test_prepare_defaults_use_current_full_body_reference(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['video', 'prepare']), redirect_stdout(output):
            video.main()
        body = json.loads(output.getvalue())
        url = body['content'][2]['image_url']['url']
        self.assertTrue(url.startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(url.split(',', 1)[1]),
                         (video.ROOT / 'docs/design/launch/mia-full-body-end-reference.png').read_bytes())
        self.assertIn('both boot soles', body['content'][0]['text'])

    def request(self):
        return video.build_request('Mia turns', 'https://example.com/start.png',
                                   'https://example.com/end.png', '768P', 5)

    def test_first_last_frame_contract(self):
        body = self.request()
        self.assertEqual(body['model'], 'MiniMax-H3')
        self.assertEqual(body['ratio'], 'adaptive')
        self.assertEqual(body['duration'], 5)
        self.assertEqual(body['resolution'], '768P')
        self.assertFalse(body['aigc_watermark'])
        self.assertEqual(body['content'][1], {
            'type': 'image_url', 'image_url': {'url': 'https://example.com/start.png'},
            'role': 'first_frame'})
        self.assertEqual(body['content'][2]['role'], 'last_frame')

    def test_invalid_input(self):
        for prompt, first, resolution, duration in [
            (' ', 'https://example.com/a.png', '768P', 5),
            ('x' * 7001, 'https://example.com/a.png', '768P', 5),
            ('Mia', 'http://example.com/a.png', '768P', 5),
            ('Mia', 'https://example.com/a.png', '480P', 5),
            ('Mia', 'https://example.com/a.png', '768P', 3),
        ]:
            with self.subTest(prompt=prompt[:10], resolution=resolution, duration=duration):
                with self.assertRaises(video.VideoError):
                    video.build_request(prompt, first, 'https://example.com/b.png',
                                        resolution, duration)

    def test_local_png_encoded_inline_without_remote_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'frame.png'
            image.write_bytes(b'\x89PNG\r\n\x1a\nTEST_ONLY')
            body = video.build_request('Mia', str(image), str(image), '768P', 5)
            url = body['content'][1]['image_url']['url']
            self.assertTrue(url.startswith('data:image/png;base64,'))
            self.assertEqual(base64.b64decode(url.split(',', 1)[1]), image.read_bytes())
            image.write_bytes(b'not an image')
            with self.assertRaises(video.VideoError):
                video.build_request('Mia', str(image), str(image), '768P', 5)

    def test_create_and_query_auth_contract(self):
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.headers['Authorization'], 'Bearer TEST_ONLY')
            if request.method == 'POST':
                self.assertEqual(str(request.url), video.API + '/video_generation')
                self.assertEqual(json.loads(request.content), self.request())
                return httpx.Response(200, json={'task_id': '123'})
            self.assertEqual(str(request.url), video.API + '/query/video_generation/123')
            return httpx.Response(200, json={'task': {'id': '123', 'status': 'running'}})
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            self.assertEqual(video.create(client, 'TEST_ONLY', self.request()), '123')
            self.assertEqual(video.query(client, 'TEST_ONLY', '123')['status'], 'running')
        self.assertEqual(len(calls), 2)

    def test_http_error_does_not_echo_upstream_secret_or_message(self):
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
                401, json={'error': {'message': 'DO_NOT_ECHO_TEST_VALUE'}}))) as client:
            with self.assertRaises(video.VideoError) as caught:
                video.create(client, 'TEST_ONLY', self.request())
        self.assertIn('401', str(caught.exception))
        self.assertNotIn('DO_NOT_ECHO', str(caught.exception))

    def test_creation_timeout_is_not_retried(self):
        calls = []
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout('DO_NOT_ECHO_TEST_VALUE')
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(video.VideoError):
                video.create(client, 'TEST_ONLY', self.request())
        self.assertEqual(len(calls), 1)

    def test_bad_response_and_task_id(self):
        with httpx.Client(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={}))) as client:
            with self.assertRaises(video.VideoError):
                video.create(client, 'TEST_ONLY', self.request())
            with self.assertRaises(video.VideoError):
                video.query(client, 'TEST_ONLY', '../other')

    def test_wait_queued_running_success(self):
        results = [{'status': x} for x in ['queued', 'running', 'succeeded']]
        with patch.object(video, 'query', side_effect=results), patch.object(video.time, 'sleep'):
            self.assertEqual(video.wait(None, 'TEST_ONLY', '123', 10, 1)['status'], 'succeeded')

    def test_wait_failure_cancel_and_timeout(self):
        for status in ['failed', 'cancelled']:
            with patch.object(video, 'query', return_value={'status': status}):
                with self.assertRaises(video.VideoError):
                    video.wait(None, 'TEST_ONLY', '123', 10, 1)
        with patch.object(video, 'query', return_value={'status': 'running'}), \
                patch.object(video.time, 'sleep'), \
                patch.object(video.time, 'monotonic', side_effect=[0, 0, 1, 11]):
            with self.assertRaises(video.VideoError):
                video.wait(None, 'TEST_ONLY', '123', 10, 1)

    def test_download_has_no_auth_and_preserves_existing_file(self):
        def handler(request):
            self.assertNotIn('authorization', request.headers)
            return httpx.Response(200, content=b'test-video')
        with tempfile.TemporaryDirectory() as directory, httpx.Client(
                transport=httpx.MockTransport(handler)) as client:
            output = Path(directory) / 'result.mp4'
            video.download(client, 'https://cdn.example.com/video.mp4', output)
            self.assertEqual(output.read_bytes(), b'test-video')
            with self.assertRaises(video.VideoError):
                video.download(client, 'https://cdn.example.com/video.mp4', output)

    def test_download_failure_removes_partial(self):
        with tempfile.TemporaryDirectory() as directory, httpx.Client(
                transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
            output = Path(directory) / 'result.mp4'
            with self.assertRaises(video.VideoError):
                video.download(client, 'https://cdn.example.com/video.mp4', output)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_key_saved_privately_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                video.getpass, 'getpass', return_value='TEST_ONLY'), \
                patch.object(sys.stdin, 'isatty', return_value=True):
            target = Path(directory) / 'minimax.key'
            video.configure(target)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(video.load_key(target), 'TEST_ONLY')
        with self.assertRaises(video.VideoError):
            video.configure(Path(__file__).resolve().parents[2] / 'test.key')

    def test_configure_refuses_noninteractive_input(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                sys.stdin, 'isatty', return_value=False), patch.object(video.getpass, 'getpass') as read:
            with self.assertRaises(video.VideoError):
                video.configure(Path(directory) / 'minimax.key')
            read.assert_not_called()

    def test_cli_paid_gate_and_existing_state_prevent_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / 'task.json'
            argv = ['video', 'create', '--state', str(state)]
            with patch.object(sys, 'argv', argv), patch.object(video, 'create') as create:
                with self.assertRaises(SystemExit):
                    video.main()
                create.assert_not_called()
            state.write_text('{"task_id":"previous"}')
            with patch.object(sys, 'argv', argv + ['--confirm-charge']), \
                    patch.object(video, 'load_key', return_value='TEST_ONLY'), \
                    patch.object(video, 'create') as create:
                with self.assertRaises(SystemExit):
                    video.main()
                create.assert_not_called()
            self.assertEqual(json.loads(state.read_text()), {'task_id': 'previous'})

    def test_cli_records_task_without_key_and_preserves_uncertain_submission(self):
        for success in [True, False]:
            with self.subTest(success=success), tempfile.TemporaryDirectory() as directory:
                state = Path(directory) / 'task.json'
                with patch.object(sys, 'argv', ['video', 'create', '--confirm-charge', '--state', str(state)]), \
                        patch.object(video, 'load_key', return_value='TEST_ONLY'), \
                        patch.object(video, 'create', return_value='123',
                                     side_effect=None if success else video.VideoError('network failed')):
                    if success:
                        video.main()
                    else:
                        with self.assertRaises(SystemExit):
                            video.main()
                self.assertEqual(json.loads(state.read_text()),
                                 {'task_id': '123'} if success else {'status': 'submission_pending'})
                self.assertEqual(state.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
