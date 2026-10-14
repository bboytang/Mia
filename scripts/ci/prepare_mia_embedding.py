"""Export pinned public BGE weights for the isolated P06 inference experiment."""

import argparse
import hashlib
import json
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModel, AutoTokenizer


class LastHiddenState(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask, token_type_ids):
        return self.model(input_ids=input_ids, attention_mask=attention_mask,
                          token_type_ids=token_type_ids).last_hidden_state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision,
                                             trust_remote_code=False)
    model = AutoModel.from_pretrained(args.model, revision=args.revision,
                                     trust_remote_code=False, weights_only=True,
                                     attn_implementation='eager')
    model.eval()
    tokenizer.save_pretrained(args.output)
    sample = tokenizer(['中文语义检索测试'], return_tensors='pt')
    names = ['input_ids', 'attention_mask', 'token_type_ids']
    path = args.output / 'model.onnx'
    with torch.no_grad():
        torch.onnx.export(LastHiddenState(model), tuple(sample[n] for n in names),
                          str(path), input_names=names, output_names=['hidden_state'],
                          dynamic_axes={n: {0: 'batch', 1: 'sequence'} for n in names + ['hidden_state']},
                          opset_version=17, do_constant_folding=True, dynamo=False)
    quantized = args.output / 'model-int8.onnx'
    quantize_dynamic(str(path), str(quantized), weight_type=QuantType.QInt8,
                     op_types_to_quantize=['MatMul', 'Gemm'],
                     extra_options={'MatMulConstBOnly': True})
    metadata = {'model': args.model, 'revision': args.revision,
                'dimension': model.config.hidden_size, 'max_tokens': 512,
                'query_prefix': '为这个句子生成表示以用于检索相关文章：',
                'pooling': 'CLS', 'normalized': True, 'models': {}, 'reference_vectors': []}
    for text in ['测试文字', '雨后的树林很安静。', '出行之前要检查天气。', '喝热水还是冷水？']:
        for query in [False, True]:
            encoded = tokenizer((metadata['query_prefix'] if query else '') + text,
                                return_tensors='pt', truncation=True, max_length=512)
            with torch.no_grad():
                vector = model(**encoded).last_hidden_state[0, 0]
                vector = torch.nn.functional.normalize(vector, dim=0)
            metadata['reference_vectors'].append({'text': text, 'query': query, 'vector': vector.tolist()})
    for item in [path, quantized]:
        metadata['models'][item.name] = {'sha256': hashlib.sha256(item.read_bytes()).hexdigest(),
                                        'bytes': item.stat().st_size}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
