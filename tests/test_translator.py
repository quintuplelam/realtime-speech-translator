import argostranslate.package
import argostranslate.translate
from src.api.translator import Translator

def test_translator_initializes():
    t = Translator()
    assert t is not None

def test_translate_english_to_chinese():
    # Install package first if not installed
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    pkg = next((p for p in packages if p.from_code == "en" and p.to_code == "zh"), None)
    if pkg:
        argostranslate.package.install_from_path(pkg.download())

    t = Translator()
    result = t.translate("Hello", "en", "zh")
    assert result is not None
    assert len(result) > 0