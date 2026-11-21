# PEPTalk Data Sources and Licensing

This document tracks all external sources used to construct the authoritative corpus for PEPTalk (DEV-07), including formats, retrieval endpoints, and license terms.

## Record Schema
Each document record in PEPTalk contains the following standard attributes:
- `id`: Unique document identifier (e.g., `pep-0604`)
- `pep_number`: Official PEP number (integer, e.g., `604`)
- `title`: Canonical title of the proposal or release notes
- `status`: Official PEP status (e.g., `Final`, `Draft`, `Accepted`, `Active`)
- `type`: Document category (`PEP` or `ReleaseNotes`)
- `python_version`: Primary target CPython release version (e.g., `3.10`, `3.13`)
- `created`: Date of original publication or release (ISO format `YYYY-MM-DD`)

## Data Sources

| Source Name | Format | URL / Repository | Terms of Use / License |
|---|---|---|---|
| Python Enhancement Proposals (PEPs) | ReST / Markdown / Web Page | https://github.com/python/peps | Public Domain / Creative Commons Zero (CC0) |
| PEP Official Web Pages | HTML / Web Page | https://peps.python.org/ | Public Domain / Creative Commons Zero (CC0) |
| Python 3.8 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.8.html | Python Software Foundation (PSF) License |
| Python 3.9 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.9.html | Python Software Foundation (PSF) License |
| Python 3.10 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.10.html | Python Software Foundation (PSF) License |
| Python 3.11 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.11.html | Python Software Foundation (PSF) License |
| Python 3.12 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.12.html | Python Software Foundation (PSF) License |
| Python 3.13 What's New | HTML / Web Page | https://docs.python.org/3/whatsnew/3.13.html | Python Software Foundation (PSF) License |
| Python Release Documentation Index | HTML / Web Page | https://docs.python.org/3/whatsnew/index.html | Python Software Foundation (PSF) License |
