"""Explicit user-authorized CI model comparison; never a production fallback."""

import os
import re


APPROVED_MODELS = ('glm-5.3-flash', 'glm-5.3-flashx', 'glm-4.7-flash')


def safe_provider_error(error):
    result = {'error_class': type(error).__name__}
    status = getattr(error, 'status_code', None)
    code = getattr(error, 'code', None)
    if type(status) is int:
        result['status_code'] = status
    if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}', code):
        result['code'] = code
    causes, current = [], error.__cause__
    while current is not None and len(causes) < 8:
        causes.append(type(current).__name__)
        current = current.__cause__
    result['causes'] = causes
    return result  # No exception message, response body, headers or credentials.


def requested_model():
    model = os.environ.get('MIA_TEST_MODEL_OVERRIDE', '')
    if model and model not in APPROVED_MODELS:
        raise ValueError('Unapproved isolated comparison model')
    return model


def selected_model(baseline):
    return requested_model() or baseline


def output_tokens():
    return 4096 if requested_model() else 768


def context_window():
    return 16384 if requested_model() else 8192


def configure_provider(provider):
    model = requested_model()
    if not model:
        return None
    if provider.model_name != model:
        raise ValueError('Actual provider differs from authorized comparison model')

    def enable_required_thinking(params):
        # Freeze enabled thinking for this isolated comparison, including 4.7.
        # This does not claim all models require it. Preserve Provider/raw output.
        body = params.setdefault('extra_body', {})
        body['thinking'] = {'type': 'enabled'}
        if params.get('tools'):
            body['tool_stream'] = True
    provider._apply_thinking_disabled = enable_required_thinking
    return {'model': model, 'thinking': 'enabled', 'tool_stream_for_functions': True,
            'output_tokens': output_tokens(), 'ci_context_window': context_window(),
            'scope': 'Explicit isolated comparison only; production configuration and Secrets unchanged',
            'official_source': ('https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash'
                                if model == 'glm-4.7-flash' else
                                'https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash')}
