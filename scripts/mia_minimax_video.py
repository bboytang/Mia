"""Offline Mia animation authoring via the documented MiniMax H3 V2 API."""

import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import urlsplit

import httpx


API = 'https://api.minimax.cn/v2'
ROOT = Path(__file__).resolve().parents[1]
KEY_FILE = Path.home() / '.config/mia/minimax.key'


class VideoError(Exception):
    pass


def https_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise VideoError('媒体地址必须为不含账号密码的 HTTPS URL。')
    return value


def image_url(value):
    if urlsplit(value).scheme:
        return https_url(value)
    path = Path(value)
    if not path.is_file() or path.stat().st_size > 30 * 1024 * 1024:
        raise VideoError('本地参考图必须存在且不超过 30 MB。')
    data = path.read_bytes()
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        kind = 'png'
    elif data.startswith(b'\xff\xd8\xff'):
        kind = 'jpeg'
    else:
        raise VideoError('本地参考图仅支持 PNG/JPEG。')
    return 'data:image/' + kind + ';base64,' + base64.b64encode(data).decode('ascii')


def build_request(prompt, first, last, resolution, duration):
    if not prompt.strip() or len(prompt) > 7000:
        raise VideoError('提示词必须非空且不超过 7000 字符。')
    if resolution not in ('768P', '2K') or not 4 <= duration <= 15:
        raise VideoError('H3 要求 768P/2K 和 4–15 秒整数时长。')
    body = {
        'model': 'MiniMax-H3',
        'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': image_url(first)}, 'role': 'first_frame'},
            {'type': 'image_url', 'image_url': {'url': image_url(last)}, 'role': 'last_frame'},
        ],
        'resolution': resolution, 'duration': duration, 'ratio': 'adaptive',
        'aigc_watermark': False,
    }
    if len(json.dumps(body).encode()) > 64 * 1024 * 1024:
        raise VideoError('内嵌参考图导致请求超过 64 MB；请缩小素材。')
    return body


def api_json(client, key, method, path, body=None):
    try:
        response = client.request(method, API + path, json=body,
                                  headers={'Authorization': 'Bearer ' + key}, timeout=60)
    except httpx.HTTPError:
        raise VideoError('API 网络失败；创建任务可能已被受理，请核对控制台，勿直接重提。') from None
    if response.status_code != 200:
        # Upstream messages and request URLs can contain submitted material or secrets.
        raise VideoError(f'MiniMax HTTP {response.status_code}；未输出上游正文。')
    try:
        return response.json()
    except ValueError:
        raise VideoError('MiniMax 返回非 JSON 响应。') from None


def create(client, key, body):
    result = api_json(client, key, 'POST', '/video_generation', body)
    task_id = result.get('task_id') if isinstance(result, dict) else None
    if not isinstance(task_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
        raise VideoError('创建响应缺少有效任务 ID；请核对控制台，勿直接重提。')
    return task_id


def query(client, key, task_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', task_id):
        raise VideoError('任务 ID 格式无效。')
    result = api_json(client, key, 'GET', '/query/video_generation/' + task_id)
    task = result.get('task') if isinstance(result, dict) else None
    if not isinstance(task, dict) or task.get('status') not in (
            'queued', 'running', 'succeeded', 'failed', 'cancelled'):
        raise VideoError('查询响应缺少有效任务状态。')
    return task


def wait(client, key, task_id, timeout, interval):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = query(client, key, task_id)
        status = task['status']
        print('任务状态=' + status, flush=True)
        if status == 'succeeded':
            return task
        if status in ('failed', 'cancelled'):
            raise VideoError('生成任务终止：' + status + '；未自动重新生成。')
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise VideoError('等待超时；可用同一任务 ID 继续查询，不会重复扣费。')


def download(client, url, output):
    https_url(url)
    if output.exists():
        raise VideoError('输出文件已存在；请选择新路径。')
    partial = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
            partial = Path(stream.name)
            # A separate client without API auth is used by the CLI. Redirects are
            # disabled: inspect a changed CDN address rather than leaking credentials.
            with client.stream('GET', url, timeout=120, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise VideoError(f'视频下载 HTTP {response.status_code}。')
                for chunk in response.iter_bytes():
                    stream.write(chunk)
        if partial.stat().st_size == 0:
            raise VideoError('视频文件为空。')
        # Atomic publication without overwriting an existing user file.
        os.link(partial, output)
    except httpx.HTTPError:
        raise VideoError('视频下载网络失败；可重试下载同一任务。') from None
    finally:
        if partial is not None:
            partial.unlink(missing_ok=True)


def configure(path):
    if path.resolve().is_relative_to(ROOT):
        raise VideoError('密钥文件必须位于仓库外。')
    if not sys.stdin.isatty():
        raise VideoError('请在交互终端运行 configure；不接受可能回显的管道输入。')
    key = getpass.getpass('输入 MiniMax 中国平台 API Key（不回显）：')
    if not key or any(c.isspace() for c in key) or not key.isascii():
        raise VideoError('Key 必须非空，不能包含空白或非 ASCII 字符。')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Replace atomically, including a pre-existing file with unsafe permissions.
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(key)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    print('Key 已保存到仓库外的 0600 文件；未提交生成任务。')


def load_key(path):
    key = os.environ.get('MINIMAX_API_KEY')
    if key:
        return key
    if not path.exists() or path.stat().st_mode & 0o077:
        raise VideoError('未配置 Key 或文件权限不安全；先运行 configure。')
    return path.read_text().strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key-file', type=Path, default=KEY_FILE)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('configure')
    for name in ('prepare', 'create'):
        command = commands.add_parser(name)
        command.add_argument('--prompt', type=Path, default=ROOT / 'docs/design/launch/mia-minimax-prompt.txt')
        command.add_argument('--first', default=str(ROOT / 'docs/design/launch/mia-particle-start.png'))
        command.add_argument('--last', default=str(ROOT / 'docs/design/launch/mia-full-body-end-reference.png'))
        command.add_argument('--resolution', choices=['768P', '2K'], default='768P')
        command.add_argument('--duration', type=int, default=5)
        if name == 'create':
            command.add_argument('--confirm-charge', action='store_true')
            command.add_argument('--state', type=Path, required=True)
    for name in ('status', 'wait', 'download'):
        command = commands.add_parser(name)
        command.add_argument('task_id')
        if name == 'wait':
            command.add_argument('--timeout', type=int, default=900)
        if name == 'download':
            command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'configure':
            configure(args.key_file)
            return
        if args.command in ('prepare', 'create'):
            body = build_request(args.prompt.read_text(), args.first, args.last,
                                 args.resolution, args.duration)
            if args.command == 'prepare':
                print(json.dumps(body, ensure_ascii=False, indent=2))
                return
            if not args.confirm_charge:
                raise VideoError('create 会收费；审核请求和费用后才可传 --confirm-charge。')
        if args.command == 'wait' and args.timeout <= 0:
            raise VideoError('等待时限必须为正数。')
        key = load_key(args.key_file)
        with httpx.Client(follow_redirects=False) as client:
            if args.command == 'create':
                # Reserve the state file before a paid request; any uncertain outcome
                # leaves this marker to prevent a blind repeat with the same path.
                with args.state.open('x') as state:
                    os.chmod(args.state, 0o600)
                    json.dump({'status': 'submission_pending'}, state)
                    state.flush()
                    task_id = create(client, key, body)
                    print('任务 ID=' + task_id, flush=True)
                    state.seek(0)
                    json.dump({'task_id': task_id}, state)
                    state.truncate()
                return
            task = (wait(client, key, args.task_id, args.timeout, 10)
                    if args.command == 'wait' else query(client, key, args.task_id))
        if args.command == 'download':
            if task['status'] != 'succeeded':
                raise VideoError('任务尚未成功；没有下载。')
            url = task.get('content', {}).get('url')
            if not isinstance(url, str):
                raise VideoError('成功响应缺少视频 URL。')
            with httpx.Client() as media:
                download(media, url, args.output)
            print('视频已下载；角色、动作、音轨与首页衔接待验收。')
        else:
            print(json.dumps({k: task[k] for k in ('id', 'status', 'model', 'resolution',
                                                 'duration', 'ratio', 'usage') if k in task}))
    except (VideoError, OSError, ValueError):
        # Never render raw HTTP/JSON/filesystem exception content.
        error = sys.exc_info()[1]
        print(str(error) if isinstance(error, VideoError) else '本地文件或参数操作失败。', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
