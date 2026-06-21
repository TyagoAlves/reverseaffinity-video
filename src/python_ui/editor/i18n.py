import os
import json
from PyQt5.QtCore import QObject, pyqtSignal


LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale")

RTL_LANGUAGES = {"ar", "he", "fa", "ur", "yi"}


class Translator(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.translations: dict[str, dict[str, str]] = {}
        self.current_lang = self._init_lang_from_settings()
        self._load_translations(self.current_lang)

    def _init_lang_from_settings(self) -> str:
        from PyQt5.QtCore import QStandardPaths
        config_dir = QStandardPaths.writableLocation(QStandardPaths.ConfigLocation)
        settings_path = os.path.join(config_dir, 'reverseaffinity', 'settings.json')
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                saved = data.get('language', '')
                if saved and saved != 'system':
                    return saved
        except Exception:
            pass
        return "pt_BR"

    def _load_translations(self, lang_code: str):
        path = os.path.join(LOCALE_DIR, f"{lang_code}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {}
            for module_dict in data.values():
                merged.update(module_dict)
            self.translations[lang_code] = merged
        else:
            self.translations[lang_code] = {}

    def translate(self, msgid: str) -> str:
        if msgid in self.translations.get(self.current_lang, {}):
            return self.translations[self.current_lang][msgid]
        if "en_US" in self.translations and msgid in self.translations["en_US"]:
            return self.translations["en_US"][msgid]
        return msgid

    def available_languages(self) -> list[tuple[str, str]]:
        if not os.path.isdir(LOCALE_DIR):
            return [("pt_BR", "Português (Brasil)")]
        langs = []
        for fn in sorted(os.listdir(LOCALE_DIR)):
            if fn.endswith(".json"):
                code = fn[:-5]
                names = {
                    "pt_BR": "Português (Brasil)",
                    "en_US": "English (US)",
                    "es_ES": "Español",
                    "fr_FR": "Français",
                    "de_DE": "Deutsch",
                    "it_IT": "Italiano",
                    "ja_JP": "日本語",
                }
                langs.append((code, names.get(code, code)))
        return langs if langs else [("pt_BR", "Português (Brasil)")]

    def set_language(self, lang_code: str):
        if lang_code not in self.translations:
            self._load_translations(lang_code)
        self.current_lang = lang_code
        self.language_changed.emit(lang_code)

    def is_rtl(self) -> bool:
        parts = self.current_lang.split("_")
        if parts:
            lang = parts[0].lower()
            return lang in RTL_LANGUAGES
        return False

    def reload_all(self):
        self._load_translations(self.current_lang)


_translator = Translator()


def _(msgid: str) -> str:
    return _translator.translate(msgid)


def get_translator() -> Translator:
    return _translator
