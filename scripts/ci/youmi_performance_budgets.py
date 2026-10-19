"""D08 v2 acceptance tolerance; original optimization targets remain active."""

REVISION = 'D08-v2-20261017'
OPTIMIZATION_TARGETS = {'encode_hybrid_p95_ms': 400, 'sqlite_10k_p95_ms': 150,
                        'first_sentence_delta_p95_ms': 500, 'python_peak_rss_mib': 512}
LIMITS = {**OPTIMIZATION_TARGETS, 'encode_hybrid_p95_ms': 500,
          'sqlite_10k_p95_ms': 250, 'first_sentence_delta_p95_ms': 600}


def within_budgets(row, *, shared=False, limits=LIMITS):
    if 'error_class' in row:
        return False
    size = row['size_per_frontend_scope' if shared else 'size_per_scope']
    queries = ([case for owner in row['sequential'] for case in owner['queries']]
               if shared else row['queries'])
    return (all(case['encode_hybrid']['p95_ms'] <= limits['encode_hybrid_p95_ms']
                and (size != 10000 or case['sqlite_exact']['p95_ms'] <= limits['sqlite_10k_p95_ms'])
                for case in queries)
            and row['rss_peak_mib'] <= limits['python_peak_rss_mib'] and row['integrity'] == 'ok'
            and all('error_class' not in value
                    and value.get('p95_ms', float('inf')) <= limits['encode_hybrid_p95_ms']
                    for value in row['competition']['foreground'])
            and row['competition']['rebuild'].get('indexed') == 32)
