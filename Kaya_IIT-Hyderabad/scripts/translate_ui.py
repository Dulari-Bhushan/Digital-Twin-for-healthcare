"""Translate the patient app's screen text and the assistant's fixed safety messages into the other Indian languages with Sarvam-Translate.

Writes dashboard/src/i18n_extra.json (screen text) and src/api/lang_extra.json (assistant messages). Both are machine drafts: they need a
native speaker before clinical use, and the app says so. Re-running only translates what is missing (results are cached in
data/translate_cache.json), so an interrupted run can simply be started again.

    python scripts/translate_ui.py            # all missing strings, all languages
    python scripts/translate_ui.py ta bn      # only these languages
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "api"))

import httpx  # noqa: E402
from voice import BASE, load_key  # noqa: E402

# app code -> Sarvam language code (Hindi, Telugu and Kannada are written by hand and are not touched here)
LANGS = {
    "as": "as-IN", "bn": "bn-IN", "brx": "brx-IN", "doi": "doi-IN", "gu": "gu-IN", "ks": "ks-IN", "kok": "kok-IN", "mai": "mai-IN",
    "ml": "ml-IN", "mni": "mni-IN", "mr": "mr-IN", "ne": "ne-IN", "od": "od-IN", "pa": "pa-IN", "sa": "sa-IN", "sat": "sat-IN",
    "sd": "sd-IN", "ta": "ta-IN", "ur": "ur-IN",
}
CACHE = ROOT / "data" / "translate_cache.json"
OUT_UI = ROOT / "dashboard" / "src" / "i18n_extra.json"
OUT_API = ROOT / "src" / "api" / "lang_extra.json"
PH = re.compile(r"\{(\w+)\}")
LOCK = threading.Lock()


def english_strings() -> dict[str, str]:
    """The English screen text: the `en` object literal in dashboard/src/i18n.js, evaluated by node."""
    src = (ROOT / "dashboard" / "src" / "i18n.js").read_text(encoding="utf-8")
    start = src.index("const en = {") + len("const en = ")
    end = src.index("\n}", start) + 2
    out = subprocess.run(["node", "-e", f"console.log(JSON.stringify({src[start:end]}))"], capture_output=True, text=True, check=True, encoding="utf-8").stdout
    return {k: v for k, v in json.loads(out).items() if isinstance(v, str)}


def api_strings() -> dict[str, str]:
    import assistant as a
    d = {"emergency": a.EMERGENCY_MSG["en"], "medicine": a.MEDICINE_MSG["en"], "fallback": a.FALLBACK_MSG["en"], "open": a.OPEN_MSG["en"]}
    d.update({f"tab{i}": x for i, x in enumerate(a.TAB_LABEL["en"])})
    return d


def translate(client: httpx.Client, key: str, text: str, code: str, tries: int = 5) -> str | None:
    """One string, with placeholders like {n} protected as {{1}}. None when the result lost a placeholder every time."""
    names = list(dict.fromkeys(PH.findall(text)))
    src = PH.sub(lambda m: "{{%d}}" % (names.index(m.group(1)) + 1), text)
    for _ in range(tries):
        try:
            r = client.post(f"{BASE}/translate", headers={"api-subscription-key": key}, timeout=40,
                            json={"input": src, "source_language_code": "en-IN", "target_language_code": code, "model": "sarvam-translate:v1"})
            if r.status_code == 429:                                        # rate limited: wait, then try again
                time.sleep(3 + 4 * _)
                continue
            if r.status_code != 200:
                continue
            out = (r.json().get("translated_text") or "").strip()
        except (httpx.HTTPError, ValueError):
            continue
        if out and all(("{{%d}}" % (i + 1)) in out for i in range(len(names))) and out.count("{{") == len(names):
            for i, n in enumerate(names):
                out = out.replace("{{%d}}" % (i + 1), "{%s}" % n)
            return out
    return None


def main() -> None:
    key = load_key(ROOT)
    if not key:
        sys.exit("SARVAM_API_KEY is not set")
    wanted = [c for c in sys.argv[1:] if c in LANGS] or list(LANGS)
    ui, api = english_strings(), api_strings()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    jobs = [(lang, f"ui:{k}", v) for lang in wanted for k, v in ui.items() if f"{lang}|ui:{k}" not in cache]
    jobs += [(lang, f"api:{k}", v) for lang in wanted for k, v in api.items() if f"{lang}|api:{k}" not in cache]
    print(f"{len(jobs)} strings to translate into {len(wanted)} languages", flush=True)
    done = [0]
    with httpx.Client() as client:
        def work(job):
            lang, key_, text = job
            res = translate(client, key, text, LANGS[lang])
            with LOCK:
                if res is not None:                                              # failures are not cached, so a re-run tries them again
                    cache[f"{lang}|{key_}"] = res
                done[0] += 1
                if done[0] % 200 == 0:
                    CACHE.parent.mkdir(exist_ok=True)
                    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                    print(f"  {done[0]}/{len(jobs)}", flush=True)
        with ThreadPoolExecutor(3) as ex:
            list(ex.map(work, jobs))
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    ui_out, api_out, failed = {}, {}, {}
    for lang in LANGS:
        u = {k: cache[f"{lang}|ui:{k}"] for k in ui if cache.get(f"{lang}|ui:{k}")}
        if not u:
            continue
        ui_out[lang] = u
        failed[lang] = len(ui) - len(u)
        a = {k: cache[f"{lang}|api:{k}"] for k in api if cache.get(f"{lang}|api:{k}")}
        api_out[lang] = {"emergency": a.get("emergency"), "medicine": a.get("medicine"), "fallback": a.get("fallback"), "open": a.get("open"),
                         "tabs": [a.get(f"tab{i}") for i in range(4)]}
    OUT_UI.write_text(json.dumps(ui_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    OUT_API.write_text(json.dumps(api_out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("strings left in English (placeholder trouble or service error):", failed)


if __name__ == "__main__":
    main()
