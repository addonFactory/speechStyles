# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import itertools
from dataclasses import dataclass

from speech.commands import (
    BaseProsodyCommand,
    CharacterModeCommand,
    EndUtteranceCommand,
    PitchCommand,
    RateCommand,
    VolumeCommand,
)

from .markers import ScopeEnd, ScopeStart, SoundCommand, TaggedText, VoiceStateCommand
from .model import (
    DelimiterSpeech,
    ElementPart,
    SoundPosition,
    VoiceProfile,
)
from .patterns import findMatches
from .profiles import EMPTY_PROFILE, PROSODY_SETTINGS, merge, voiceStateFor
from .spanParser import findSpans

PROSODY_COMMANDS = {"pitch": PitchCommand, "volume": VolumeCommand, "rate": RateCommand}

ITEM_SEPARATOR = " "


@dataclass(frozen=True, slots=True)
class _Layer:
    key: str
    profile: VoiceProfile
    parts: frozenset[ElementPart] | None = None

    def appliesTo(self, text):
        if self.parts is None or not isinstance(text, TaggedText):
            return True
        return text.part in self.parts


@dataclass(slots=True)
class _Text:
    text: str
    layers: tuple[_Layer, ...]
    scannable: bool
    labelLayers: tuple[_Layer, ...] = ()

    @property
    def allLayers(self):
        return self.layers + self.labelLayers


@dataclass(slots=True)
class _Command:
    command: object


def contextMatches(rule, context):
    return context is None or context in rule.contexts


def needsTransform(sequence, ruleSet):
    if ruleSet.hasSpanRules:
        return True
    checkLabels = ruleSet.hasElementRules
    return any(
        isinstance(item, (ScopeStart, ScopeEnd))
        or (checkLabels and isinstance(item, TaggedText) and item.target is not None)
        for item in sequence
    )


def transform(sequence, ruleSet, getSynth):
    if not needsTransform(sequence, ruleSet):
        return sequence
    units = _buildUnits(sequence, ruleSet)
    if ruleSet.hasSpanRules:
        units = _applyTextRules(units, ruleSet)
    return _emit(units, getSynth())


def stripMarkers(sequence):
    return [item for item in sequence if not isinstance(item, (ScopeStart, ScopeEnd))]


def takeSoundsWithoutSpeech(sequence):
    if any(isinstance(item, str) and item.strip() for item in sequence):
        return sequence, []
    sounds = [item for item in sequence if isinstance(item, SoundCommand)]
    if not sounds:
        return sequence, []
    return [item for item in sequence if not isinstance(item, SoundCommand)], sounds


def _buildUnits(sequence, ruleSet):
    stack = []
    units = []
    characterMode = False
    for item in sequence:
        if isinstance(item, ScopeStart):
            rule = ruleSet.ruleById(item.ruleId)
            if rule is not None:
                profile = rule.profile if rule.customizesSpeech else EMPTY_PROFILE
                stack.append(_Layer(rule.id, profile, rule.elementParts))
                if rule.playsSound:
                    units.append(_Command(SoundCommand(rule.sound, item.position)))
        elif isinstance(item, ScopeEnd):
            for index in range(len(stack) - 1, -1, -1):
                if stack[index].key == item.ruleId:
                    del stack[index]
                    break
        elif isinstance(item, TaggedText) and item.target is not None:
            _addLabel(item, stack, units, ruleSet)
        elif isinstance(item, str):
            units.append(_Text(item, tuple(stack), not characterMode))
        else:
            if isinstance(item, CharacterModeCommand):
                characterMode = item.state
            units.append(_Command(item))
    return units


def _addLabel(label, stack, units, ruleSet):
    rules = [
        rule
        for rule in ruleSet.rulesFor(*label.target)
        if contextMatches(rule, label.context) and (rule.applyToExit or not label.isExit)
    ]
    inScope = {layer.key for layer in stack}
    for rule in rules:
        if rule.playsSound and (label.isExit or rule.id not in inScope):
            units.append(_Command(SoundCommand(rule.sound, label.position)))
    if any(rule.hideLabel for rule in rules):
        return
    labelLayers = tuple(
        _Layer(rule.id, rule.profile) for rule in rules if rule.customizesSpeech and rule.id not in inScope
    )
    units.append(_Text(label, tuple(stack), False, labelLayers))


def _applyTextRules(units, ruleSet):
    offsets = {}
    opaqueOffsets = {}
    parts = []
    length = 0
    for index, unit in enumerate(units):
        if not isinstance(unit, _Text):
            continue
        if parts:
            parts.append(ITEM_SEPARATOR)
            length += len(ITEM_SEPARATOR)
        if unit.scannable:
            offsets[index] = length
            parts.append(unit.text)
            length += len(unit.text)
        else:
            opaqueOffsets[index] = length
            parts.append(ITEM_SEPARATOR)
            length += len(ITEM_SEPARATOR)
    if not offsets:
        return units
    flags = ruleSet.flags
    joined = "".join(parts)
    spans = findSpans(joined, ruleSet.textRules, flags.allowNesting, flags.enclosedInComments)
    spans = sorted(
        spans + findMatches(joined, ruleSet.patternRules), key=lambda span: (span.start, -span.end)
    )
    if not spans:
        return units
    result = []
    endSounds = set()
    for index, unit in enumerate(units):
        if index in offsets:
            result.extend(_splitUnit(unit, offsets[index], spans, endSounds))
        elif index in opaqueOffsets:
            result.append(_inSpans(unit, opaqueOffsets[index], spans))
        else:
            result.append(unit)
    for spanIndex, span in enumerate(spans):
        if spanIndex not in endSounds and _playsAt(span, SoundPosition.END):
            result.append(_Command(SoundCommand(span.rule.sound)))
    return result


def _playsAt(span, position):
    return not span.rule.sound.isSilent and span.rule.soundPosition in (position, SoundPosition.BOTH)


def _inSpans(unit, offset, spans):
    layers = tuple(
        _Layer(span.rule.id, span.rule.profile)
        for span in spans
        if span.contentStart <= offset < span.contentEnd
    )
    if not layers:
        return unit
    return _Text(unit.text, unit.layers + layers, unit.scannable, unit.labelLayers)


def _splitUnit(unit, start, spans, endSounds):
    end = start + len(unit.text)
    relevant = [(index, span) for index, span in enumerate(spans) if span.start < end and span.end > start]
    if not relevant:
        return [unit]
    boundaries = {start, end}
    for _, span in relevant:
        for boundary in (span.start, span.contentStart, span.contentEnd, span.end):
            if start < boundary < end:
                boundaries.add(boundary)
    ordered = sorted(boundaries)
    pieces = []
    for pieceStart, pieceEnd in itertools.pairwise(ordered):
        for _, span in relevant:
            if span.start == pieceStart and _playsAt(span, SoundPosition.START):
                pieces.append(_Command(SoundCommand(span.rule.sound)))
        layers = []
        hidden = False
        for _, span in relevant:
            if not (span.start <= pieceStart and pieceEnd <= span.end):
                continue
            if span.hidden:
                hidden = True
                break
            if pieceStart < span.contentStart or pieceStart >= span.contentEnd:
                if span.delimiters == DelimiterSpeech.HIDDEN:
                    hidden = True
                    break
                if span.delimiters == DelimiterSpeech.NORMAL:
                    continue
            layers.append(_Layer(span.rule.id, span.rule.profile))
        if not hidden:
            text = unit.text[pieceStart - start : pieceEnd - start]
            if isinstance(unit.text, TaggedText):
                text = unit.text.withText(text)
            piece = _Text(text, unit.layers + tuple(layers), True, unit.labelLayers)
            if pieces and isinstance(pieces[-1], _Text) and pieces[-1].layers == piece.layers:
                previous = pieces[-1]
                joined = str(previous.text) + str(piece.text)
                if isinstance(previous.text, TaggedText):
                    joined = previous.text.withText(joined)
                pieces[-1] = _Text(joined, previous.layers, True, previous.labelLayers)
            else:
                pieces.append(piece)
        for spanIndex, span in relevant:
            if span.end == pieceEnd and spanIndex not in endSounds and _playsAt(span, SoundPosition.END):
                endSounds.add(spanIndex)
                pieces.append(_Command(SoundCommand(span.rule.sound)))
    return pieces


def _emit(units, synth):
    out = []
    base = dict.fromkeys(PROSODY_SETTINGS)
    emitted = dict(base)
    voice = None
    spokenInUtterance = False
    for unit in units:
        if isinstance(unit, _Command):
            command = unit.command
            if isinstance(command, BaseProsodyCommand) and command.settingName in base:
                base[command.settingName] = None if command.isDefault else command
                continue
            if isinstance(command, EndUtteranceCommand):
                voice = None
                spokenInUtterance = False
            out.append(command)
            continue
        text = unit.text
        if not text.strip():
            out.append(text)
            continue
        profile = merge(layer.profile for layer in unit.allLayers if layer.appliesTo(text))
        state = voiceStateFor(profile, synth)
        if state != voice:
            if spokenInUtterance:
                out.append(EndUtteranceCommand())
                spokenInUtterance = False
            if state is not None:
                out.append(VoiceStateCommand(state))
            voice = state
        for setting, commandClass in PROSODY_COMMANDS.items():
            desired = _desiredProsody(setting, profile, base[setting], synth, commandClass)
            if desired != emitted[setting]:
                out.append(desired if desired is not None else commandClass())
                emitted[setting] = desired
        out.append(text)
        spokenInUtterance = True
    for setting, commandClass in PROSODY_COMMANDS.items():
        if emitted[setting] != base[setting]:
            out.append(base[setting] if base[setting] is not None else commandClass())
    return out


def _desiredProsody(setting, profile, baseCommand, synth, commandClass):
    default = synth.defaults.get(setting)
    if default is None:
        return baseCommand
    target = getattr(profile, setting).resolve(default)
    if target is None:
        return baseCommand
    if target == default:
        return None
    return commandClass(offset=target - default)
