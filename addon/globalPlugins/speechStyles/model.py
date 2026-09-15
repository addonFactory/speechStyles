# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses
import logging
import types
import typing
import uuid
from dataclasses import dataclass, field
from enum import Enum, StrEnum

log = logging.getLogger(__name__)

PARAM_MIN = 0
PARAM_MAX = 100
RELATIVE_MIN = -100
RELATIVE_MAX = 100

MIN_FREQUENCY = 50
MAX_FREQUENCY = 5000
MIN_LENGTH = 10
MAX_LENGTH = 5000
MAX_PAUSE = 5000
MAX_VOLUME = 100


def newId():
    return uuid.uuid4().hex


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)


class ParamMode(StrEnum):
    UNCHANGED = "unchanged"
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class SoundType(StrEnum):
    NONE = "none"
    BEEPS = "beeps"
    WAVE = "wave"


class TargetType(StrEnum):
    ROLE = "role"
    STATE = "state"
    NEGATIVE_STATE = "negativeState"


class Scope(StrEnum):
    LABEL = "label"
    ELEMENT = "element"
    CONTENT = "content"


class ElementPart(StrEnum):
    NAME = "name"
    ROLE = "role"
    VALUE = "value"
    STATES = "states"
    DESCRIPTION = "description"
    OTHER = "other"


class ContextGroup(StrEnum):
    FOCUS = "focus"
    NAVIGATION = "navigation"
    SAY_ALL = "sayAll"
    OBJECT_NAVIGATION = "objectNavigation"
    CHANGES = "changes"


class TextCategory(StrEnum):
    ENCLOSED = "enclosed"
    COMMENT = "comment"


class TextKind(StrEnum):
    PAIR = "pair"
    LINE = "line"


class DelimiterSpeech(StrEnum):
    CUSTOMIZED = "customized"
    NORMAL = "normal"
    HIDDEN = "hidden"


class SoundPosition(StrEnum):
    START = "start"
    END = "end"
    BOTH = "both"


class PatternKind(StrEnum):
    TEXT = "text"
    WORD = "word"
    REGEX = "regex"
    EMOJI = "emoji"


class ImportMode(StrEnum):
    REPLACE = "replace"
    MERGE = "merge"


def _clampedInt(minimum, maximum, default):
    return field(default=default, metadata={"range": (minimum, maximum)})


class _Model:
    def __post_init__(self):
        for f in dataclasses.fields(self):
            bounds = f.metadata.get("range")
            if bounds is not None:
                object.__setattr__(self, f.name, clamp(getattr(self, f.name), *bounds))


@dataclass(frozen=True)
class ParamSetting(_Model):
    mode: ParamMode = ParamMode.UNCHANGED
    value: int = 0

    def __post_init__(self):
        if self.mode == ParamMode.RELATIVE:
            object.__setattr__(self, "value", clamp(self.value, RELATIVE_MIN, RELATIVE_MAX))
        else:
            object.__setattr__(self, "value", clamp(self.value, PARAM_MIN, PARAM_MAX))

    @property
    def isUnchanged(self):
        return self.mode == ParamMode.UNCHANGED

    def resolve(self, default):
        if self.mode == ParamMode.ABSOLUTE:
            return self.value
        if self.mode == ParamMode.RELATIVE:
            return clamp(default + self.value, PARAM_MIN, PARAM_MAX)
        return None


UNCHANGED = ParamSetting()


@dataclass(frozen=True)
class VoiceProfile(_Model):
    volume: ParamSetting = UNCHANGED
    pitch: ParamSetting = UNCHANGED
    rate: ParamSetting = UNCHANGED
    inflection: ParamSetting = UNCHANGED
    voices: dict[str, str] = field(default_factory=dict, hash=False)

    @property
    def isEmpty(self):
        return not self.voices and all(
            getattr(self, name).isUnchanged for name in ("volume", "pitch", "rate", "inflection")
        )

    def voiceFor(self, synthName):
        return self.voices.get(synthName) or None

    def withVoice(self, synthName, voiceId):
        voices = dict(self.voices)
        if voiceId:
            voices[synthName] = voiceId
        else:
            voices.pop(synthName, None)
        return dataclasses.replace(self, voices=voices)


@dataclass(frozen=True)
class BeepStep(_Model):
    frequency: int = _clampedInt(MIN_FREQUENCY, MAX_FREQUENCY, 440)
    length: int = _clampedInt(MIN_LENGTH, MAX_LENGTH, 40)
    leftVolume: int = _clampedInt(0, MAX_VOLUME, 50)
    rightVolume: int = _clampedInt(0, MAX_VOLUME, 50)
    pause: int = _clampedInt(0, MAX_PAUSE, 0)


def pannedSteps(steps, position):
    if position is None:
        return steps
    position = min(max(position, 0.0), 1.0)
    result = []
    for step in steps:
        volume = max(step.leftVolume, step.rightVolume)
        result.append(
            dataclasses.replace(
                step,
                leftVolume=round(volume * (1 - position)),
                rightVolume=round(volume * position),
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class Sound(_Model):
    type: SoundType = SoundType.NONE
    beeps: tuple[BeepStep, ...] = (BeepStep(),)
    panByPosition: bool = False
    waveFile: str = ""
    waveVolume: int = _clampedInt(0, MAX_VOLUME, 100)

    @property
    def isSilent(self):
        if self.type == SoundType.BEEPS:
            return not self.beeps
        if self.type == SoundType.WAVE:
            return not self.waveFile
        return True


@dataclass(frozen=True)
class RuleTarget(_Model):
    type: TargetType = TargetType.ROLE
    value: str = ""


ALL_CONTEXTS = frozenset(ContextGroup)
ALL_PARTS = frozenset(ElementPart)


@dataclass(frozen=True)
class ElementRule(_Model):
    target: RuleTarget = RuleTarget()
    contexts: frozenset[ContextGroup] = ALL_CONTEXTS
    hideLabel: bool = False
    customizeSpeech: bool = False
    scope: Scope = Scope.LABEL
    elementParts: frozenset[ElementPart] = ALL_PARTS
    profile: VoiceProfile = VoiceProfile()
    playSound: bool = False
    sound: Sound = Sound()
    applyToExit: bool = True
    enabled: bool = True
    id: str = field(default_factory=newId)

    @property
    def customizesSpeech(self):
        return self.customizeSpeech and not self.profile.isEmpty

    @property
    def playsSound(self):
        return self.playSound and not self.sound.isSilent

    @property
    def hasEffect(self):
        return bool(self.contexts) and (self.hideLabel or self.customizesSpeech or self.playsSound)


@dataclass(frozen=True)
class TextRule(_Model):
    category: TextCategory = TextCategory.ENCLOSED
    name: str = ""
    kind: TextKind = TextKind.PAIR
    start: str = ""
    end: str = ""
    requireBoundary: bool = False
    lineStartOnly: bool = False
    allowUnclosed: bool = False
    delimiters: DelimiterSpeech = DelimiterSpeech.CUSTOMIZED
    profile: VoiceProfile = VoiceProfile()
    sound: Sound = Sound()
    soundPosition: SoundPosition = SoundPosition.START
    enabled: bool = True
    id: str = field(default_factory=newId)

    def __post_init__(self):
        super().__post_init__()
        if self.category == TextCategory.ENCLOSED and self.kind != TextKind.PAIR:
            object.__setattr__(self, "kind", TextKind.PAIR)

    @property
    def isSymmetric(self):
        return self.kind == TextKind.PAIR and self.start == self.end

    @property
    def isValid(self):
        return bool(self.start) and (self.kind == TextKind.LINE or bool(self.end))

    @property
    def hasEffect(self):
        return (
            not self.profile.isEmpty or not self.sound.isSilent or self.delimiters == DelimiterSpeech.HIDDEN
        )


@dataclass(frozen=True)
class PatternRule(_Model):
    name: str = ""
    kind: PatternKind = PatternKind.TEXT
    pattern: str = ""
    caseSensitive: bool = False
    hideText: bool = False
    profile: VoiceProfile = VoiceProfile()
    sound: Sound = Sound()
    soundPosition: SoundPosition = SoundPosition.START
    enabled: bool = True
    id: str = field(default_factory=newId)

    @property
    def needsPattern(self):
        return self.kind != PatternKind.EMOJI

    @property
    def isValid(self):
        return bool(self.pattern) or not self.needsPattern

    @property
    def hasEffect(self):
        return self.hideText or not self.profile.isEmpty or not self.sound.isSilent


FORMAT_VERSION = 1


@dataclass(frozen=True)
class RulesDocument(_Model):
    version: int = FORMAT_VERSION
    elementRules: tuple[ElementRule, ...] = ()
    textRules: tuple[TextRule, ...] = ()
    patternRules: tuple[PatternRule, ...] = ()

    def textRulesOf(self, category):
        return tuple(rule for rule in self.textRules if rule.category == category)


def toDict(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: toDict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (set, frozenset)):
        return sorted(toDict(item) for item in obj)
    if isinstance(obj, (list, tuple)):
        return [toDict(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): toDict(value) for key, value in obj.items()}
    return obj


class _Invalid(Exception):
    pass


_T = typing.TypeVar("_T")


def fromDict(cls, data):
    if not isinstance(data, dict):
        log.warning(f"Expected an object for {cls.__name__}, got {data!r}; using defaults")
        return cls()
    hints = typing.get_type_hints(cls)
    values = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        try:
            values[f.name] = _convert(hints[f.name], data[f.name], f"{cls.__name__}.{f.name}")
        except _Invalid as e:
            log.warning(f"{e}; using the default")
    return cls(**values)


def _convert(tp, value, where):
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if tp is bool:
        if isinstance(value, bool):
            return value
    elif tp is int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    elif tp is str:
        if isinstance(value, str):
            return value
    elif isinstance(tp, type) and issubclass(tp, Enum):
        try:
            return tp(value)
        except ValueError:
            pass
    elif isinstance(tp, type) and dataclasses.is_dataclass(tp):
        if isinstance(value, dict):
            return fromDict(tp, value)
    elif origin in (tuple, frozenset) and isinstance(value, list):
        itemType = args[0]
        items = []
        for index, item in enumerate(value):
            try:
                items.append(_convert(itemType, item, f"{where}[{index}]"))
            except _Invalid as e:
                log.warning(f"{e}; skipping it")
        return origin(items)
    elif origin is dict and isinstance(value, dict):
        keyType, valueType = args
        return {
            _convert(keyType, key, f"{where} key"): _convert(valueType, item, f"{where}[{key!r}]")
            for key, item in value.items()
        }
    elif origin in (types.UnionType, typing.Union):
        for option in args:
            try:
                return _convert(option, value, where)
            except _Invalid:
                continue
    raise _Invalid(f"Invalid value {value!r} for {where}")
