# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import logging
import re

from .model import PatternKind
from .spanParser import Span

log = logging.getLogger(__name__)

EMOJI_PATTERN = "[\U0001f000-\U0001faff\U0001f1e6-\U0001f1ff←-⇿⌀-⏿①-➿⬀-⯿️‍⃣♀♂]+"

_compiled = {}


def _source(rule):
    if rule.kind == PatternKind.EMOJI:
        return EMOJI_PATTERN
    if rule.kind == PatternKind.REGEX:
        return rule.pattern
    escaped = re.escape(rule.pattern)
    return rf"\b{escaped}\b" if rule.kind == PatternKind.WORD else escaped


def compiled(rule):
    key = (rule.kind.value, rule.pattern, rule.caseSensitive)
    if key not in _compiled:
        _compiled[key] = _compile(rule)
    return _compiled[key]


def _compile(rule):
    if not rule.isValid:
        return None
    try:
        return re.compile(_source(rule), 0 if rule.caseSensitive else re.IGNORECASE)
    except re.error:
        log.warning(f"Cannot use the pattern {rule.pattern!r} of the rule {rule.name!r}", exc_info=True)
        return None


def patternError(rule):
    if not rule.isValid:
        return ""
    try:
        re.compile(_source(rule))
    except re.error as e:
        return str(e)
    return None


def findMatches(text, rules):
    spans = []
    taken = []
    for rule in rules:
        expression = compiled(rule)
        if expression is None:
            continue
        for match in expression.finditer(text):
            start, end = match.span()
            if start == end or any(start < other[1] and end > other[0] for other in taken):
                continue
            taken.append((start, end))
            spans.append(Span(rule, start, start, end, end, hidden=rule.hideText))
    return spans
