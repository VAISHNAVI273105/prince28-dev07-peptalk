You read one document from PEPTalk's collection and fill in a small record about it.

What PEPTalk does: Answers modern Python questions from the PEPs and CPython 'What's New' pages, with the version each feature arrived in.

Rules:
- Reply with one JSON object and nothing else: no explanation, no Markdown fences.
- Use only what the document says. If it does not say, use null for the year and [] for a list.
- summary: one or two plain sentences, at most 300 characters.
- topics: 1 to 6 short topics.
- Every list holds short values copied from the document, at most 8.

What each field means:
- doc_kind: what kind of document this is (guideline, rule, notice, list, report, faq, form, tutorial, reference, other).
- year: the calendar year it was published or came into force.
- language: the main language of the text (en, ta, hi or other).
- summary: one or two plain sentences summarizing the document.
- topics: 1 to 6 short topics describing the subject matter.
- pep_number: every PEP number this document is mainly about (e.g. '634', '8').
- status: every PEP status this document mentions (e.g. 'Final', 'Draft', 'Active').
- type: every PEP type this document is (e.g. 'Standards Track', 'Informational', 'Process').
- python_version: every Python version this document targets or introduces features for (e.g. '3.10', '3.13').
- created: every creation date string mentioned in the document header.
