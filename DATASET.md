# Dataset: PEPTalk

Answers modern Python questions from the PEPs and CPython 'What's New' pages, with the version each feature arrived in.

- **Start target:** Final + Active PEPs and What's New 3.10-3.13
- **Full target:** All PEPs + What's New 3.8-latest (1,500+ documents)
- **Parsing coverage:** 100% of files (777/777 parsed into PostgreSQL, 0 failed, 5,692 pages)
- **Collected by:** `scripts/fetch.py` as `examate-student-bot` (https://github.com/VAISHNAVI273105/prince28-dev07-peptalk): robots.txt respected, at most 4 requests at once, 0.5 s between requests to one site.

## Where the documents come from

- https://github.com/python/peps
- https://docs.python.org/3/whatsnew/index.html

## Terms I follow

PEPs are public domain or CC0; Python docs PSF licence.

- Every answer links to the original document.
- No personal data is collected.

<!-- generated:start -->
## Sources (generated 2026-11-23 14:46 UTC by scripts/dataset_report.py)

| Source | Licence / terms | Files | MB | Pages* | How | Fetched | Example URL |
|---|---|---|---|---|---|---|---|
| peps | PEPs are public domain or CC0; Python docs PSF licence. | 767 | 14.8 | 4,941 | git @ 4434e728a7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/api/index.rst |
| peps-web | Public domain or CC0 | 6 | 0.6 | 72 | http | 2026-11-23 | https://peps.python.org/pep-0008/ |
| python-docs | PSF License | 4 | 1.6 | 125 | http | 2026-11-23 | https://docs.python.org/3/whatsnew/3.10.html |

**Total:** 777 files, 17.0 MB, 5,138 pages. Not downloaded: 0 blocked by robots.txt, 0 failed.

*Pages = PDF pages, plus one page per 3,000 characters of text or HTML.

## Files (first 200 of 777)

The complete list, with a sha256 fingerprint of every file, is `data/manifest.jsonl`.

| # | Title / file | Source | Pages | Fetched | URL |
|---|---|---|---|---|---|
| 1 | peps/api/index.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/api/index.rst |
| 2 | peps/contents.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/contents.rst |
| 3 | peps/docs/build.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/docs/build.rst |
| 4 | peps/docs/index.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/docs/index.rst |
| 5 | peps/docs/rendering_system.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/docs/rendering_system.rst |
| 6 | peps/pep-0001.rst | peps | 14 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0001.rst |
| 7 | peps/pep-0002.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0002.rst |
| 8 | peps/pep-0003.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0003.rst |
| 9 | peps/pep-0004.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0004.rst |
| 10 | peps/pep-0005.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0005.rst |
| 11 | peps/pep-0006.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0006.rst |
| 12 | peps/pep-0007.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0007.rst |
| 13 | peps/pep-0008.rst | peps | 17 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0008.rst |
| 14 | peps/pep-0009.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0009.rst |
| 15 | peps/pep-0010.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0010.rst |
| 16 | peps/pep-0011.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0011.rst |
| 17 | peps/pep-0012.rst | peps | 9 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0012.rst |
| 18 | peps/pep-0012/pep-NNNN.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0012/pep-NNNN.rst |
| 19 | peps/pep-0013.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0013.rst |
| 20 | peps/pep-0020.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0020.rst |
| 21 | peps/pep-0042.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0042.rst |
| 22 | peps/pep-0100.rst | peps | 14 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0100.rst |
| 23 | peps/pep-0101.rst | peps | 11 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0101.rst |
| 24 | peps/pep-0102.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0102.rst |
| 25 | peps/pep-0103.rst | peps | 13 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0103.rst |
| 26 | peps/pep-0160.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0160.rst |
| 27 | peps/pep-0200.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0200.rst |
| 28 | peps/pep-0201.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0201.rst |
| 29 | peps/pep-0202.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0202.rst |
| 30 | peps/pep-0203.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0203.rst |
| 31 | peps/pep-0204.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0204.rst |
| 32 | peps/pep-0205.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0205.rst |
| 33 | peps/pep-0206.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0206.rst |
| 34 | peps/pep-0207.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0207.rst |
| 35 | peps/pep-0208.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0208.rst |
| 36 | peps/pep-0209.rst | peps | 10 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0209.rst |
| 37 | peps/pep-0210.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0210.rst |
| 38 | peps/pep-0211.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0211.rst |
| 39 | peps/pep-0212.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0212.rst |
| 40 | peps/pep-0213.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0213.rst |
| 41 | peps/pep-0214.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0214.rst |
| 42 | peps/pep-0215.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0215.rst |
| 43 | peps/pep-0216.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0216.rst |
| 44 | peps/pep-0217.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0217.rst |
| 45 | peps/pep-0218.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0218.rst |
| 46 | peps/pep-0219.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0219.rst |
| 47 | peps/pep-0220.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0220.rst |
| 48 | peps/pep-0221.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0221.rst |
| 49 | peps/pep-0222.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0222.rst |
| 50 | peps/pep-0223.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0223.rst |
| 51 | peps/pep-0224.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0224.rst |
| 52 | peps/pep-0225.rst | peps | 10 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0225.rst |
| 53 | peps/pep-0226.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0226.rst |
| 54 | peps/pep-0227.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0227.rst |
| 55 | peps/pep-0228.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0228.rst |
| 56 | peps/pep-0229.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0229.rst |
| 57 | peps/pep-0230.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0230.rst |
| 58 | peps/pep-0231.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0231.rst |
| 59 | peps/pep-0232.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0232.rst |
| 60 | peps/pep-0233.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0233.rst |
| 61 | peps/pep-0234.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0234.rst |
| 62 | peps/pep-0235.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0235.rst |
| 63 | peps/pep-0236.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0236.rst |
| 64 | peps/pep-0237.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0237.rst |
| 65 | peps/pep-0238.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0238.rst |
| 66 | peps/pep-0239.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0239.rst |
| 67 | peps/pep-0240.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0240.rst |
| 68 | peps/pep-0241.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0241.rst |
| 69 | peps/pep-0242.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0242.rst |
| 70 | peps/pep-0243.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0243.rst |
| 71 | peps/pep-0244.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0244.rst |
| 72 | peps/pep-0245.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0245.rst |
| 73 | peps/pep-0246.rst | peps | 10 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0246.rst |
| 74 | peps/pep-0247.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0247.rst |
| 75 | peps/pep-0248.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0248.rst |
| 76 | peps/pep-0249.rst | peps | 15 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0249.rst |
| 77 | peps/pep-0250.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0250.rst |
| 78 | peps/pep-0251.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0251.rst |
| 79 | peps/pep-0252.rst | peps | 10 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0252.rst |
| 80 | peps/pep-0253.rst | peps | 14 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0253.rst |
| 81 | peps/pep-0254.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0254.rst |
| 82 | peps/pep-0255.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0255.rst |
| 83 | peps/pep-0256.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0256.rst |
| 84 | peps/pep-0257.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0257.rst |
| 85 | peps/pep-0258.rst | peps | 12 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0258.rst |
| 86 | peps/pep-0259.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0259.rst |
| 87 | peps/pep-0260.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0260.rst |
| 88 | peps/pep-0261.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0261.rst |
| 89 | peps/pep-0262.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0262.rst |
| 90 | peps/pep-0263.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0263.rst |
| 91 | peps/pep-0264.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0264.rst |
| 92 | peps/pep-0265.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0265.rst |
| 93 | peps/pep-0266.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0266.rst |
| 94 | peps/pep-0267.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0267.rst |
| 95 | peps/pep-0268.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0268.rst |
| 96 | peps/pep-0269.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0269.rst |
| 97 | peps/pep-0270.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0270.rst |
| 98 | peps/pep-0271.rst | peps |  | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0271.rst |
| 99 | peps/pep-0272.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0272.rst |
| 100 | peps/pep-0273.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0273.rst |
| 101 | peps/pep-0274.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0274.rst |
| 102 | peps/pep-0275.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0275.rst |
| 103 | peps/pep-0276.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0276.rst |
| 104 | peps/pep-0277.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0277.rst |
| 105 | peps/pep-0278.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0278.rst |
| 106 | peps/pep-0279.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0279.rst |
| 107 | peps/pep-0280.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0280.rst |
| 108 | peps/pep-0281.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0281.rst |
| 109 | peps/pep-0282.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0282.rst |
| 110 | peps/pep-0283.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0283.rst |
| 111 | peps/pep-0284.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0284.rst |
| 112 | peps/pep-0285.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0285.rst |
| 113 | peps/pep-0286.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0286.rst |
| 114 | peps/pep-0287.rst | peps | 11 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0287.rst |
| 115 | peps/pep-0288.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0288.rst |
| 116 | peps/pep-0289.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0289.rst |
| 117 | peps/pep-0290.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0290.rst |
| 118 | peps/pep-0291.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0291.rst |
| 119 | peps/pep-0292.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0292.rst |
| 120 | peps/pep-0293.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0293.rst |
| 121 | peps/pep-0294.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0294.rst |
| 122 | peps/pep-0295.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0295.rst |
| 123 | peps/pep-0296.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0296.rst |
| 124 | peps/pep-0297.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0297.rst |
| 125 | peps/pep-0298.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0298.rst |
| 126 | peps/pep-0299.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0299.rst |
| 127 | peps/pep-0301.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0301.rst |
| 128 | peps/pep-0302.rst | peps | 9 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0302.rst |
| 129 | peps/pep-0303.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0303.rst |
| 130 | peps/pep-0304.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0304.rst |
| 131 | peps/pep-0305.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0305.rst |
| 132 | peps/pep-0306.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0306.rst |
| 133 | peps/pep-0307.rst | peps | 12 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0307.rst |
| 134 | peps/pep-0308.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0308.rst |
| 135 | peps/pep-0309.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0309.rst |
| 136 | peps/pep-0310.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0310.rst |
| 137 | peps/pep-0311.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0311.rst |
| 138 | peps/pep-0312.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0312.rst |
| 139 | peps/pep-0313.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0313.rst |
| 140 | peps/pep-0314.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0314.rst |
| 141 | peps/pep-0315.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0315.rst |
| 142 | peps/pep-0316.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0316.rst |
| 143 | peps/pep-0317.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0317.rst |
| 144 | peps/pep-0318.rst | peps | 10 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0318.rst |
| 145 | peps/pep-0319.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0319.rst |
| 146 | peps/pep-0320.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0320.rst |
| 147 | peps/pep-0321.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0321.rst |
| 148 | peps/pep-0322.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0322.rst |
| 149 | peps/pep-0323.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0323.rst |
| 150 | peps/pep-0324.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0324.rst |
| 151 | peps/pep-0325.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0325.rst |
| 152 | peps/pep-0326.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0326.rst |
| 153 | peps/pep-0327.rst | peps | 13 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0327.rst |
| 154 | peps/pep-0328.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0328.rst |
| 155 | peps/pep-0329.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0329.rst |
| 156 | peps/pep-0330.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0330.rst |
| 157 | peps/pep-0331.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0331.rst |
| 158 | peps/pep-0332.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0332.rst |
| 159 | peps/pep-0333.rst | peps | 25 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0333.rst |
| 160 | peps/pep-0334.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0334.rst |
| 161 | peps/pep-0335.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0335.rst |
| 162 | peps/pep-0336.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0336.rst |
| 163 | peps/pep-0337.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0337.rst |
| 164 | peps/pep-0338.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0338.rst |
| 165 | peps/pep-0339.rst | peps | 8 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0339.rst |
| 166 | peps/pep-0340.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0340.rst |
| 167 | peps/pep-0341.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0341.rst |
| 168 | peps/pep-0342.rst | peps | 8 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0342.rst |
| 169 | peps/pep-0343.rst | peps | 12 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0343.rst |
| 170 | peps/pep-0344.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0344.rst |
| 171 | peps/pep-0345.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0345.rst |
| 172 | peps/pep-0346.rst | peps | 15 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0346.rst |
| 173 | peps/pep-0347.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0347.rst |
| 174 | peps/pep-0348.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0348.rst |
| 175 | peps/pep-0349.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0349.rst |
| 176 | peps/pep-0350.rst | peps | 8 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0350.rst |
| 177 | peps/pep-0351.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0351.rst |
| 178 | peps/pep-0352.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0352.rst |
| 179 | peps/pep-0353.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0353.rst |
| 180 | peps/pep-0354.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0354.rst |
| 181 | peps/pep-0355.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0355.rst |
| 182 | peps/pep-0356.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0356.rst |
| 183 | peps/pep-0357.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0357.rst |
| 184 | peps/pep-0358.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0358.rst |
| 185 | peps/pep-0359.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0359.rst |
| 186 | peps/pep-0360.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0360.rst |
| 187 | peps/pep-0361.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0361.rst |
| 188 | peps/pep-0362.rst | peps | 6 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0362.rst |
| 189 | peps/pep-0363.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0363.rst |
| 190 | peps/pep-0364.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0364.rst |
| 191 | peps/pep-0365.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0365.rst |
| 192 | peps/pep-0366.rst | peps | 2 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0366.rst |
| 193 | peps/pep-0367.rst | peps | 7 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0367.rst |
| 194 | peps/pep-0368.rst | peps | 12 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0368.rst |
| 195 | peps/pep-0369.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0369.rst |
| 196 | peps/pep-0370.rst | peps | 3 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0370.rst |
| 197 | peps/pep-0371.rst | peps | 5 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0371.rst |
| 198 | peps/pep-0372.rst | peps | 4 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0372.rst |
| 199 | peps/pep-0373.rst | peps | 1 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0373.rst |
| 200 | peps/pep-0374.rst | peps | 18 | 2026-11-23 | https://github.com/python/peps/blob/HEAD/peps/pep-0374.rst |
<!-- generated:end -->

## Known gaps

- The start target (Final + Active PEPs and What's New 3.10-3.13) is collected: 767 PEPs via Door 2 shallow git clone, 4 What's New releases (3.10 to 3.13), and 6 key PEP reference HTML files via Door 1.
- Gaps toward the 1,500 full target: older What's New documents (Python 3.8 and 3.9), CPython release changelogs, and historical PEP supplementary attachments, which will be fetched in subsequent ingestion cycles.
