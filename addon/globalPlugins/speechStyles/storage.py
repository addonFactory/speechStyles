# Copyright (C) 2026 Beka Gozalishvili <beqaprogger@gmail.com>
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

import dataclasses
import json
import logging
import os
import zipfile

from .model import (
    FORMAT_VERSION,
    ImportMode,
    ParamMode,
    ParamSetting,
    PatternKind,
    PatternRule,
    RulesDocument,
    TextCategory,
    TextKind,
    TextRule,
    VoiceProfile,
    fromDict,
    newId,
    toDict,
)

log = logging.getLogger(__name__)

RULES_FILE_NAME = "rules.json"
SOUNDS_FOLDER_NAME = "sounds"
ARCHIVE_SOUNDS_PREFIX = f"{SOUNDS_FOLDER_NAME}/"
MAX_ARCHIVE_SIZE = 64 * 1024 * 1024

CONFIG_SECTION = "speechStyles"
CONFIG_SPEC = {
    "enabled": "boolean(default=True)",
    "elementRules": "boolean(default=True)",
    "enclosedText": "boolean(default=False)",
    "comments": "boolean(default=False)",
    "patterns": "boolean(default=False)",
    "allowNesting": "boolean(default=True)",
    "enclosedInComments": "boolean(default=False)",
}


class StorageError(Exception):
    pass


def _identity(text):
    return text


def _pitch(value):
    return VoiceProfile(pitch=ParamSetting(ParamMode.RELATIVE, value))


def defaultTextRules(_=_identity):
    pass

    def enclosed(name, start, end, profile, requireBoundary=False):
        return TextRule(
            category=TextCategory.ENCLOSED,
            name=name,
            start=start,
            end=end,
            requireBoundary=requireBoundary,
            profile=profile,
            enabled=False,
        )

    def lineComment(name, start, enabled):
        return TextRule(
            category=TextCategory.COMMENT,
            name=name,
            kind=TextKind.LINE,
            start=start,
            requireBoundary=True,
            profile=_pitch(-20),
            enabled=enabled,
        )

    def blockComment(name, start, end, enabled):
        return TextRule(
            category=TextCategory.COMMENT,
            name=name,
            start=start,
            end=end,
            allowUnclosed=True,
            profile=_pitch(-20),
            enabled=enabled,
        )

    quotes = _pitch(15)
    singleQuotes = _pitch(10)
    return (
        # Translators: Name of a default delimiter pair: "text".
        enclosed(_("Double quotes"), '"', '"', quotes, requireBoundary=True),
        # Translators: Name of a default delimiter pair: “text”.
        enclosed(_("Typographic double quotes"), "“", "”", quotes),
        # Translators: Name of a default delimiter pair: „text“.
        enclosed(_("Low double quotes"), "„", "“", quotes),
        # Translators: Name of a default delimiter pair: «text».
        enclosed(_("Guillemets"), "«", "»", quotes),
        # Translators: Name of a default delimiter pair: 'text'.
        enclosed(_("Single quotes"), "'", "'", singleQuotes, requireBoundary=True),
        # Translators: Name of a default delimiter pair: text in typographic single quotes.
        enclosed(_("Typographic single quotes"), "\u2018", "\u2019", singleQuotes, requireBoundary=True),
        # Translators: Name of a default delimiter pair: (text).
        enclosed(_("Parentheses"), "(", ")", _pitch(-15)),
        # Translators: Name of a default delimiter pair: [text].
        enclosed(
            _("Square brackets"),
            "[",
            "]",
            VoiceProfile(
                pitch=ParamSetting(ParamMode.RELATIVE, -10),
                volume=ParamSetting(ParamMode.RELATIVE, -10),
            ),
        ),
        # Translators: Name of a default delimiter pair: {text}.
        enclosed(_("Braces"), "{", "}", _pitch(-20)),
        # Translators: Name of a default delimiter pair: <text>.
        enclosed(_("Angle brackets"), "<", ">", _pitch(-10)),
        # Translators: Name of a default comment type, as in C, Java or JavaScript.
        lineComment(_("Line comment (//)"), "//", True),
        # Translators: Name of a default comment type, as in Python or shell scripts.
        lineComment(_("Line comment (#)"), "#", True),
        # Translators: Name of a default comment type, as in SQL or Lua.
        lineComment(_("Line comment (--)"), "--", False),
        # Translators: Name of a default comment type, as in assembly or INI files.
        lineComment(_("Line comment (;)"), ";", False),
        # Translators: Name of a default comment type, as in C, CSS or JavaScript.
        blockComment(_("Block comment (/* */)"), "/*", "*/", True),
        # Translators: Name of a default comment type, as in HTML or XML.
        blockComment(_("Markup comment (<!-- -->)"), "<!--", "-->", True),
        # Translators: Name of a default comment type: a Python docstring in double quotes.
        blockComment(_('Docstring ("""…""")'), '"""', '"""', False),
        # Translators: Name of a default comment type: a Python docstring in single quotes.
        blockComment(_("Docstring ('''…''')"), "'''", "'''", False),
    )


def defaultPatternRules(_=_identity):
    return (
        PatternRule(
            # Translators: The name of a default pattern, matching emoji such as 😀.
            name=_("Emoji"),
            kind=PatternKind.EMOJI,
            profile=VoiceProfile(
                pitch=ParamSetting(ParamMode.RELATIVE, -20),
                volume=ParamSetting(ParamMode.RELATIVE, -20),
            ),
            enabled=False,
        ),
    )


def defaultDocument(_=_identity):
    return RulesDocument(textRules=defaultTextRules(_), patternRules=defaultPatternRules(_))


def documentToData(document):
    return toDict(dataclasses.replace(document, version=FORMAT_VERSION))


def documentFromData(data, _=_identity):
    document = fromDict(RulesDocument, data)
    if document.version > FORMAT_VERSION:
        log.warning(
            f"Rules were saved by a newer version of the add-on (format {document.version}); "
            "unknown settings are ignored"
        )
    if isinstance(data, dict) and "textRules" not in data:
        document = dataclasses.replace(document, textRules=defaultTextRules(_))
    if isinstance(data, dict) and "patternRules" not in data:
        document = dataclasses.replace(document, patternRules=defaultPatternRules(_))
    return withUniqueIds(document)


RULE_LISTS = ("elementRules", "textRules", "patternRules")


def allRules(document):
    return tuple(rule for name in RULE_LISTS for rule in getattr(document, name))


def mapRules(document, change):
    return dataclasses.replace(
        document,
        **{name: tuple(change(rule) for rule in getattr(document, name)) for name in RULE_LISTS},
    )


def withUniqueIds(document, regenerate=False):
    seen = set()

    def unique(rule):
        if regenerate or rule.id in seen or not rule.id:
            rule = dataclasses.replace(rule, id=newId())
        seen.add(rule.id)
        return rule

    return mapRules(document, unique)


def isValidSoundName(name):
    return (
        bool(name)
        and name == os.path.basename(name)
        and "/" not in name
        and "\\" not in name
        and not name.startswith(".")
    )


def referencedSounds(document):
    return {rule.sound.waveFile for rule in allRules(document) if rule.sound.waveFile}


def renameSounds(document, names):
    def rename(rule):
        if rule.sound.waveFile not in names:
            return rule
        return dataclasses.replace(
            rule, sound=dataclasses.replace(rule.sound, waveFile=names[rule.sound.waveFile])
        )

    return mapRules(document, rename)


class RulesStore:
    def __init__(self, folder, translate=_identity):
        self.folder = folder
        self.translate = translate

    @property
    def rulesPath(self):
        return os.path.join(self.folder, RULES_FILE_NAME)

    @property
    def soundsFolder(self):
        return os.path.join(self.folder, SOUNDS_FOLDER_NAME)

    def load(self):
        path = self.rulesPath
        if not os.path.isfile(path):
            return defaultDocument(self.translate)
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            log.error(f"Could not read {path}; using default rules", exc_info=True)
            self._setAside(path)
            return defaultDocument(self.translate)
        return documentFromData(data, self.translate)

    def _setAside(self, path):
        try:
            os.replace(path, f"{path}.bad")
        except OSError:
            log.error(f"Could not rename the unreadable file {path}", exc_info=True)

    def save(self, document):
        os.makedirs(self.folder, exist_ok=True)
        path = self.rulesPath
        temporaryPath = f"{path}.tmp"
        with open(temporaryPath, "w", encoding="utf-8") as file:
            json.dump(documentToData(document), file, ensure_ascii=False, indent="\t")
        os.replace(temporaryPath, path)
        self.removeUnusedSounds(document)

    def soundPath(self, name):
        if not isValidSoundName(name):
            return None
        path = os.path.join(self.soundsFolder, name)
        return path if os.path.isfile(path) else None

    def addSound(self, sourcePath):
        try:
            with open(sourcePath, "rb") as file:
                content = file.read()
        except OSError as e:
            raise StorageError(f"Cannot read {sourcePath}") from e
        return self._storeSound(os.path.basename(sourcePath), content)

    def _storeSound(self, name, content):
        if not isValidSoundName(name):
            name = "sound.wav"
        os.makedirs(self.soundsFolder, exist_ok=True)
        stem, extension = os.path.splitext(name)
        candidate = name
        number = 1
        while True:
            path = os.path.join(self.soundsFolder, candidate)
            if not os.path.exists(path):
                with open(path, "wb") as file:
                    file.write(content)
                return candidate
            if os.path.isfile(path) and _readBytes(path) == content:
                return candidate
            number += 1
            candidate = f"{stem}-{number}{extension}"

    def removeUnusedSounds(self, document):
        folder = self.soundsFolder
        if not os.path.isdir(folder):
            return
        used = referencedSounds(document)
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if name not in used and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    log.warning(f"Could not remove the unused sound {path}", exc_info=True)

    def exportArchive(self, document, path):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                RULES_FILE_NAME,
                json.dumps(documentToData(document), ensure_ascii=False, indent="\t"),
            )
            for name in sorted(referencedSounds(document)):
                soundPath = self.soundPath(name)
                if soundPath is None:
                    log.warning(f"The sound {name!r} is missing and is not exported")
                    continue
                archive.write(soundPath, ARCHIVE_SOUNDS_PREFIX + name)

    def importArchive(self, path, current, mode):
        data, sounds = _readArchive(path)
        imported = documentFromData(data, self.translate)
        names = {}
        for name in referencedSounds(imported):
            if name in sounds:
                names[name] = self._storeSound(name, sounds[name])
            elif self.soundPath(name) is None:
                log.warning(f"The imported sound {name!r} is not in the archive")
        imported = renameSounds(imported, names)
        if mode == ImportMode.REPLACE:
            return imported
        imported = withUniqueIds(imported, regenerate=True)
        return dataclasses.replace(
            current,
            **{name: getattr(current, name) + getattr(imported, name) for name in RULE_LISTS},
        )


def _readBytes(path):
    with open(path, "rb") as file:
        return file.read()


def _readArchive(path):
    try:
        with zipfile.ZipFile(path) as archive:
            members = {info.filename: info for info in archive.infolist() if not info.is_dir()}
            if RULES_FILE_NAME not in members:
                raise StorageError(f"{path} does not contain {RULES_FILE_NAME}")
            if sum(info.file_size for info in members.values()) > MAX_ARCHIVE_SIZE:
                raise StorageError(f"{path} is too large")
            data = json.loads(archive.read(RULES_FILE_NAME).decode("utf-8"))
            sounds = {}
            for filename in members:
                if not filename.startswith(ARCHIVE_SOUNDS_PREFIX):
                    continue
                name = filename[len(ARCHIVE_SOUNDS_PREFIX) :]
                if isValidSoundName(name):
                    sounds[name] = archive.read(filename)
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        raise StorageError(f"Cannot read {path}") from e
    if not isinstance(data, dict):
        raise StorageError(f"{path} does not contain rules")
    return data, sounds
