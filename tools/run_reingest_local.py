#!/usr/bin/env python3
"""run_reingest_local.py — re-ingest the 20 revised poems + 50 haiku series from the
local Google Drive mirror into the flow model, then rebuild v3 literal HTML.

It does NOT commit or push — it only rewrites data/flows/<slug>.json, images/flow/<slug>,
and data/rawdocx/<slug>.html so you can review `git diff` before publishing.

Run from repo root:
  python3 tools/run_reingest_local.py \
    --poems "/Users/edgar2025/Library/CloudStorage/GoogleDrive-hoedgar@gmail.com/My Drive/Haiku series/Poems--2026-july  CHINESE 1-20 pieces" \
    --haiku "/Users/edgar2025/Library/CloudStorage/GoogleDrive-hoedgar@gmail.com/My Drive/Haiku series/Poems & Haiku--KK-Haiku only--JULY---1-50-PIECES"
"""
import os, sys, re, json, argparse, glob
sys.path.insert(0, os.path.dirname(__file__))
from ingest_local import ingest_local
import literal_docx_to_html as LIT

# poem source filename (whitespace-stripped stem) -> existing catalog slug
POEM_MAP = {
    "茱麗葉故居": "p_317a3ffd",
    "走下武嶺的山路": "wuling-mountain-road",
    "那時愛琴海没有名字": "p_5cea581e",
    "雨中九份": "jiufen-rain",
    "霧迷龜山島": "p_19c83be1",
    "馬德里的黃昏": "madrid-dusk",
    "那年夏日海風如歌": "p_9aea5d74",
    "雨中看小企鵝回家": "p_new_18FxzH",
    "雨夜看西安大雁塔": "p_e43ca3f9",
    "飄浮的水城": "p_8d53e68d",
    "衫林溪的雲霧": "p_new_1X0aAr",
    "許檜木林一個蒼翠未來": "p_2f951172",
    "開始一趟旅程": "beginning-a-journey-britain",
    "野柳女王岩": "yehliu-queen-rock",
    "風景因此而美": "p_d069408e",
    "風帆如詩": "sydney-sails",
    "貝加爾湖漫步隨想": "p_c2ae755f",
    "飛越Okavango内陸三角洲": "p_c595ebe4",
    "飛越Okavango內陸三角洲": "p_c595ebe4",  # variant 內/内
    "詩意的畫苦寂的心": "p_fe772049",
    "莫那魯道的霧社": "p_593ba797",
}


def titles_by_slug():
    inv = json.load(open("data/flows/_inventory.json"))
    return {e["slug"]: e["title"] for e in inv}


def build_v3(docx, slug, title):
    """Regenerate the v3 literal popup HTML for one piece."""
    os.makedirs("data/rawdocx", exist_ok=True)
    paras, z = LIT.parse(docx)
    frag = LIT.render_html(paras, z)
    open(f"data/rawdocx/{slug}.html", "w", encoding="utf-8").write(frag)


def norm(stem):
    return re.sub(r"\s+", "", stem)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poems", required=True)
    ap.add_argument("--haiku", required=True)
    ap.add_argument("--v3", action="store_true", default=True, help="also rebuild v3 literal HTML")
    a = ap.parse_args()
    T = titles_by_slug()
    results = []

    # ---- poems ----
    for path in sorted(glob.glob(os.path.join(a.poems, "*.docx"))):
        base = os.path.basename(path)
        if base.startswith("~$"):
            continue
        stem = os.path.splitext(base)[0]
        slug = POEM_MAP.get(norm(stem))
        if not slug:
            results.append(("POEM?", base, "NO SLUG MATCH"))
            continue
        title = T.get(slug, stem)
        nh, nimg, nb = ingest_local(path, "poem", slug, title)
        build_v3(path, slug, title)
        results.append(("poem", slug, f"blocks={nb} img={nimg}"))

    # ---- haiku ----
    for path in sorted(glob.glob(os.path.join(a.haiku, "*.docx"))):
        base = os.path.basename(path)
        if base.startswith("~$"):
            continue
        m = re.search(r"--\s*(\d+)\s*\.docx$", base) or re.search(r"(\d+)\.docx$", base)
        if not m:
            results.append(("HAIKU?", base, "NO NUMBER"))
            continue
        n = int(m.group(1))
        slug = f"hdoc{n}"
        title = T.get(slug, f"現代俳句和變奏 {n}")
        nh, nimg, nb = ingest_local(path, "haiku", slug, title)
        build_v3(path, slug, title)
        # expected sequential range for this series
        exp = list(range((n - 1) * 10 + 1, n * 10 + 1))
        d = json.load(open(f"data/flows/{slug}.json"))
        nums = [h["n"] for h in d["haiku"]]
        flag = "OK" if sorted(nums) == exp else "CHECK"
        results.append(("haiku", slug, f"count={len(nums)} {flag} nums={nums}"))

    print("=== RE-INGEST SUMMARY ===")
    for kind, key, info in results:
        print(f"{kind:7} {key:28} {info}")
    checks = [r for r in results if "CHECK" in r[2] or "?" in r[0]]
    print(f"\n{len(results)} files ingested; {len(checks)} need review:")
    for r in checks:
        print("  ", r)
    print("\nNext: `python3 tools/_enrich.py` then regenerate data/flows/_embedded.js and"
          " re-inline the base64 blob in index_v2.html, then review `git diff` and push.")


if __name__ == "__main__":
    main()
