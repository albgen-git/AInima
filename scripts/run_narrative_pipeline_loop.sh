#!/bin/bash
PY="C:\Users\PC\AppData\Local\Programs\Python\Python310\python.exe"
cd "C:\Users\PC\Desktop\AInima Project"
max_iter=25
i=0
while [ $i -lt $max_iter ]; do
  remaining=$("$PY" -c "
import sys; sys.path.insert(0, 'backend')
from db import get_conn
c = get_conn(); cur = c.cursor()
cur.execute(\"SELECT count(*) AS n FROM psychometric_scores WHERE self_embedding_vector IS NULL\")
print(cur.fetchone()['n'])
")
  echo "=== Iterazione $i, ancora da fare: $remaining ==="
  if [ "$remaining" = "0" ]; then
    echo "Completato tutto."
    break
  fi
  "$PY" scripts/run_narrative_pipeline.py --limit 40
  i=$((i+1))
  sleep 2
done
