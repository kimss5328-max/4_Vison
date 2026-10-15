"""클래스 규칙 — 지정 가능 여부 / 대체 클래스 / 자동 라벨링 처리 방식
   규칙의 내용은 config.CLASSES 표에 있고, 이 파일은 그 표를 해석하는 함수만 둔다.
   목록 표시·클릭·저장·자동 라벨링·경고 문구가 모두 이 함수들을 거치므로,
   규칙을 바꿀 때는 config.CLASSES 만 고치면 된다. (자동 validation 규칙도 이 패키지에 추가)"""
from src.config import CLASSES, ISSUE_ID

AUTO_POLICIES = ("keep", "drop", "replace")
_BY_ID = {c["id"]: c for c in CLASSES}


# ── 표 검사 (프로그램 시작 시 한 번) ──
def check_class_table():
    """config.CLASSES 가 올바른지 확인 — 잘못되면 ValueError (어디가 틀렸는지 알려줌)"""
    ids = sorted(_BY_ID)
    if len(ids) != len(CLASSES):
        raise ValueError("config.CLASSES: 같은 id 가 두 번 있습니다.")
    if ids != list(range(len(ids))):
        raise ValueError(f"config.CLASSES: id 는 0 부터 빠짐없이 있어야 합니다. 현재 {ids}")
    for c in CLASSES:
        rep = c.get("replace_with")
        if rep is not None:
            if rep not in _BY_ID:
                raise ValueError(f"config.CLASSES: {c['id']}번의 replace_with={rep} 가 없는 번호입니다.")
            if not is_selectable(rep):
                raise ValueError(f"config.CLASSES: {c['id']}번의 replace_with={rep} 도 지정 불가 클래스입니다.")
        pol = c.get("auto_label", "keep")
        if pol not in AUTO_POLICIES:
            raise ValueError(f"config.CLASSES: {c['id']}번의 auto_label='{pol}' 는 {AUTO_POLICIES} 중 하나여야 합니다.")
        if pol == "replace" and rep is None:
            raise ValueError(f"config.CLASSES: {c['id']}번은 auto_label='replace' 인데 replace_with 가 없습니다.")


# ── 조회 ──
def class_ids():
    """정의된 모든 클래스 번호 (번호 순, 숨김 포함)"""
    return sorted(_BY_ID)


def is_hidden(cls):
    return is_known(cls) and _BY_ID[cls].get("hidden", False)


def list_ids():
    """클래스 목록에 표시할 번호 (숨김 제외, 번호 순) — 목록 줄 i 의 클래스 = list_ids()[i]"""
    return [c for c in class_ids() if not is_hidden(c)]


def is_known(cls):
    return cls in _BY_ID


def class_name(cls):
    return _BY_ID[cls]["name"] if is_known(cls) else "(정의 없는 번호)"


def is_selectable(cls):
    """목록에서 지정할 수 있는 클래스인지 (표에 없는 번호·숨김 클래스는 지정 불가)"""
    return is_known(cls) and not is_hidden(cls) and _BY_ID[cls].get("selectable", True)


def replacement(cls):
    """지정 불가 클래스를 대신할 번호 (없으면 None)"""
    return _BY_ID[cls].get("replace_with") if is_known(cls) else None


def auto_label_policy(cls):
    """자동 라벨링 처리 방식: keep / drop / replace (표에 없는 번호는 drop)"""
    return _BY_ID[cls].get("auto_label", "keep") if is_known(cls) else "drop"


def display_name(cls):
    """클래스 목록에 보여줄 이름 — 예) '4: 고무장갑 (지정 불가 → 1번)'"""
    text = f"{cls}: {class_name(cls)}"
    if is_selectable(cls):
        return text
    rep = replacement(cls)
    return f"{text} (지정 불가 → {rep}번)" if rep is not None else f"{text} (지정 불가)"


def guide_message(cls):
    """지정 불가 클래스를 눌렀을 때 상태 표시줄 안내"""
    rep = replacement(cls)
    if rep is not None:
        return f"{class_name(cls)}은(는) {rep}번({class_name(rep)})으로 지정하세요."
    return f"{class_name(cls)}은(는) 지정할 수 없습니다. 판단이 어려우면 이슈 노트에 기록해 주세요."


# ── 박스 목록 검사 ──
def is_locked_box(b):
    """지정 불가 클래스 박스인지 (클래스 미지정·예전 이슈 박스는 제외)"""
    return b["cls"] is not None and b["cls"] != ISSUE_ID and not is_selectable(b["cls"])


def locked_boxes(boxes):
    return [b for b in boxes if is_locked_box(b)]


def describe_locked(boxes):
    """지정 불가 박스 요약 — 예) ['4: 고무장갑 2개 → 1번(플라스틱·돌·금속류)으로 변경', '9 1개 → 삭제']"""
    counts = {}
    for b in locked_boxes(boxes):
        counts[b["cls"]] = counts.get(b["cls"], 0) + 1
    lines = []
    for cls, n in sorted(counts.items()):
        rep = replacement(cls)
        action = f"{rep}번({class_name(rep)})으로 변경" if rep is not None else "삭제"
        lines.append(f"{cls}: {class_name(cls)} {n}개 → {action}")
    return lines


def apply_locked(boxes):
    """지정 불가 박스를 규칙대로 처리 (대체 번호가 있으면 변경, 없으면 삭제). boxes 를 직접 고침
       반환: (변경 수, 삭제 수)"""
    changed = removed = 0
    keep = []
    for b in boxes:
        if is_locked_box(b):
            rep = replacement(b["cls"])
            if rep is None:
                removed += 1
                continue
            b["cls"] = rep
            b["auto"] = False
            changed += 1
        keep.append(b)
    boxes[:] = keep
    return changed, removed


def auto_label_class(cls):
    """자동 라벨링 결과 번호 → 사용할 번호 (버릴 때는 None)"""
    pol = auto_label_policy(cls)
    if pol == "drop":
        return None
    if pol == "replace":
        return replacement(cls)
    return cls


check_class_table()        # import 될 때 표를 검사 → 잘못되면 프로그램 시작 시 바로 오류
