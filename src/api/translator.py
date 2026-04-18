import argostranslate.package
import argostranslate.translate
from typing import Optional

class Translator:
    def __init__(self):
        self._ensure_package_installed()

    def _ensure_package_installed(self, from_code="en", to_code="zh"):
        packages = argostranslate.package.get_available_packages()
        installed = {p.from_code + "_" + p.to_code for p in argostranslate.package.get_installed_packages()}
        target = f"{from_code}_{to_code}"

        if target not in installed:
            pkg = next((p for p in packages if p.from_code == from_code and p.to_code == to_code), None)
            if pkg:
                argostranslate.package.install_from_path(pkg.download())

    def translate(self, text: str, from_code: str = "en", to_code: str = "zh") -> Optional[str]:
        self._ensure_package_installed(from_code, to_code)
        try:
            return argostranslate.translate.translate(text, from_code, to_code)
        except Exception:
            return None