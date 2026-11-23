# Capacity plan: PEPTalk

Full corpus target: All PEPs + What's New 3.8-latest (1,500+ documents)

<!-- generated:start -->
## Measured on my start corpus (2026-11-23 14:46 UTC)

| What | Value |
|---|---|
| Files | 777 |
| Size on disk | 17.0 MB |
| Pages (PDF pages + 1 per 3,000 characters of text/HTML) | 5,138 |
| Characters of text | 15,414,425 |
| Estimated tokens (characters / 4) | 3,853,606 |
| Tokens per page | 750 |
| PDFs with almost no text (scanned? OCR is Day 7) | 0 |
| Files not measured (zip, xlsx, unreadable) | 0 |

## Estimate for the full corpus (target: 1,500 files)

| What | How | Value |
|---|---|---|
| Scale factor | target / measured | x 1.9 |
| Tokens | measured tokens x scale | 7.44 M |
| Raw files | measured MB x scale | 33 MB |
| Chunks | tokens / 400 x 1.15 overlap | 21,388 |
| Embedding cost, one time | tokens x 1.15 x $0.15 per 1M | $1.28 = Rs 122 |
| Vector storage | chunks x 768 numbers x 4 bytes | 66 MB |
| Text in Postgres | characters x scale x 1.2 | 36 MB |

Assumptions: 4 characters per token, 400-token chunks, 768-dimension embeddings at $0.15 per 1M tokens, Rs 95 per US dollar.
<!-- generated:end -->

## What I conclude

1. Is embedding cost a problem for this product? (1 line, with the number)
No, the one-time embedding cost for the full corpus (~7.44M tokens) is only $1.28 (Rs 122), which is completely negligible.

2. Do the vectors and text fit in my free Postgres? (1 line: compare with the storage limit on my database dashboard)
Yes, combined vector storage (66 MB) and text (36 MB) equals ~102 MB, well below the 500 MB storage limit on Neon free tier.

3. Which number above am I least sure about, and how will I measure it better? (1 line)
The 4 characters per token estimate; I will measure it accurately using the embedding model's actual tokenizer (tiktoken / BPE) in Day 07.

4. What changes if the corpus grows 10 times? (2 lines)
Embedding cost remains affordable (~Rs 1,220), but storage grows to ~1.02 GB, exceeding the free 500 MB Postgres quota.
We will need HNSW/IVFFlat index memory tuning or a tiered storage plan with cold document caching.
