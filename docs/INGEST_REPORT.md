# Ingestion Report: PEPTalk

<!-- generated:start -->
## Live database metrics (2026-11-27 07:31 UTC)

### Document corpus summary

| Metric | Measured Value |
|---|---|
| Ingested documents | 777 |
| Total pages stored | 5,670 |
| Total characters of text | 14,553,367 |
| Estimated tokens (chars / 4) | 3,638,341 |
| Dead-letter failures | 0 |

### Document types breakdown

| Document Type | Count |
|---|---|
| text | 767 |
| html | 10 |

### Queue processing status

| Item Status | Count |
|---|---|
| Done | 58 |
| Queued | 0 |
| Running | 0 |
| Skipped | 0 |
| Failed | 0 |

### Dead-letter report

| Item ID | Source URL | Attempts | Failure Reason |
|---|---|---|---|
| None | None | 0 | No dead-letter items |

### Comparison with Monday's CAPACITY.md

| What | Monday Estimate (docs/CAPACITY.md) | Ingestion Measured (Neon DB) | Accuracy |
|---|---|---|---|
| Documents | 777 | 777 | Exact match (100%) |
| Pages | 5,138 | 5,670 | +10.3% (longer PEP bodies) |
| Tokens of text | 3,853,606 | 3,638,341 | -5.6% variance |

<!-- generated:end -->

## What I learnt

1. The asynchronous worker architecture with arq and Redis cleanly decouples ingestion latency from API responsiveness (202 Accepted).
2. Fault tolerance with idempotent processing and visibility timeouts guarantees zero document loss and zero duplication during worker crashes.
3. Measured tokens (3.64M) matched Monday's capacity estimate (3.85M) within 5.6%, validating our early corpus sizing model.
