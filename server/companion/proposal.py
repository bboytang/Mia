"""One proposal function on the existing Provider; no tool execution or fact writes."""

from .memory import CATEGORIES, MemoryError


NAME = 'mia_memory_proposal'


def tool_definition(context, *, sources, natural, growth, significance, tracking, feedback=None):
    string = {'type': 'string'}
    ids = [row['id'] for row in context]
    identifier = dict(string, **({'enum': ids} if ids else {}))
    rejected = (feedback or {}).get('rejected_clues', {})
    def literal(field):
        item = dict(string, description='本次完整source_quote中的连续字面短语；不能压缩、拼接或改写。', maxLength=32)
        if field == 'reconciliation.anchor':
            item.update(minLength=2, description='同时是source_quote和old_quote的连续字面主题短语；不能连接分散的词。')
        if rejected.get(field):
            item['not'] = {'enum': rejected[field]}
        return item
    properties = {
        'category': {'type': 'string', 'enum': sorted(CATEGORIES)},
        'content': dict(string, maxLength=512, description='本次用户事实完整原句；explicit时等于source_quote，不能复制旧事实。'),
        'source_quote': dict(string, maxLength=512, description='本次user_excerpts中的完整实际事实原句，逗号不拆句。'),
        'source_index': {'type': 'integer', 'minimum': 0, 'maximum': len(sources) - 1},
        'kind': {'type': 'string', 'enum': ['explicit', 'inferred']},
        'subject': {'type': 'string', 'enum': ['user']},
        'value': {'type': 'string', 'enum': ['durable']},
        'sensitive': {'type': 'boolean', 'description': '医疗/财务/身体亲密/准确住址等敏感内容为true；普通爱好/日用品本身不需确认，不因表达重视自动true。'},
        'importance_weight': {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1,
            'description': '仅据本次明确肯定重视由模型评估数值；未表达或否定时null，与category/情绪开关无关。'},
        'importance_evidence': {'type': ['string', 'null'], 'description': '本次原句的肯定重要性短语；未表达或否定时null。'},
        'anchor': literal('anchor'),
        'reconciliation': {'type': 'object', 'properties': {
            'form': {'type': 'string', 'enum': ['natural']},
            'kind': {'type': 'string', 'enum': ['correction', 'time_change', 'conflict']},
            'target_id': identifier, 'old_quote': string, 'evidence': string,
            'old_value': literal('reconciliation.old_value'), 'new_value': literal('reconciliation.new_value'),
            'anchor': literal('reconciliation.anchor')},
            'required': ['kind', 'target_id', 'old_quote', 'evidence']},
        'relations': {'type': 'array', 'maxItems': 4, 'items': {'type': 'object', 'properties': {
            'target_id': identifier, 'relation': {'type': 'string', 'enum': ['shared_term']},
            'anchor': string, 'evidence': string}, 'required': ['target_id', 'relation', 'anchor', 'evidence']}}}
    for field in ('entities', 'keywords', 'trigger_terms'):
        properties[field] = {'type': 'array', 'maxItems': 8, 'items': literal(field)}
    if not significance:
        # No source has even the literal evidence required by the unchanged
        # validator. This restricts the schema, never fills a numeric value.
        properties['importance_weight'] = {'type': 'null'}
        properties['importance_evidence'] = {'type': 'null'}
    required = ['category', 'content', 'source_index', 'source_quote', 'kind', 'subject', 'value', 'sensitive',
                'entities', 'keywords', 'trigger_terms', 'importance_weight', 'importance_evidence', 'relations']
    if natural:
        for field in ('content', 'source_quote'):
            properties[field]['enum'] = sources
        proof = properties['reconciliation']
        proof['properties']['kind']['enum'] = ['correction']
        proof['required'] += ['form', 'old_value', 'new_value', 'anchor']
        required.append('reconciliation')
    trait = {'type': 'null'}
    if growth:
        trait = {'anyOf': [{'type': 'null'}, {'type': 'object', 'properties': {
            'name': dict(string, maxLength=32), 'description': dict(string, maxLength=256), 'anchor': string,
            'evidence_ids': {'type': 'array', 'minItems': 3, 'maxItems': 16, 'uniqueItems': True, 'items': identifier},
            'evidence_quotes': {'type': 'array', 'minItems': 3, 'maxItems': 16, 'items': {'type': 'object',
                'properties': {'id': identifier, 'quote': string}, 'required': ['id', 'quote']}}},
            'required': ['name', 'description', 'anchor', 'evidence_ids', 'evidence_quotes']}]}
    parameters = {'type': 'object', 'properties': {
        'memories': {'type': 'array', 'maxItems': 16, 'items': {'type': 'object', 'properties': properties, 'required': required}},
        'trait': trait}, 'required': ['memories', 'trait']}
    if tracking:
        parameters['properties']['observations'] = {'type': 'array', 'maxItems': 1, 'items': {'type': 'object',
            'properties': {'source_index': properties['source_index'], 'source_quote': string,
                'subject': {'type': 'string', 'enum': ['user']},
                'source_kind': {'type': 'string', 'enum': ['self_report', 'inferred']},
                'tendency': {'type': 'string', 'enum': ['positive', 'negative', 'neutral', 'mixed']},
                'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1}},
            'required': ['source_index', 'source_quote', 'subject', 'source_kind', 'tendency', 'confidence']}}
    return {'type': 'function', 'function': {'name': NAME,
        'description': '仅提交由实际用户来源支持的记忆/特点提案；不执行工具、不表示已保存。', 'parameters': parameters}}


def read_stream(stream):
    """Concatenate original deltas only; reject ambiguous/mixed tool proposals."""
    text, name, arguments, identity = '', '', '', None
    seen = False
    try:
        for content, calls in stream:
            text += content or ''
            for call in calls or []:
                seen = True
                if call.index != 0 or (identity and call.id and call.id != identity):
                    raise MemoryError('invalid_input', 'Ambiguous extraction function calls')
                identity = call.id or identity
                function = call.function
                name += (function.name or '') if function else ''
                arguments += (function.arguments or '') if function else ''
            if len(text) + len(arguments) > 32768 or len(name) > 64:
                raise MemoryError('invalid_input', 'Extraction proposal exceeds bound')
        if seen:
            if name != NAME or not arguments or text.strip():
                raise MemoryError('invalid_input', 'Invalid extraction function proposal')
            return arguments
        return text  # Existing providers may stream plain JSON instead of a tool.
    finally:
        close = getattr(stream, 'close', None)
        if close:
            close()
