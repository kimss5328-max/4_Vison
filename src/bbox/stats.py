"""작업 결과 통계 — 이미지별 정보 목록을 받아 개수·비율을 계산 (화면·파일과 무관한 계산만)
   이미지 1장 정보(entry): {"stage": '' 또는 단계, "classes": [클래스 번호, ...],
                            "scene": scene_type 또는 '', "issue": 이슈 기록 여부}"""
from src.config import STATS_STAGES, SCENE_TYPES
from src.validation.rules import class_ids, class_name


def pct(n, total):
    return n / total * 100 if total else 0.0


def summarize(entries):
    """→ 통계 dict
       stages : [(이름, 개수, 색)]           — STATS_STAGES 순서
       scenes : [(기록값, 설명, 개수)] + 미지정
       classes: [(번호, 이름, 박스 수)]      — 정의된 모든 클래스 (숨김 포함)
       total, boxes, empty, issues, class4 등 품질 지표"""
    total = len(entries)
    stage_n = {key: 0 for key, _, _ in STATS_STAGES}
    scene_n = {key: 0 for key, _ in SCENE_TYPES}
    no_scene = 0
    class_n = {cid: 0 for cid in class_ids()}
    unknown_cls = 0
    boxes = empty = issues = 0
    for e in entries:
        stage_n[e["stage"] if e["stage"] in stage_n else ""] += 1
        if e["scene"] in scene_n:
            scene_n[e["scene"]] += 1
        else:
            no_scene += 1
        boxes += len(e["classes"])
        empty += not e["classes"]
        issues += bool(e["issue"])
        for c in e["classes"]:
            if c in class_n:
                class_n[c] += 1
            else:
                unknown_cls += 1
    return {
        "total": total,
        "stages": [(name, stage_n[key], color) for key, name, color in STATS_STAGES],
        "scenes": [(key, desc, scene_n[key]) for key, desc in SCENE_TYPES],
        "no_scene": no_scene,
        "classes": [(cid, class_name(cid), class_n[cid]) for cid in class_ids()],
        "unknown_cls": unknown_cls,
        "boxes": boxes,
        "empty": empty,
        "issues": issues,
        "avg_boxes": boxes / total if total else 0.0,
    }


def table_rows(s):
    """데이터 품질 지표 표 — [(항목, 값, 비율 문자열)]"""
    t = s["total"]
    rows = [("전체 이미지 수", t, "100%" if t else "-")]
    rows += [(f"{name}", n, f"{pct(n, t):.1f}%") for name, n, _ in s["stages"]]
    rows += [("이슈 기록 이미지", s["issues"], f"{pct(s['issues'], t):.1f}%"),
             ("빈 라벨 (박스 0개)", s["empty"], f"{pct(s['empty'], t):.1f}%"),
             ("Scene Type 미지정", s["no_scene"], f"{pct(s['no_scene'], t):.1f}%"),
             ("전체 BBox 수", s["boxes"], "-"),
             ("평균 BBox 개수", f"{s['avg_boxes']:.2f}", "-")]
    if s["unknown_cls"]:
        rows.append(("정의 없는 클래스 BBox", s["unknown_cls"], "-"))
    return rows


def stage_table_rows(s):
    """통계 화면 표 — 전체 이미지 수 + 작업 상태(미작업 ~ final)까지만"""
    t = s["total"]
    return ([("전체 이미지 수", t, "100%" if t else "-")]
            + [(name, n, f"{pct(n, t):.1f}%") for name, n, _ in s["stages"]])


def csv_rows(s, scope):
    """[CSV 저장] 내용 — [구분, 항목, 값, 비율]"""
    t, b = s["total"], s["boxes"]
    rows = [["범위", "선택한 영역", " / ".join(scope), ""]]
    rows += [["작업 상태", name, n, f"{pct(n, t):.1f}%"] for name, n, _ in s["stages"]]
    rows += [["Scene Type", key, n, f"{pct(n, t):.1f}%"] for key, _, n in s["scenes"]]
    rows.append(["Scene Type", "(미지정)", s["no_scene"], f"{pct(s['no_scene'], t):.1f}%"])
    rows += [["Class", f"{cid}: {name}", n, f"{pct(n, b):.1f}%"] for cid, name, n in s["classes"]]
    rows += [["품질 지표", item, val, ratio] for item, val, ratio in table_rows(s)]
    return rows
