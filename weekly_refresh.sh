#!/bin/zsh
# Щотижневе автооновлення звіту Orders Health.
# Запускається через launchd (щопонеділка 10:30 за Києвом).
# Тягне свіжі дані з Databricks (main.ng_delivery), ребілдить HTML і пушить у GitHub Pages.
set -u
REPO="/Users/yuliia.nikolaieva/Library/CloudStorage/GoogleDrive-yuliia.nikolaieva@bolt.eu/My Drive/Cursor/Reports GIT HUB/Failed-Orders"
LOG="$REPO/refresh.log"
PY=/usr/bin/python3
GIT=/usr/bin/git

cd "$REPO" || { echo "$(date) cannot cd to repo" >> "$LOG"; exit 1; }
echo "" >> "$LOG"
echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') weekly refresh START =====" >> "$LOG"

"$PY" build_data.py >> "$LOG" 2>&1 || { echo "!! build_data.py FAILED" >> "$LOG"; exit 1; }
"$PY" build_html.py >> "$LOG" 2>&1 || { echo "!! build_html.py FAILED" >> "$LOG"; exit 1; }

"$GIT" add -A >> "$LOG" 2>&1
if "$GIT" diff --cached --quiet; then
  echo "-- no changes to commit" >> "$LOG"
else
  "$GIT" -c user.email="report@local" -c user.name="weekly-report" \
    commit -m "Weekly auto-refresh $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
  if "$GIT" push origin main >> "$LOG" 2>&1; then
    echo "-- pushed OK" >> "$LOG"
  else
    echo "!! git push FAILED (перевір git-креденшли / gh auth)" >> "$LOG"
  fi
fi
echo "===== $(date '+%H:%M:%S') weekly refresh DONE =====" >> "$LOG"
