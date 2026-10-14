"""CSV 파일 읽기/쓰기 및 SHA-256 해시 계산 — 화면(tkinter) 무관

제공 함수:
    sha256_file(path)            → hex 문자열
    sha256_str(text)             → hex 문자열
    read_csv(path)               → list[dict]
    write_csv(path, rows, header)
    upsert_csv(path, row, key_fields)  → 기존 키 있으면 교체, 없으면 append (tmp-then-replace)
"""
import csv
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ── SHA-256 ───────────────────────────────────────────────────────────────────

def sha256_file(path: str | Path, prefix: int = 0) -> str:
    """파일 SHA-256 hex.  prefix > 0 이면 앞 N자만 반환."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    return digest[:prefix] if prefix else digest


def sha256_str(text: str, prefix: int = 0) -> str:
    """문자열 SHA-256 hex."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:prefix] if prefix else digest


# ── CSV 읽기 ──────────────────────────────────────────────────────────────────

def read_csv(path: str | Path) -> List[Dict[str, str]]:
    """CSV → list[dict].  파일이 없으면 빈 목록.  BOM 자동 처리."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ── CSV 쓰기 ──────────────────────────────────────────────────────────────────

def write_csv(path: str | Path,
              rows: List[Dict[str, Any]],
              header: Optional[Sequence[str]] = None) -> None:
    """rows → CSV.  header 미지정 시 첫 행 키 사용.  부모 디렉토리 자동 생성."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and header is None:
        header = []
    fieldnames = list(header) if header is not None else list(rows[0].keys())
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in fieldnames} for r in rows)
    os.replace(tmp, path)          # 원자적 교체


# ── Upsert ────────────────────────────────────────────────────────────────────

def upsert_csv(path: str | Path,
               row: Dict[str, Any],
               key_fields: Sequence[str],
               header: Optional[Sequence[str]] = None) -> None:
    """기존 CSV에서 key_fields 가 같은 행은 교체, 없으면 append.
    header 미지정 시 기존 파일 헤더 → row 키 순으로 결정."""
    path = Path(path)
    existing = read_csv(path)
    if existing:
        fieldnames = list(existing[0].keys())
    elif header is not None:
        fieldnames = list(header)
    else:
        fieldnames = list(row.keys())

    key = tuple(str(row.get(k, "")) for k in key_fields)
    replaced = False
    for i, r in enumerate(existing):
        if tuple(str(r.get(k, "")) for k in key_fields) == key:
            existing[i] = row
            replaced = True
            break
    if not replaced:
        existing.append(row)
    write_csv(path, existing, fieldnames)
