"""One real compatibility probe for Mia's configured chat provider, not capability acceptance."""

import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def main():
    names = ['MIA_TEST_LLM_API_KEY', 'MIA_TEST_LLM_BASE_URL', 'MIA_TEST_LLM_MODEL']
    report = {'code_sha': os.environ.get('GITHUB_SHA'), 'kind': 'real_provider_connectivity_only',
              'configured': {name: bool(os.environ.get(name)) for name in names},
              'passed': False, 'capability_acceptance': 'not_executed',
              'limits': {'requests': 1, 'max_output_tokens': 128, 'timeout_seconds': 30, 'retries': 0}}
    output = Path(os.environ['MIA_TEST_REPORT_PATH'])
    if not all(report['configured'].values()):
        report['status'] = 'not_executed_missing_test_configuration'
        output.write_text(json.dumps(report, indent=2) + '\n')
        raise SystemExit('Dedicated test configuration missing; no provider request sent')
    base = os.environ[names[1]].rstrip('/')
    model = os.environ[names[2]]
    url = urllib.parse.urlsplit(base)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        report['status'] = 'not_executed_invalid_https_base_url'
        output.write_text(json.dumps(report, indent=2) + '\n')
        raise SystemExit('Test base URL must be a valid HTTPS API root')
    report['provider_host'] = url.hostname
    report['configuration_sha256'] = hashlib.sha256((base + '\n' + model).encode()).hexdigest()
    payload = {'model': model, 'stream': False, 'max_tokens': 128,
               'messages': [{'role': 'system', 'content': '请用中文简短回答。'},
                            {'role': 'user', 'content': '请用一句话说明遇到缺少信息的问题时应该怎么回答。'}]}
    # Match the existing pinned provider's Volcengine non-thinking request setting.
    if url.hostname == 'volces.com' or url.hostname.endswith('.volces.com'):
        payload['thinking'] = {'type': 'disabled'}
    request = urllib.request.Request(base + '/chat/completions', data=json.dumps(payload).encode(),
                                     headers={'Authorization': 'Bearer ' + os.environ[names[0]],
                                              'Content-Type': 'application/json'}, method='POST')
    opener = urllib.request.build_opener(NoRedirect(),
                                        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    started = time.perf_counter()
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(100001)
            if len(raw) > 100000:
                raise ValueError('Provider response exceeds probe limit')
            data = json.loads(raw)
        content = data['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError('Empty provider content')
        report.update(status='executed', passed=True, response_text=content,
                      response_model=data.get('model'), usage=data.get('usage'))
    except urllib.error.HTTPError as error:
        report.update(status='provider_http_error', http_status=error.code)
    except Exception as error:
        # Never log request headers, API key, raw response errors or environment.
        report.update(status='provider_or_transport_error', error_type=type(error).__name__)
    report['elapsed_ms'] = (time.perf_counter() - started) * 1000
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['kind', 'status', 'passed', 'capability_acceptance']}))
    if not report['passed']:
        raise SystemExit('Real provider probe did not pass; inspect sanitized report')


if __name__ == '__main__':
    main()
