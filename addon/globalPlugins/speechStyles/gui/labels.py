# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import addonHandler

from ..model import (
    ALL_CONTEXTS,
    ContextGroup,
    DelimiterSpeech,
    ElementPart,
    ParamMode,
    PatternKind,
    Scope,
    SoundPosition,
    SoundType,
    TargetType,
    TextCategory,
    TextKind,
)
from ..profiles import SETTINGS
from ..targets import TARGET_TYPE_LABELS, describeTarget, targetChoices, targetValueLabel

addonHandler.initTranslation()

PARAM_MODES = (ParamMode.UNCHANGED, ParamMode.ABSOLUTE, ParamMode.RELATIVE)
PARAM_MODE_LABELS = {
    # Translators: A choice for a speech setting such as pitch: it is not changed.
    ParamMode.UNCHANGED: _("Unchanged"),
    # Translators: A choice for a speech setting such as pitch: it is set to a fixed value.
    ParamMode.ABSOLUTE: _("Set to"),
    # Translators: A choice for a speech setting such as pitch: the configured value is raised or lowered.
    ParamMode.RELATIVE: _("Change by"),
}

SETTING_LABELS = {
    # Translators: The name of a speech setting.
    "volume": _("&Volume"),
    # Translators: The name of a speech setting.
    "pitch": _("Pitc&h"),
    # Translators: The name of a speech setting.
    "rate": _("R&ate"),
    # Translators: The name of a speech setting.
    "inflection": _("In&flection"),
}

TARGET_TYPES = (TargetType.ROLE, TargetType.STATE, TargetType.NEGATIVE_STATE)

SCOPES = (Scope.LABEL, Scope.ELEMENT, Scope.CONTENT)
SCOPE_LABELS = {
    # Translators: What customized speech applies to: only the role or state word.
    Scope.LABEL: _("The label only"),
    # Translators: What customized speech applies to: what NVDA says about the element.
    Scope.ELEMENT: _("The element announcement"),
    # Translators: What customized speech applies to: the announcement and the text inside the element.
    Scope.CONTENT: _("The element and its content"),
}

ELEMENT_PARTS = (
    ElementPart.NAME,
    ElementPart.ROLE,
    ElementPart.VALUE,
    ElementPart.STATES,
    ElementPart.DESCRIPTION,
    ElementPart.OTHER,
)
ELEMENT_PART_LABELS = {
    # Translators: A part of what NVDA says about an element.
    ElementPart.NAME: _("Name"),
    # Translators: A part of what NVDA says about an element.
    ElementPart.ROLE: _("Role"),
    # Translators: A part of what NVDA says about an element.
    ElementPart.VALUE: _("Value"),
    # Translators: A part of what NVDA says about an element.
    ElementPart.STATES: _("States"),
    # Translators: A part of what NVDA says about an element.
    ElementPart.DESCRIPTION: _("Description"),
    # Translators: A part of what NVDA says about an element: position, level, shortcut key and so on.
    ElementPart.OTHER: _("Other properties"),
}

CONTEXTS = (
    ContextGroup.FOCUS,
    ContextGroup.NAVIGATION,
    ContextGroup.SAY_ALL,
    ContextGroup.OBJECT_NAVIGATION,
    ContextGroup.CHANGES,
)
CONTEXT_LABELS = {
    # Translators: A situation in which a rule applies.
    ContextGroup.FOCUS: _("Focus changes"),
    # Translators: A situation in which a rule applies.
    ContextGroup.NAVIGATION: _("Caret and quick navigation"),
    # Translators: A situation in which a rule applies.
    ContextGroup.SAY_ALL: _("Say all"),
    # Translators: A situation in which a rule applies.
    ContextGroup.OBJECT_NAVIGATION: _("Object navigation and mouse"),
    # Translators: A situation in which a rule applies.
    ContextGroup.CHANGES: _("State and value changes"),
}

TEXT_KINDS = (TextKind.PAIR, TextKind.LINE)
TEXT_KIND_LABELS = {
    # Translators: A kind of comment: it has a start and an end, such as /* and */.
    TextKind.PAIR: _("Block comment"),
    # Translators: A kind of comment: it runs to the end of the line, such as // or #.
    TextKind.LINE: _("Line comment"),
}

DELIMITER_SPEECHES = (DelimiterSpeech.CUSTOMIZED, DelimiterSpeech.NORMAL, DelimiterSpeech.HIDDEN)
DELIMITER_SPEECH_LABELS = {
    # Translators: A choice of how the delimiters themselves are spoken.
    DelimiterSpeech.CUSTOMIZED: _("With the customized voice"),
    # Translators: A choice of how the delimiters themselves are spoken.
    DelimiterSpeech.NORMAL: _("With the normal voice"),
    # Translators: A choice of how the delimiters themselves are spoken.
    DelimiterSpeech.HIDDEN: _("Not at all"),
}

SOUND_POSITIONS = (SoundPosition.START, SoundPosition.END, SoundPosition.BOTH)
SOUND_POSITION_LABELS = {
    # Translators: A choice of when the sound of a rule is played.
    SoundPosition.START: _("At the start"),
    # Translators: A choice of when the sound of a rule is played.
    SoundPosition.END: _("At the end"),
    # Translators: A choice of when the sound of a rule is played.
    SoundPosition.BOTH: _("At the start and at the end"),
}

PATTERN_KINDS = (PatternKind.TEXT, PatternKind.WORD, PatternKind.REGEX, PatternKind.EMOJI)
PATTERN_KIND_LABELS = {
    # Translators: A way of matching text: anywhere the text appears.
    PatternKind.TEXT: _("This text, anywhere"),
    # Translators: A way of matching text: the text as a whole word.
    PatternKind.WORD: _("This text, as a whole word"),
    # Translators: A way of matching text: a regular expression.
    PatternKind.REGEX: _("A regular expression"),
    # Translators: A way of matching text: any emoji, such as a smiling face.
    PatternKind.EMOJI: _("Any emoji"),
}

SOUND_TYPES = (SoundType.NONE, SoundType.BEEPS, SoundType.WAVE)
SOUND_TYPE_LABELS = {
    # Translators: A choice of sound.
    SoundType.NONE: _("No sound"),
    # Translators: A choice of sound.
    SoundType.BEEPS: _("Beeps"),
    # Translators: A choice of sound.
    SoundType.WAVE: _("Wave file"),
}


def _describe(what, effects, name=""):
    if not effects:
        # Translators: Part of a rule description: the rule has no effect.
        effects = [_("no effect")]
    done = "; ".join(effects)
    if name and name != what:
        # Translators: How a named rule is shown in the list. {name} is its name, {what} what it
        # matches, and {effects} what it does to it.
        return _("{name}: {what}, {effects}").format(name=name, what=what, effects=done)
    # Translators: How a rule is shown in the list. {what} is what it matches, {effects} what it does.
    return _("{what}, {effects}").format(what=what, effects=done)


def _soundEffect():
    # Translators: Part of a rule description: the rule plays a sound.
    return _("sound")


def _speechEffects(rule):
    effects = []
    speech = describeProfile(rule.profile)
    if speech:
        effects.append(speech)
    if not rule.sound.isSilent:
        effects.append(_soundEffect())
    return effects


def describeElementRule(rule):
    effects = []
    if rule.hideLabel:
        # Translators: Part of a rule description: the role or state word is not spoken.
        effects.append(_("label hidden"))
    if rule.customizesSpeech:
        # Translators: Part of a rule description. {scope} is what the customization applies to.
        effects.append(_("customized speech for {scope}").format(scope=SCOPE_LABELS[rule.scope].lower()))
    if rule.playsSound:
        effects.append(_soundEffect())
    if rule.contexts != ALL_CONTEXTS:
        contexts = ", ".join(CONTEXT_LABELS[context] for context in CONTEXTS if context in rule.contexts)
        # Translators: Part of a rule description. {contexts} lists the situations the rule applies in.
        effects.append(_("only in: {contexts}").format(contexts=contexts))
    return _describe(describeTarget(rule.target), effects)


def describeProfile(profile):
    parts = []
    for setting in SETTINGS:
        param = getattr(profile, setting)
        if param.isUnchanged:
            continue
        value = f"{param.value:+d}" if param.mode == ParamMode.RELATIVE else str(param.value)
        parts.append(f"{SETTING_LABELS[setting].replace('&', '')} {value}")
    if profile.voices:
        # Translators: Part of a rule description: the rule changes the voice.
        parts.append(_("another voice"))
    return ", ".join(parts)


def textRuleMatch(rule):
    if rule.kind == TextKind.LINE:
        # Translators: The delimiter of a line comment rule, such as "# to the end of the line".
        return _("{start} to the end of the line").format(start=rule.start)
    # Translators: The delimiters of a rule, such as ( ).
    return _("{start} {end}").format(start=rule.start, end=rule.end)


def describeTextRule(rule):
    effects = _speechEffects(rule)
    if rule.delimiters == DelimiterSpeech.HIDDEN:
        # Translators: Part of a rule description: the delimiters themselves are not spoken.
        effects.append(_("delimiters not spoken"))
    return _describe(textRuleMatch(rule), effects, rule.name)


def patternRuleMatch(rule):
    if rule.kind == PatternKind.EMOJI:
        return PATTERN_KIND_LABELS[PatternKind.EMOJI]
    # Translators: What a pattern rule matches. {kind} is how it matches, {pattern} what it matches.
    return _("{pattern} ({kind})").format(pattern=rule.pattern, kind=PATTERN_KIND_LABELS[rule.kind].lower())


def describePatternRule(rule):
    effects = []
    if rule.hideText:
        # Translators: Part of a rule description: the matched text is not spoken.
        effects.append(_("not spoken"))
    effects.extend(_speechEffects(rule))
    return _describe(patternRuleMatch(rule), effects, rule.name)


def ruleName(rule, match):
    return rule.name or match


def categoryTitle(category, editing):
    if category == TextCategory.COMMENT:
        # Translators: The title of the dialog to change a comment type.
        # Translators: The title of the dialog to add a comment type.
        return _("Edit comment type") if editing else _("Add comment type")
    # Translators: The title of the dialog to change a pair of delimiters.
    # Translators: The title of the dialog to add a pair of delimiters.
    return _("Edit delimiters") if editing else _("Add delimiters")


__all__ = [
    "TARGET_TYPE_LABELS",
    "describeElementRule",
    "describePatternRule",
    "describeTarget",
    "describeTextRule",
    "patternRuleMatch",
    "ruleName",
    "targetChoices",
    "targetValueLabel",
    "textRuleMatch",
]
