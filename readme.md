# Speech Styles

**Speech Styles** is an NVDA add-on that lets you customize how NVDA speaks different kinds of text and UI elements.

The idea is inspired by **Emacspeak**, bringing voice styling to NVDA so information can be distinguished by sound instead of extra words.

## Features

* Customize **roles and states** (buttons, links, checked, selected, etc.).
* Style **text inside quotes, parentheses, brackets, braces**, and other delimiters.
* Style **source code comments** (`//`, `#`, `/* */`, `<!-- -->`, and more).
* Match **custom text patterns or emojis** using plain text or regular expressions.
* Change **voice, pitch, rate, volume, inflection**, or play **sounds** for any rule.

Rules can be enabled or disabled independently and work with NVDA configuration profiles.

## Requirements

* NVDA **2025.1** or later.

## Development

```console
uv sync
uv run ruff check addon
uv run nvaddon build
```

## Translating

Translations are welcome.

```console
nvaddon locale-add <language code>
```

Then translate `addon/locale/<language code>/LC_MESSAGES/nvda.po` and open a pull request.

## License

GPL v2. See `COPYING.txt` for details.
