#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synchronise la version projet dans tous les fichiers de release."""

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent

TARGETS = {
    "launcher": ROOT / "launcher.py",
    "updater": ROOT / "auto_updater.py",
    "package": ROOT / "electron-app" / "package.json",
    "installer": ROOT / "installer.nsi",
}


def ensure_version_format(version: str) -> str:
    if not re.fullmatch(r"\d+(?:\.\d+){0,3}", version):
        raise ValueError(
            f"Version invalide '{version}'. Format attendu: X, X.Y, X.Y.Z ou X.Y.Z.W"
        )
    return version


def to_win_version(version: str) -> str:
    parts = version.split(".")
    parts += ["0"] * (4 - len(parts))
    return ".".join(parts[:4])


def replace_regex(content: str, pattern: str, replacement: str, file_label: str) -> str:
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"{file_label}: motif introuvable ou ambigu")
    return new_content


def update_launcher(version: str) -> None:
    path = TARGETS["launcher"]
    content = path.read_text(encoding="utf-8")
    content = replace_regex(
        content,
        r'^VERSION\s*=\s*"[0-9.]+"\s*$',
        f'VERSION = "{version}"',
        "launcher.py",
    )
    path.write_text(content, encoding="utf-8")


def update_updater(version: str) -> None:
    path = TARGETS["updater"]
    content = path.read_text(encoding="utf-8")
    content = replace_regex(
        content,
        r'^CURRENT_VERSION\s*=\s*"[0-9.]+"\s*$',
        f'CURRENT_VERSION = "{version}"',
        "auto_updater.py",
    )
    path.write_text(content, encoding="utf-8")


def update_package(version: str) -> None:
    path = TARGETS["package"]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_installer(version: str) -> None:
    path = TARGETS["installer"]
    content = path.read_text(encoding="utf-8")
    content = replace_regex(
        content,
        r'^!define APP_VERSION "[^"]+"\s*$',
        f'!define APP_VERSION "{version}"',
        "installer.nsi",
    )
    content = replace_regex(
        content,
        r'^!define APP_VERSION_WIN "[^"]+"\s*$',
        f'!define APP_VERSION_WIN "{to_win_version(version)}"',
        "installer.nsi",
    )
    path.write_text(content, encoding="utf-8")


def read_versions() -> dict:
    launcher = TARGETS["launcher"].read_text(encoding="utf-8")
    updater = TARGETS["updater"].read_text(encoding="utf-8")
    installer = TARGETS["installer"].read_text(encoding="utf-8")
    package = json.loads(TARGETS["package"].read_text(encoding="utf-8"))

    launcher_v = re.search(r'^VERSION\s*=\s*"([0-9.]+)"\s*$', launcher, flags=re.MULTILINE)
    updater_v = re.search(r'^CURRENT_VERSION\s*=\s*"([0-9.]+)"\s*$', updater, flags=re.MULTILINE)
    installer_v = re.search(r'^!define APP_VERSION "([^"]+)"\s*$', installer, flags=re.MULTILINE)
    installer_win_v = re.search(r'^!define APP_VERSION_WIN "([^"]+)"\s*$', installer, flags=re.MULTILINE)

    return {
        "launcher.py": launcher_v.group(1) if launcher_v else None,
        "auto_updater.py": updater_v.group(1) if updater_v else None,
        "electron-app/package.json": package.get("version"),
        "installer.nsi": installer_v.group(1) if installer_v else None,
        "installer.nsi (win)": installer_win_v.group(1) if installer_win_v else None,
    }


def check_consistency(expected: str | None = None) -> int:
    versions = read_versions()
    expected_win = to_win_version(expected) if expected else None

    print("Versions détectées:")
    for name, value in versions.items():
        print(f" - {name}: {value}")

    base_values = {
        versions["launcher.py"],
        versions["auto_updater.py"],
        versions["electron-app/package.json"],
        versions["installer.nsi"],
    }

    ok = len(base_values) == 1 and None not in base_values
    if expected:
        ok = ok and versions["launcher.py"] == expected and versions["installer.nsi (win)"] == expected_win

    if ok:
        print("OK: versions cohérentes.")
        return 0

    print("ERREUR: versions incohérentes.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronise les versions de release")
    parser.add_argument("version", nargs="?", help="Version cible (ex: 2.7)")
    parser.add_argument("--check", action="store_true", help="Vérifie seulement la cohérence")
    args = parser.parse_args()

    if args.check and not args.version:
        return check_consistency()

    if not args.version:
        parser.error("version requise sauf avec --check")

    version = ensure_version_format(args.version)

    update_launcher(version)
    update_updater(version)
    update_package(version)
    update_installer(version)

    return check_consistency(expected=version)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERREUR: {exc}")
        raise SystemExit(1)

