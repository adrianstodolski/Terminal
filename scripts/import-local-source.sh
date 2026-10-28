#!/usr/bin/env bash
# Import existing EdgeDepth source tree from the user's Mac into GitHub.
# Does not claim to include the ChatGPT-hosted Theta ZIP unless it is present locally.
set -euo pipefail
REPO_URL="https://github.com/adrianstodolski/Terminal.git"
SOURCE="${EDGE_SOURCE:-$HOME/Dev/market-funnel}"
DEST="${EDGE_DEST:-$HOME/Dev/Terminal}"
if [[ ! -d "$SOURCE/vendor/edgedepth-terminal" || ! -d "$SOURCE/vendor/edgedepth-gateway" ]]; then
  echo "Missing source directories under $SOURCE/vendor. Set EDGE_SOURCE first." >&2
  exit 1
fi
if [[ ! -d "$DEST/.git" ]]; then
  git clone "$REPO_URL" "$DEST"
fi
cd "$DEST"
git remote -v
git pull --ff-only origin main
mkdir -p vendor/edgedepth-terminal vendor/edgedepth-gateway
rsync -a --exclude='.git/' --exclude='node_modules/' --exclude='target/' --exclude='build/' --exclude='dist/' --exclude='.env*' --exclude='*.pem' --exclude='*.key' \
  "$SOURCE/vendor/edgedepth-terminal/" "vendor/edgedepth-terminal/"
rsync -a --exclude='.git/' --exclude='node_modules/' --exclude='target/' --exclude='build/' --exclude='dist/' --exclude='.env*' --exclude='*.pem' --exclude='*.key' \
  "$SOURCE/vendor/edgedepth-gateway/" "vendor/edgedepth-gateway/"
for file in market_scanner.py inspect_signals.py signal_ranker.py candle_levels.py; do
  if [[ -f "$SOURCE/$file" ]]; then cp "$SOURCE/$file" "$file"; fi
done
# If the Theta archive was successfully copied onto the Mac, prefer its full code snapshot.
for zipfile in "$HOME/Downloads/edgedepth-integrated-theta-code.zip" "$HOME/Desktop/edgedepth-integrated-theta-code.zip"; do
 if [[ -f "$zipfile" ]]; then
   echo "Importing Theta code archive: $zipfile"
   python3 - "$zipfile" "$DEST" <<'PY'
import zipfile, sys, pathlib
source=pathlib.Path(sys.argv[1]); dest=pathlib.Path(sys.argv[2]).resolve()
blocked={'.git','node_modules','target','build','dist','__pycache__','.venv'}
with zipfile.ZipFile(source) as archive:
 for info in archive.infolist():
  if info.is_dir(): continue
  rel=pathlib.PurePosixPath(info.filename)
  if rel.is_absolute() or '..' in rel.parts or any(p in blocked for p in rel.parts): continue
  if any(p.startswith('.env') for p in rel.parts) or rel.suffix in {'.pem','.key','.p12','.pfx','.sqlite3','.db'}:continue
  if (info.external_attr >> 16) & 0o170000 == 0o120000:continue
  target=dest.joinpath(*rel.parts)
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(archive.read(info))
PY
   break
 fi
done
echo "Review files before pushing (this GitHub repo may be PUBLIC):"
git status --short | head -80
echo "Scanning obvious secret filenames..."
if git status --porcelain --untracked-files=all | grep -Ei '\\.(pem|key|p12|pfx)$|(^|/)\\.env([./ ]|$)' ; then
  echo "Potential sensitive files detected; stop and inspect." >&2; exit 1
fi
git add -A
git diff --cached --check
git diff --cached --stat
echo
read -r -p "Push reviewed source to GitHub main? Type PUSH: " answer
if [[ "$answer" != "PUSH" ]]; then echo "Not pushed."; exit 0; fi
git commit -m "Import complete local EdgeDepth source and integrations" || true
git push origin main
echo "Done: https://github.com/adrianstodolski/Terminal"
