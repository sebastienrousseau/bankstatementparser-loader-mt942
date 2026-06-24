# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""bankstatementparser-loader-mt942: SWIFT MT942 loader.

A focused companion to the
`bankstatementparser <https://github.com/sebastienrousseau/bankstatementparser>`_
library that parses SWIFT **MT942 Interim Transaction Report** files —
a format the core library does not support — into
:class:`bankstatementparser.transaction_models.Transaction` objects.
"""

from bankstatementparser_loader_mt942.loader import (
    Mt942Summary,
    load_mt942,
    load_mt942_file,
    summarize_mt942,
)

__all__ = [
    "Mt942Summary",
    "load_mt942",
    "load_mt942_file",
    "summarize_mt942",
]

__version__ = "0.0.12"
