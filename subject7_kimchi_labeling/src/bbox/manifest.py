"""데이터 대장(manifest) — 이미지 1장당 1행, 저장할 때마다 그 행만 최신 값으로 덮어씀 (upsert)
   화면(tkinter)과 무관한 계산·파일 쓰기만 담당. 값 규칙은 config.MANIFEST_HEADER / STAGE_STATUS
     file_name      이미지 파일명
     source_dataset 데이터셋 이름 (folder_mixin 이 정함)
     original_split train / validation (이미지 폴더 경로에서 찾음, 없으면 빈칸)
     scene_type     작업자가 선택
     worker         처음 저장한 사람 — 한 번 정해지면 바뀌지 않음
     status/qa_status  저장 단계로 결정 (view 는 status 유지 + WAIT)
     review_reason  새로 고르면 바뀌고, 고르지 않으면 이전 값 유지 (지우지 않음)
   - 행 찾기: (source_dataset, original_split, file_name) — train·validation 에 같은 파일명이 있어도 구분
   - 행 순서 유지(제자리 수정) → Git 충돌 줄임 / 임시 파일에 쓴 뒤 교체 → 쓰다가 꺼져도 대장 보존"""
import csv
import os

from src.config import MANIFEST_HEADER, STAGE_STATUS, QA_WAIT, SPLIT_NAMES


class ManifestFormatError(Exception):
    """기존 manifest 의 열 구성이 지금 형식과 다를 때 (덮어쓰면 기존 값이 어긋나므로 쓰지 않음)"""


def split_of(path):
    """이미지가 들어 있는 폴더 경로에서 train / validation 찾기 (가장 가까운 폴더부터). 없으면 ''"""
    for part in reversed(os.path.normpath(os.path.dirname(path)).split(os.sep)):
        name = SPLIT_NAMES.get(part.lower())
        if name:
            return name
    return ""


def _key(row):
    return (row.get("source_dataset", ""), row.get("original_split", ""), row.get("file_name", ""))


def read_rows(path):
    """→ 행 목록 (파일이 없으면 빈 목록). 열 구성이 다르면 ManifestFormatError"""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and list(reader.fieldnames) != MANIFEST_HEADER:
            raise ManifestFormatError(f"{os.path.basename(path)} 열 구성이 다릅니다: {reader.fieldnames}")
        return list(reader)


def find_row(path, dataset, split, file_name):
    """이 이미지의 현재 행 (없거나 읽을 수 없으면 None)"""
    try:
        rows = read_rows(path)
    except (OSError, ManifestFormatError):
        return None
    key = (dataset, split, file_name)
    return next((r for r in rows if _key(r) == key), None)


def build_row(prev, file_name, dataset, split, scene, stage, person_name, reason):
    """저장 1회 → 새 행. prev: 이 이미지의 기존 행 (없으면 None)"""
    prev = prev or {}
    if stage in STAGE_STATUS:
        status, qa = STAGE_STATUS[stage]
    else:                                   # view: 재작업 요청 → 상태는 직전 값 유지, 검수 대기
        status, qa = prev.get("status", ""), QA_WAIT
    return {"file_name": file_name,
            "source_dataset": dataset,
            "original_split": split,
            "scene_type": scene or prev.get("scene_type", ""),
            "worker": prev.get("worker") or person_name,          # 처음 저장한 사람 고정
            "status": status,
            "qa_status": qa,
            "review_reason": reason or prev.get("review_reason", "")}   # 지우지 않음


def upsert(path, row):
    """같은 이미지 행이 있으면 그 자리에서 바꾸고, 없으면 맨 아래에 추가"""
    rows = read_rows(path)
    for i, r in enumerate(rows):
        if _key(r) == _key(row):
            rows[i] = row
            break
    else:
        rows.append(row)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_HEADER)
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in MANIFEST_HEADER} for r in rows)
    os.replace(tmp, path)                   # 다 쓴 뒤 한 번에 교체
