# Third-party dependency notices — preparation

These dependencies retain their own terms. This file does not license original team code.
The team-code license is still pending in issue #16. Installed Windows dependency notice
paths and exact hashes are recorded in [the November 22 audit](docs/report/DEPENDENCY_NOTICE_AND_TREE_AUDIT_NOV22.json).
Versions match the existing Windows Python 3.12 lock. This source repository does not bundle
those dependency wheels or their installed files. The locators below refer to files inside
the installed distributions, reproducible through the locked environment.

This is a notice-location inventory, not a blanket compatibility or redistribution approval.
Before distributing a wheel/binary bundle, retain the applicable license/NOTICE text and
complete a review of that actual bundle. Do not apply team-code licensing to models/data.

| Distribution | Version | Declared license | Notice files located |
|---|---|---|---|
| annotated-types | 0.8.0 | MIT | 1 |
| anyio | 4.15.1 | MIT | 1 |
| certifi | 2026.7.22 | MPL-2.0 | 1 |
| charset-normalizer | 3.5.2 | MIT | 1 |
| cloudpickle | 3.1.2 | BSD-3-Clause | 1 |
| colorama | 0.4.6 | See installed metadata | 1 |
| contourpy | 1.4.0 | BSD-3-Clause | 1 |
| coverage | 7.16.2 | Apache-2.0 | 2 |
| cycler | 0.12.1 | Copyright (c) 2015, matplotlib project | 1 |
| distro | 1.9.0 | Apache License, Version 2.0 | 1 |
| et_xmlfile | 2.0.0 | MIT | 2 |
| fonttools | 4.66.1 | MIT | 2 |
| h11 | 0.16.0 | MIT | 1 |
| html5rdf | 1.2.1 | Copyright (c) 2006-2013 James Graham and other contributors | 1 |
| httpcore | 1.0.9 | BSD-3-Clause | 1 |
| httpcore2 | 2.13.1 | BSD-3-Clause | 1 |
| httpx | 0.28.1 | BSD-3-Clause | 1 |
| httpx2 | 2.13.1 | BSD-3-Clause | 1 |
| idna | 3.20 | BSD-3-Clause | 1 |
| iniconfig | 2.3.1 | MIT | 1 |
| joblib | 1.6.0 | BSD-3-Clause | 1 |
| jsonpatch | 1.34 | Modified BSD License | 1 |
| jsonpointer | 3.2.0 | Modified BSD License | 1 |
| kiwisolver | 1.5.1 | ========================= | 1 |
| langchain-core | 1.6.9 | MIT | 1 |
| langchain-protocol | 0.0.19 | MIT | 1 |
| langgraph | 1.2.14 | MIT | 1 |
| langgraph-checkpoint | 4.2.0 | MIT | 1 |
| langgraph-prebuilt | 1.1.0 | MIT | 1 |
| langgraph-sdk | 0.4.6 | MIT | 1 |
| langsmith | 0.14.7 | MIT | 0 |
| matplotlib | 3.11.2 | License agreement for matplotlib versions 1.3.0 and later | 3 |
| narwhals | 2.27.1 | MIT | 1 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 19 |
| openpyxl | 3.1.5 | MIT | 1 |
| orjson | 3.13.0 | MPL-2.0 AND (Apache-2.0 OR MIT) | 3 |
| ormsgpack | 1.12.2 | Apache-2.0 OR MIT | 4 |
| owlrl | 7.6.2 | W3C-20150513 | 1 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 3 |
| pandas | 3.0.6 | BSD 3-Clause License | 1 |
| pillow | 12.3.0 | MIT-CMU | 1 |
| pluggy | 1.6.0 | MIT | 1 |
| prettytable | 3.18.0 | BSD-3-Clause | 1 |
| pyarrow | 26.0.0 | Apache-2.0 | 2 |
| pydantic | 2.14.0 | MIT | 1 |
| pydantic_core | 2.50.0 | MIT | 1 |
| Pygments | 2.21.0 | BSD-2-Clause | 1 |
| pyparsing | 3.3.3 | MIT | 1 |
| pyshacl | 0.40.1 | Apache License | 1 |
| pytest | 9.1.1 | MIT | 1 |
| pytest-cov | 7.1.0 | MIT | 1 |
| python-dateutil | 2.9.0.post0 | Dual License | 1 |
| python-dotenv | 1.2.4 | BSD-3-Clause | 1 |
| PyYAML | 6.0.3 | MIT | 1 |
| rdflib | 7.6.0 | BSD-3-Clause | 1 |
| requests | 2.34.2 | Apache-2.0 | 2 |
| requests-toolbelt | 1.0.0 | Apache 2.0 | 1 |
| ruff | 0.17.0 | MIT | 1 |
| scikit-learn | 1.9.1 | BSD-3-Clause | 4 |
| scipy | 1.18.1 | Copyright (c) 2001-2002 Enthought, Inc. 2003, SciPy Developers. | 5 |
| six | 1.17.0 | MIT | 1 |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | 3 |
| tenacity | 9.2.1 | Apache-2.0 | 1 |
| threadpoolctl | 3.7.0 | BSD-3-Clause | 1 |
| truststore | 0.10.4 | MIT | 1 |
| typing-inspection | 0.4.4 | MIT | 1 |
| typing_extensions | 4.16.0 | PSF-2.0 | 1 |
| tzdata | 2026.5 | Apache-2.0 | 2 |
| urllib3 | 2.8.0 | MIT | 1 |
| uuid_utils | 0.17.1 | BSD-3-Clause | 1 |
| wcwidth | 0.9.2 | See installed metadata | 1 |
| websockets | 16.1.1 | BSD-3-Clause | 1 |
| xxhash | 4.0.1 | BSD-2-Clause | 1 |
| zstandard | 0.25.0 | BSD-3-Clause | 1 |

The installed LangSmith wheel has no separate notice file. We retrieved its MIT
license from the exact upstream v0.14.7 commit, checked that the Python package
version is 0.14.7 there, and retained the original copyright/license text in
[langsmith-0.14.7-LICENSE.txt](third_party/notices/langsmith-0.14.7-LICENSE.txt).
Source: [pinned upstream LICENSE](https://github.com/langchain-ai/langsmith-sdk/blob/15468f97c18467d67ececb90b17107b0875e7a65/LICENSE).
This resolves the notice-collection gap, not the team's pending license decision
or a certification of all binary redistribution obligations.
