"""단계 흐름 규칙 — 누가 / 어떤 이미지를 / 어디로 보낼 수 있는지 + 작업 이력
   화면(tkinter)과 파일 이동은 다루지 않고, 사람 목록(config.PEOPLE)과 이력 csv 로 '판정'만 한다.
     작업자 : final 을 뺀 모든 이미지 작업 → pass / edited / review 로 저장 (저장한 뒤에도 다시 수정 가능)
     검수자 : 모든 이미지 작업 가능 (작업자 일 포함) → pass / edited / review / view / final
              (pass·edited·review 확인 → final 승인 또는 view 로 재작업 요청, final 도 언제든 view 로)"""
import csv
import os

from src.config import (INFO_FIELDS, PEOPLE, ROLE_NAMES, STAGE_LABELS,
                        WORKER_TARGETS, REVIEWER_TARGETS, WORKER_EDITABLE, DEFAULT_TARGET)

WORKER, REVIEWER = "worker", "reviewer"
ID_KEY = INFO_FIELDS[-1][1]          # 사람을 구분하는 열 꼬리 ('id')


# ── 사람 목록 ──
def person_label(person):
    """드롭다운 표시 — 예) '1 (검수자)'"""
    return f"{person['name']} ({ROLE_NAMES[person['role']]})"


def people_labels():
    return [person_label(p) for p in PEOPLE]


def person_by_label(label):
    for p in PEOPLE:
        if person_label(p) == label:
            return p
    return None


def check_people():
    """config.PEOPLE 검사 — 역할 오타 / ID 중복이면 프로그램 시작 시 바로 오류"""
    ids = [p[ID_KEY] for p in PEOPLE]
    if len(ids) != len(set(ids)):
        raise ValueError(f"config.PEOPLE: 같은 {ID_KEY} 가 두 번 있습니다. {ids}")
    for p in PEOPLE:
        if p.get("role") not in ROLE_NAMES:
            raise ValueError(f"config.PEOPLE: {p} 의 role 은 {tuple(ROLE_NAMES)} 중 하나여야 합니다.")
        for _, key in INFO_FIELDS:
            if not str(p.get(key, "")).strip():
                raise ValueError(f"config.PEOPLE: {p} 에 '{key}' 값이 없습니다.")


# ── 이력 읽기 ──
def read_events(csv_path):
    """이미지별 이력 csv → 저장 1회당 1개의 dict 목록 (오래된 순)
       csv 는 박스 1개당 1행이므로 (saved_at, stage) 가 같은 연속 행을 하나로 묶는다."""
    if not csv_path or not os.path.exists(csv_path):
        return []
    events = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            row = {k: (v or "") for k, v in row.items() if k}
            key = (row.get("saved_at"), row.get("stage"))
            if events and events[-1]["_key"] == key:
                continue
            row["_key"] = key
            events.append(row)
    return events


def who(ev):
    """기록 1건을 저장한 사람 → '이름 (ID)' (작업자·검수자 중 채워진 쪽)"""
    for role in (REVIEWER, WORKER):
        vals = [ev.get(f"{role}_{key}", "") for _, key in INFO_FIELDS]
        if any(vals):
            return vals[0] + (f" ({', '.join(vals[1:])})" if len(vals) > 1 else "")
    return "-"


# ── 한 이미지의 상태 ──
class Flow:
    """stage: 이 이미지가 지금 있는 폴더 ('' = 원본), events: 이력 csv 기록"""

    def __init__(self, stage, events):
        self.stage = stage or ""
        self.events = events

    def can_act(self, person):
        """→ (가능 여부, 안 되는 이유)"""
        if person is None:
            return False, "작업자 정보에서 이름을 선택해야 수정·저장할 수 있습니다."
        if person["role"] == REVIEWER:
            return True, ""
        if self.stage in WORKER_EDITABLE:
            return True, ""
        if self.stage == "final":
            return False, "final 이미지는 검수자만 다룰 수 있습니다."
        return False, f"{self.stage} 이미지는 작업자가 다룰 수 없습니다."

    @staticmethod
    def targets(person):
        """검수 상태에서 고를 수 있는 단계"""
        if person is None:
            return ()
        return REVIEWER_TARGETS if person["role"] == REVIEWER else WORKER_TARGETS

    def default_target(self, person):
        """검수 상태 기본 선택
           작업자: 지금 있는 단계(pass·edited·review) 그대로, 그 외(원본·view)는 pass
           검수자: 확인할 이미지면 final, final 이면 view"""
        if person and person["role"] == REVIEWER:
            if self.stage in ("pass", "edited", "review"):
                return "final"
            if self.stage == "final":
                return "view"
        if self.stage in WORKER_TARGETS:
            return self.stage
        return DEFAULT_TARGET

    @staticmethod
    def records_review(person):
        """검수자 저장이면 박스별 review_action 기록"""
        return person is not None and person["role"] == REVIEWER

    # ── 작업 이력 패널 문구 ──
    def history_lines(self):
        """(위: 단계별 처음 저장한 사람 — 고정) + (아래: 그 뒤의 이동 기록 — 덧붙임)"""
        firsts = {}
        for ev in self.events:
            firsts.setdefault(ev["stage"], ev)
        top = [f"{label:<6} {who(firsts[st]) if st in firsts else '-'}"
               for st, label in STAGE_LABELS.items()]
        first_ids = {id(ev) for ev in firsts.values()}
        log = [f"{ev.get('saved_at', '')[5:16]} {ev.get('from', '')}→{ev['stage']} {who(ev)}"
               for ev in self.events if id(ev) not in first_ids]
        return top, log


check_people()
