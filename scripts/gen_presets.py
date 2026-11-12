"""Write the manifest's ``llm_presets`` block from ``presets.PRESETS``.

Run from the repository root so the package is importable:

    python -m scripts.gen_presets           # rewrite kohaku.yaml
    python -m scripts.gen_presets --check   # exit 1 when the file is stale
"""

import sys
from pathlib import Path

import yaml

from kt_antigravity_login.presets import PRESETS

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "kohaku.yaml"


def render(manifest: dict) -> str:
    """Serialized manifest with every preset rebuilt from the catalogue."""
    updated = dict(manifest)
    updated["llm_presets"] = [
        {"name": name, "provider": provider, **body}
        for (provider, name), body in PRESETS.items()
    ]
    return yaml.safe_dump(updated, sort_keys=False, allow_unicode=True, width=100)


def main(argv: list[str]) -> int:
    """Rewrite the manifest, or verify it is current with ``--check``."""
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    rendered = render(manifest)
    if "--check" in argv:
        if MANIFEST.read_text(encoding="utf-8") != rendered:
            print("kohaku.yaml is stale; run: python -m scripts.gen_presets")
            return 1
        print(f"kohaku.yaml matches {len(PRESETS)} presets")
        return 0
    MANIFEST.write_text(rendered, encoding="utf-8")
    print(f"wrote {len(PRESETS)} presets to {MANIFEST.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
