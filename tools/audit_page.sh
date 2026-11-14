#!/bin/bash
# audit_page.sh: pre-push checks for the web app (app/) and its data (data/processed/).
#
# Usage (from anywhere; the script moves to the repo root first):
#     bash tools/audit_page.sh
#
# Prints PASS, WARN or FAIL lines, then a summary table. Exits 1 if any check FAILs.
# Grep checks skip comment lines (lines that start with //, /*, * or <!--). A comment
# that sits after code on the same line is still scanned. Sizes: 1 MB = 1048576 bytes,
# 600 KB = 614400 bytes (same as tools/make_web_assets.py). No network access.
# Bash 3.2 compatible (the default bash on macOS).
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd) || exit 1
cd "$ROOT" || exit 1

IMG_LIMIT=614400          # 600 KB per image
PAGE_LIMIT=15728640       # 15 MB page weight
ALLOW_CDN=1572864         # 1.5 MB allowance: CDN libraries and fonts
ALLOW_TILES=3145728       # 3 MB allowance: map tiles
MANIFEST="data/processed/manifest.json"

N_PASS=0; N_WARN=0; N_FAIL=0
SEC_NAME=""; SEC_F0=0; SEC_W0=0
SUMMARY=""

pass() { N_PASS=$((N_PASS + 1)); printf 'PASS  %s\n' "$1"; }
warn() { N_WARN=$((N_WARN + 1)); printf 'WARN  %s\n' "$1"; }
fail() { N_FAIL=$((N_FAIL + 1)); printf 'FAIL  %s\n' "$1"; }

section() {
  SEC_NAME="$1"; SEC_F0=$N_FAIL; SEC_W0=$N_WARN
  printf '\n== %s\n' "$1"
}

# section_end DETAIL: records one summary row; the row status comes from the FAIL/WARN counters
section_end() {
  local st="PASS"
  if [ "$N_FAIL" -gt "$SEC_F0" ]; then st="FAIL"
  elif [ "$N_WARN" -gt "$SEC_W0" ]; then st="WARN"; fi
  SUMMARY="${SUMMARY}$(printf '%-30s %-5s %s' "$SEC_NAME" "$st" "$1")"$'\n'
}

# bytes_of PATHS...: total size of the regular files found under the given paths (find syntax)
bytes_of() {
  find "$@" -type f -exec wc -c {} + 2>/dev/null | awk '$2 != "total" { s += $1 } END { print s + 0 }'
}

mb() { awk -v b="$1" 'BEGIN { printf "%.2f MB", b / 1048576 }'; }

# scan MODE PATTERN FILES...: prints file:line:text for every match outside comment lines.
# MODE i = case-insensitive. Prints nothing when there are no matches.
scan() {
  local mode="$1" pat="$2"; shift 2
  [ "$#" -gt 0 ] || return 0
  local flags="-HnE"
  [ "$mode" = "i" ] && flags="-HniE"
  grep $flags -- "$pat" "$@" 2>/dev/null \
    | grep -vE '^[^:]+:[0-9]+:[[:space:]]*(//|/\*|\*|<!--)' || true
}

count_lines() { printf '%s' "$1" | grep -c . || true; }

# ---------------------------------------------------------------- (a) page weight
section "(a) page weight"
HTML_B=$(bytes_of app/index.html)
CSS_B=$(bytes_of app/css -name '*.css')
JS_B=$(bytes_of app/js -name '*.js')
STR_B=$(bytes_of app/strings -name '*.json')
DATA_B=$(bytes_of data/processed)
APP_B=$((HTML_B + CSS_B + JS_B + STR_B))
TOTAL=$((APP_B + DATA_B + ALLOW_CDN + ALLOW_TILES))
printf '      page html %s, css %s, js %s, strings %s, data/processed %s (includes img/)\n' \
  "$(mb $HTML_B)" "$(mb $CSS_B)" "$(mb $JS_B)" "$(mb $STR_B)" "$(mb $DATA_B)"
printf '      plus allowances 1.5 MB (CDN and fonts) and 3.00 MB (map tiles)\n'
if [ "$TOTAL" -gt "$PAGE_LIMIT" ]; then
  fail "page weight estimate $(mb $TOTAL) is over the 15 MB limit"
else
  pass "page weight estimate $(mb $TOTAL) (limit 15 MB)"
fi

BIG_N=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  fail "image over 600 KB: $line"; BIG_N=$((BIG_N + 1))
done < <(find data/processed/img -type f -exec wc -c {} + 2>/dev/null \
  | awk -v lim="$IMG_LIMIT" '$2 != "total" && $1 > lim { printf "%s (%d bytes)\n", $2, $1 }')
[ "$BIG_N" -eq 0 ] && pass "every file in data/processed/img is 600 KB or smaller"
section_end "$(mb $TOTAL) of 15 MB; $BIG_N image(s) over 600 KB"

# ---------------------------------------------------------------- (b) forbidden hard-coding
section "(b) forbidden hard-coding"
UI_FILES=(app/index.html app/js/*.js)
NAME_FILES=()
for f in "${UI_FILES[@]}"; do
  [ "$(basename "$f")" = "case.js" ] || NAME_FILES+=("$f")
done

DATE_HITS=$(scan c '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "${UI_FILES[@]}")
while IFS= read -r line; do
  [ -n "$line" ] || continue
  fail "literal ISO date: $line"
done <<< "$DATE_HITS"
[ -z "$DATE_HITS" ] && pass "no literal ISO dates in app/index.html or app/js (comments skipped)"

T156_HITS=$(scan c 'T156' "${UI_FILES[@]}")
while IFS= read -r line; do
  [ -n "$line" ] || continue
  fail "Track 156 mentioned: $line"
done <<< "$T156_HITS"
[ -z "$T156_HITS" ] && pass "no 'T156' in app/index.html or app/js"

NAME_HITS=$(scan i 'Arnab|Narsapur' "${NAME_FILES[@]}")
while IFS= read -r line; do
  [ -n "$line" ] || continue
  fail "event name outside case.js: $line"
done <<< "$NAME_HITS"
[ -z "$NAME_HITS" ] && pass "'Arnab' and 'Narsapur' appear only in app/js/case.js (outside comments)"
section_end "dates $(count_lines "$DATE_HITS"), T156 $(count_lines "$T156_HITS"), names $(count_lines "$NAME_HITS") hit(s)"

# ---------------------------------------------------------------- (c) hex colours
section "(c) hex colours"
CSS_FILES=()
for f in app/css/*.css; do
  [ "$(basename "$f")" = "tokens.css" ] || CSS_FILES+=("$f")
done
HEX='#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?([^-_0-9A-Za-z]|$)'

CSS_HITS=$(scan c "$HEX" "${CSS_FILES[@]}")
while IFS= read -r line; do
  [ -n "$line" ] || continue
  fail "hex colour outside tokens.css: $line"
done <<< "$CSS_HITS"
[ -z "$CSS_HITS" ] && pass "no hex colours in app/css outside tokens.css"

JS_HITS=$(scan c "$HEX" app/js/*.js)
while IFS= read -r line; do
  [ -n "$line" ] || continue
  warn "hex colour in JavaScript: $line"
done <<< "$JS_HITS"
[ -z "$JS_HITS" ] && pass "no hex colours in app/js (comments skipped)"
section_end "css $(count_lines "$CSS_HITS") hit(s) (FAIL), js $(count_lines "$JS_HITS") hit(s) (WARN)"

# ---------------------------------------------------------------- (d) manifest checker
section "(d) manifest checker"
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found, cannot run tools/check_manifest.py"
  CM_NOTE="python3 missing"
else
  CM_OUT=$(python3 tools/check_manifest.py 2>&1); CM_RC=$?
  CM_LAST=$(printf '%s\n' "$CM_OUT" | grep -E '^(PASS|FAIL) \(' | tail -1)
  if [ "$CM_RC" -eq 0 ]; then
    pass "tools/check_manifest.py passes: $CM_LAST"
  else
    fail "tools/check_manifest.py fails: $CM_LAST"
    printf '%s\n' "$CM_OUT" | grep -E '^FAIL|^ +- ' | sed 's/^/      /'
  fi
  CM_NOTE="exit $CM_RC; $CM_LAST"
fi
section_end "$CM_NOTE"

# ---------------------------------------------------------------- (e) JSON parses
section "(e) JSON parses"
JSON_N=0; JSON_BAD=0
while IFS= read -r -d '' f; do
  JSON_N=$((JSON_N + 1))
  if ! python3 -m json.tool "$f" >/dev/null 2>&1; then
    fail "does not parse as JSON: $f"; JSON_BAD=$((JSON_BAD + 1))
  fi
done < <(find data/processed app/strings -type f \( -name '*.json' -o -name '*.geojson' \) -print0 2>/dev/null)
if [ "$JSON_N" -eq 0 ]; then
  warn "no JSON files found under data/processed or app/strings"
elif [ "$JSON_BAD" -eq 0 ]; then
  pass "all $JSON_N JSON files in data/processed and app/strings parse"
fi
section_end "$JSON_N file(s) checked, $JSON_BAD bad"

# ---------------------------------------------------------------- (f) referenced files exist
section "(f) referenced files exist"
REF_PY='
import json, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
rows = []
for l in m.get("layers", []):
    for k in ("png", "file"):
        if l.get(k):
            rows.append((l[k], l.get("status", ""), l.get("id", "")))
    for c in l.get("classes") or []:
        if c.get("png"):
            rows.append((c["png"], l.get("status", ""), l.get("id", "")))
for e in m.get("events", []):
    if e.get("track_geojson"):
        rows.append((e["track_geojson"], "", e.get("id", "")))
for a in m.get("analyses", []):
    if a.get("rank_file"):
        rows.append((a["rank_file"], "", a.get("id", "")))
for k, v in (m.get("files") or {}).items():
    if v:
        rows.append((v, "", "files." + k))
for p, s, who in rows:
    print("|".join([p, s, who]))
'
REF_OK=0; REF_ALLOWED=0; REF_MISS=0
if [ ! -f "$MANIFEST" ]; then
  fail "$MANIFEST is missing"
else
  REF_LIST=$(python3 -I -c "$REF_PY" "$MANIFEST" 2>/dev/null) || REF_LIST=""
  while IFS='|' read -r p st who; do
    [ -n "$p" ] || continue
    if [ -e "$p" ]; then REF_OK=$((REF_OK + 1))
    elif [ "$st" = "unavailable" ]; then REF_ALLOWED=$((REF_ALLOWED + 1))
    else REF_MISS=$((REF_MISS + 1)); warn "missing file: $p (referenced by $who, status ${st:-none})"
    fi
  done <<< "$REF_LIST"
  if [ "$REF_MISS" -eq 0 ]; then
    pass "$REF_OK referenced file(s) exist; $REF_ALLOWED missing but status unavailable (allowed)"
  fi
fi
section_end "$REF_OK present, $REF_ALLOWED allowed, $REF_MISS missing"

# ---------------------------------------------------------------- (g) JavaScript syntax
section "(g) JavaScript syntax"
if ! command -v node >/dev/null 2>&1; then
  warn "node not found, JavaScript syntax not checked"
  JS_SYN_NOTE="skipped (no node)"
else
  JS_N=0; JS_BAD=0
  for f in app/js/*.js; do
    JS_N=$((JS_N + 1))
    ERR=$(node --check "$f" 2>&1) || {
      fail "syntax error: $f"
      printf '%s\n' "$ERR" | head -4 | sed 's/^/      /'
      JS_BAD=$((JS_BAD + 1))
    }
  done
  [ "$JS_BAD" -eq 0 ] && pass "node --check passes on all $JS_N files in app/js"
  JS_SYN_NOTE="$JS_N file(s), $JS_BAD with errors"
fi
section_end "${JS_SYN_NOTE:-}"

# ---------------------------------------------------------------- summary
echo
echo "== Summary"
printf '%-30s %-5s %s\n' "Check" "Result" "Detail"
printf '%-30s %-5s %s\n' "------------------------------" "-----" "------"
printf '%s' "$SUMMARY"
echo
echo "$N_PASS PASS, $N_WARN WARN, $N_FAIL FAIL"
if [ "$N_FAIL" -gt 0 ]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: PASS"
exit 0
