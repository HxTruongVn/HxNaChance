"""Core-owned persistence for user-created Workshop pipelines."""
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class PipelineStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    def _connect(self): return sqlite3.connect(str(self.db_path))
    def _init_db(self):
        with self._connect() as con:
            con.execute("CREATE TABLE IF NOT EXISTS pipelines (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS pipeline_steps (id INTEGER PRIMARY KEY AUTOINCREMENT, pipeline_id INTEGER NOT NULL, step_order INTEGER NOT NULL, workshop_id TEXT NOT NULL, workshop_version TEXT, workshop_name TEXT, state_json TEXT NOT NULL, FOREIGN KEY(pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE, UNIQUE(pipeline_id, step_order))")
    def save(self, name: str, steps: list[dict[str, Any]], pipeline_id: int | None = None) -> int:
        name = name.strip()
        if not name: raise ValueError("Tên Pipeline không được để trống.")
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as con:
            if pipeline_id is None:
                cur = con.execute("INSERT INTO pipelines(name, created_at, updated_at) VALUES (?, ?, ?)", (name, now, now)); pipeline_id = int(cur.lastrowid)
            else:
                con.execute("UPDATE pipelines SET name=?, updated_at=? WHERE id=?", (name, now, pipeline_id))
                con.execute("DELETE FROM pipeline_steps WHERE pipeline_id=?", (pipeline_id,))
            for idx, step in enumerate(steps, 1):
                con.execute("INSERT INTO pipeline_steps(pipeline_id, step_order, workshop_id, workshop_version, workshop_name, state_json) VALUES (?, ?, ?, ?, ?, ?)", (pipeline_id, idx, step["workshop_id"], step.get("workshop_version"), step.get("workshop_name"), json.dumps(step.get("state") or {}, ensure_ascii=False, sort_keys=True)))
        return pipeline_id
    def list(self):
        with self._connect() as con:
            rows = con.execute("SELECT id,name,created_at,updated_at FROM pipelines ORDER BY updated_at DESC").fetchall()
        return [dict(id=r[0], name=r[1], created_at=r[2], updated_at=r[3]) for r in rows]
    def get(self, pipeline_id: int):
        with self._connect() as con:
            row = con.execute("SELECT id,name,created_at,updated_at FROM pipelines WHERE id=?", (pipeline_id,)).fetchone()
            if not row: return None
            steps = con.execute("SELECT step_order,workshop_id,workshop_version,workshop_name,state_json FROM pipeline_steps WHERE pipeline_id=? ORDER BY step_order", (pipeline_id,)).fetchall()
        return {"id":row[0],"name":row[1],"created_at":row[2],"updated_at":row[3],"steps":[{"order":s[0],"workshop_id":s[1],"workshop_version":s[2],"workshop_name":s[3],"state":json.loads(s[4] or "{}")} for s in steps]}
    def delete(self, pipeline_id: int):
        with self._connect() as con:
            con.execute("DELETE FROM pipeline_steps WHERE pipeline_id=?", (pipeline_id,)); con.execute("DELETE FROM pipelines WHERE id=?", (pipeline_id,))
