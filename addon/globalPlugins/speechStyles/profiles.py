# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses
from dataclasses import dataclass, field

from .model import ParamSetting, VoiceProfile

PROSODY_SETTINGS = ("volume", "pitch", "rate")
SYNTH_SETTINGS = ("inflection",)
SETTINGS = PROSODY_SETTINGS + SYNTH_SETTINGS

EMPTY_PROFILE = VoiceProfile()


def merge(profiles):
    result = None
    for profile in profiles:
        if result is None:
            result = profile
            continue
        if profile.isEmpty:
            continue
        changes = {
            name: getattr(profile, name) for name in SETTINGS if not getattr(profile, name).isUnchanged
        }
        if profile.voices:
            changes["voices"] = {**result.voices, **profile.voices}
        result = dataclasses.replace(result, **changes)
    return result if result is not None else EMPTY_PROFILE


@dataclass(frozen=True)
class SynthContext:
    name: str = ""
    defaults: dict[str, int] = field(default_factory=dict, hash=False)
    supportsVoice: bool = False


@dataclass(frozen=True)
class VoiceState:
    voice: str | None = None
    inflection: ParamSetting | None = None


def voiceStateFor(profile, synth):
    voice = profile.voiceFor(synth.name) if synth.supportsVoice else None
    inflection = None
    if not profile.inflection.isUnchanged and "inflection" in synth.defaults:
        inflection = profile.inflection
    if voice is None and inflection is None:
        return None
    return VoiceState(voice, inflection)
