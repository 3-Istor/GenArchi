#!/usr/bin/env python3
"""Vérifie la frontière P2/P3 : aucune ressource Terraform interdite par
contracts/platforms/boundary.toml dans le code d'une plateforme, modules locaux compris.

Usage : python3 scripts/check_boundary.py [--root .]
Code retour : 0 si conforme, 1 si une ressource interdite est trouvée, 2 si config invalide.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import sys
import tomllib
from pathlib import Path

RESOURCE_RE = re.compile(r'^\s*(resource|data)\s+"([^"]+)"\s+"([^"]+)"', re.MULTILINE)
MODULE_SOURCE_RE = re.compile(r'module\s+"[^"]+"\s*\{[^}]*?\bsource\s*=\s*"(\.{1,2}/[^"]+)"', re.DOTALL)


def tf_files(directory: Path, seen: set[Path]) -> list[Path]:
    """Fichiers .tf d'un dossier + ceux des modules locaux qu'il appelle, récursivement."""
    directory = directory.resolve()
    if directory in seen or not directory.is_dir():
        return []
    seen.add(directory)
    files = sorted(p for p in directory.glob("*.tf") if p.is_file())
    for f in list(files):
        for src in MODULE_SOURCE_RE.findall(f.read_text(encoding="utf-8")):
            files += tf_files(directory / src, seen)
    return files


def check(root: Path) -> int:
    cfg_path = root / "contracts/platforms/boundary.toml"
    try:
        cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"config illisible {cfg_path}: {exc}", file=sys.stderr)
        return 2

    violations = 0
    for name in ("platform2", "platform3"):
        rules = cfg.get(name)
        if not rules:
            print(f"section [{name}] absente de {cfg_path}", file=sys.stderr)
            return 2
        base = root / rules["path"]
        if not base.exists():
            print(f"[{name}] {rules['path']} absent, ignoré")
            continue
        allow = set(rules.get("allow", []))
        for f in tf_files(base, set()):
            text = f.read_text(encoding="utf-8")
            for m in RESOURCE_RE.finditer(text):
                block, rtype, rname = m.groups()
                if rtype in allow:
                    continue
                hit = next((p for p in rules["deny"] if fnmatch.fnmatchcase(rtype, p)), None)
                if hit:
                    line = text.count("\n", 0, m.start()) + 1
                    rel = f.relative_to(root.resolve()) if f.is_relative_to(root.resolve()) else f
                    print(f"{rel}:{line}: [{name}] {block} \"{rtype}\" \"{rname}\" interdit (règle {hit}). {rules['reason']}")
                    violations += 1
    if violations:
        print(f"\n{violations} violation(s) de frontière. Corriger, ou justifier dans une ADR + `allow`.")
        return 1
    print("Frontière P2/P3 respectée.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", type=Path)
    sys.exit(check(parser.parse_args().root.resolve()))


if __name__ == "__main__":
    main()
