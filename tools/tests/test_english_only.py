#!/usr/bin/env python3
"""English-only guard. Plain asserts:  python3 tools/tests/test_english_only.py
Fails if any text the page shows contains a letter outside Latin script (Telugu, Devanagari, Arabic, CJK, Cyrillic, Greek...),
and tests the SACHET fallback (Telugu-only CAP -> one English line; en+te CAP -> the English block)."""
import glob
import json
import os
import sys
import traceback
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "src", "fetch"))
sys.path.insert(0, os.path.join(ROOT, "tools", "pipeline"))
import sachet_snapshot as SS  # noqa: E402
import alerts as AL  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def bad_letters(s):
    return sorted({c for c in s if c.isalpha() and not unicodedata.name(c, "").startswith("LATIN")})


def strings_of(o, path="$"):
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from strings_of(k, path + ".<key>")
            yield from strings_of(v, path + "." + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings_of(v, "%s[%d]" % (path, i))


def check_file(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return
    d = json.load(open(p, encoding="utf-8"))
    for path, s in strings_of(d):
        b = bad_letters(s)
        assert not b, "%s %s has non-Latin letters %s: %r" % (rel, path, b, s[:80])


def files(*pats):
    out = []
    for pat in pats:
        out += [os.path.relpath(f, ROOT) for f in sorted(glob.glob(os.path.join(ROOT, pat)))]
    return out


def test_story_json():
    check_file("data/web/story.json")


def test_findings():
    for f in files("data/processed/findings/*.json"):
        check_file(f)


def test_processed_json():
    for f in ("alerts", "events", "profile", "mandal_rank"):
        check_file("data/processed/%s.json" % f)


def test_strings_and_rules():
    for f in files("app/strings/*.json", "data/story_rules.json"):
        check_file(f)


def test_place_names_latin():
    for rel in ("data/processed/mandals.geojson", "data/processed/mandal_rank.json"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            check_file(rel)


def test_no_language_switch_left():
    for rel in ("app/index.html", "app/css/tokens.css", "app/css/app.css"):
        t = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        assert "Anek+Telugu" not in t and "--font-te" not in t and 'id="lang-te"' not in t, rel


def read(name):
    return open(os.path.join(FIX, name), "rb").read()


def base_item(headline="", office="Andhra Pradesh SDMA"):
    return {"id": "x", "headline": headline, "area": office, "issued": "2026-11-14T17:01:42+05:30", "source": office,
            "link": "https://example.invalid/cap.xml", "category": "Met"}


def test_cap_telugu_only_fallback():
    it = SS.apply_cap(base_item("సముద్రంలో భారీఅలలు"), read("cap_te_only.xml"))
    out = AL.out_sachet_item(it)
    for k, v in out.items():
        assert not bad_letters(str(v)), (k, v)
    assert out["link_label"] == "Original alert (not in English)" and out["lang_note"] == "no English text in the source alert"
    assert out["link"] == "https://example.invalid/cap.xml"
    assert "moderate" in out["headline"] and "issued 14 Nov 2026, 17:01 IST" in out["headline"], out["headline"]
    assert out["headline"].startswith("Meteorological alert"), out["headline"]
    assert "Andhra Pradesh SDMA" in out["headline"] or out["area"] == "Andhra Pradesh SDMA", out


def test_cap_en_te_uses_english_block():
    it = SS.apply_cap(base_item("సముద్రంలో భారీఅలలు"), read("cap_en_te.xml"))
    out = AL.out_sachet_item(it)
    assert out["headline"].startswith("High waves of 3 to 6 m"), out
    assert out["area"] == "Mukkam To Chintapalli", out
    assert "link_label" not in out and "lang_note" not in out
    for v in out.values():
        assert not bad_letters(str(v)), v


def test_rss_title_non_latin_fallback():
    it = SS.english_fallback_rss(base_item("భారీ అలలు హెచ్చరిక"))
    out = AL.out_sachet_item(it)
    assert not bad_letters(out["headline"]) and out["lang_note"] and out["link_label"], out
    assert out["headline"].startswith("Meteorological alert"), out


def test_matching_uses_original_and_english():
    am = {"states": ["Andhra Pradesh"], "keywords": ["Mukkam"]}
    te = SS.apply_cap(base_item("సముద్రంలో", office="SDMA"), read("cap_te_only.xml"))
    te["source"] = "SDMA"
    te["_match_text"] += " Andhra Pradesh"           # original-language text mentioned the state in Latin letters
    assert AL.sachet_matches(te, am)
    en = SS.apply_cap(base_item("సముద్రంలో", office="SDMA"), read("cap_en_te.xml"))
    assert AL.sachet_matches(en, am)                  # keyword Mukkam in the English area
    other = SS.apply_cap(base_item("x", office="Jammu SDMA"), read("cap_te_only.xml"))
    assert not AL.sachet_matches(other, {"states": ["Kerala"], "keywords": []})


def test_build_fixture_output_is_english():
    raw = [AL.out_sachet_item(SS.apply_cap(base_item("సముద్రంలో"), read("cap_te_only.xml")))]
    raw[0]["headline"] = "భారీ అలలు"      # even a stray non-Latin value is replaced by the safety net
    it = dict(raw[0])
    it["_match_text"] = ""
    out = AL.out_sachet_item(it)
    assert not bad_letters(out["headline"]) and out["lang_note"], out


def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    bad = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except Exception:      # noqa: BLE001
            bad += 1
            print("FAIL  %s" % name)
            traceback.print_exc()
    print("%d tests, %d failed" % (len(tests), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
