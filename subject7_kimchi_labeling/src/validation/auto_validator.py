"""자동 validation — 폴더를 열 때 원본 이미지·라벨 쌍을 기계적으로 검사 (원작: feature/KJH)
   - 쌍 맞추기는 프로그램과 같은 방식(상대 경로 → 파일명 순)으로 앱이 만들어 넘겨준다
     → 다른 폴더에 같은 이름 파일이 있어도 엉뚱한 짝을 검사하지 않음
   - 클래스 판정은 rules.py(= config.CLASSES 표)를 따른다
       표에 없는 번호 → ERROR / 지정 불가 클래스(예: 4 고무장갑) → REVIEW (대체 번호 안내)
   - 이 파일은 tkinter 를 쓰지 않는다 (백그라운드 스레드에서 실행해도 안전)
     결과 팝업·상태 표시는 folder_mixin 이 메인 스레드에서 처리
   - 상세 결과: reports/validation_report.csv (추가만, Git 에 올리지 않음)
     이상이 없어도 'OK' 1줄을 남겨 검사한 기록이 남게 함"""
import csv
import os
from datetime import datetime

from PIL import Image

from src.config import BASE_DIR
from src.validation.rules import is_known, is_selectable, class_name, replacement

REPORT_DIR = os.path.join(BASE_DIR, "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "validation_report.csv")
REPORT_HEADER = ["checked_at", "project", "file", "level", "check", "detail"]
LEVELS = ("ERROR", "WARNING", "REVIEW")
OK_LEVEL = "OK"


# ── 검사 함수 (각각 (level, check, detail) 리스트 반환) ──
def check_image(img_path):
    try:
        with Image.open(img_path) as im:
            w, h = im.size
        if w <= 0 or h <= 0:
            return [("ERROR", "IMG_SIZE", f"이미지 크기 이상: {w}×{h}")]
    except Exception as e:
        return [("ERROR", "IMG_OPEN", f"이미지 열기 실패: {e}")]
    return []


def check_class(ln, cid):
    if not is_known(cid):
        return [("ERROR", "CLASS_ID", f"라인 {ln}: 정의 없는 클래스 번호 {cid}")]
    if not is_selectable(cid):
        rep = replacement(cid)
        guide = f" → {rep}번({class_name(rep)})으로 변경 필요" if rep is not None else ""
        return [("REVIEW", "CLASS_LOCKED",
                 f"라인 {ln}: {cid}번({class_name(cid)})은 지정 불가 클래스{guide}")]
    return []


def check_label(label_path):
    """라벨 파일 검사 — YOLO txt(공백) / 쉼표 5칸 csv 모두 (프로그램이 읽는 방식과 같음)"""
    try:
        with open(label_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return [("ERROR", "TXT_OPEN", f"라벨 읽기 실패: {e}")]

    issues = []
    for ln, line in enumerate(lines, 1):
        text = line.strip()
        if not text:
            continue                      # 빈 줄 / 빈 파일 = 이물 없는 이미지 (정상)
        parts = text.replace(",", " ").split()
        if len(parts) != 5:
            issues.append(("ERROR", "FORMAT", f"라인 {ln}: 값이 {len(parts)}개 (5개여야 함) → '{text}'"))
            continue
        try:
            cid = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:])
        except ValueError:
            issues.append(("ERROR", "PARSE", f"라인 {ln}: 숫자 변환 실패 → '{text}'"))
            continue
        issues += check_class(ln, cid)
        if not all(0.0 <= v <= 1.0 for v in (xc, yc, bw, bh)):
            issues.append(("ERROR", "COORD_RANGE",
                           f"라인 {ln}: 좌표 범위(0~1) 초과 → xc={xc}, yc={yc}, w={bw}, h={bh}"))
        if bw <= 0 or bh <= 0:
            issues.append(("ERROR", "COORD_SIZE", f"라인 {ln}: w·h 는 0보다 커야 함 → w={bw}, h={bh}"))
    return issues


# ── 메인 ──
def run_validation(job):
    """job = {"project": 이름, "pairs": [(표시명, 이미지 경로, 라벨 경로 또는 None)],
              "orphans": [(표시명, 짝 이미지가 없는 라벨 경로)]}
       → 이슈 dict 리스트 (빈 리스트면 이상 없음). 이슈가 있으면 리포트 csv 에 추가"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    issues = []

    def add(name, found):
        for level, check, detail in found:
            issues.append({"checked_at": now, "project": job["project"], "file": name,
                           "level": level, "check": check, "detail": detail})

    for name, img_path, label_path in job["pairs"]:
        if label_path is None:
            add(name, [("WARNING", "TXT_MISSING", "이미지만 있고 라벨이 없음 (빈 라벨로 시작)")])
            add(name, check_image(img_path))
            continue
        add(name, check_image(img_path))
        add(name, check_label(label_path))
    for name, label_path in job["orphans"]:
        add(name, [("ERROR", "IMG_MISSING", f"라벨만 있고 이미지가 없음: {label_path}")])

    n = len(job["pairs"])
    write_report(issues or [{"checked_at": now, "project": job["project"], "file": "-",
                             "level": OK_LEVEL, "check": "NO_ISSUE",
                             "detail": f"이상 없음 (이미지 {n}장)"}])
    return issues


def write_report(issues):
    os.makedirs(REPORT_DIR, exist_ok=True)
    new = not os.path.exists(REPORT_FILE)
    with open(REPORT_FILE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_HEADER)
        if new:
            w.writeheader()
        w.writerows(issues)


def summarize(results, total):
    """results: {프로젝트명: 이슈 리스트} → (팝업 문구, 상태 표시줄 문구, 이상 없음 여부)"""
    all_issues = [i for lst in results.values() for i in lst]
    count = {lv: sum(1 for i in all_issues if i["level"] == lv) for lv in LEVELS}
    status = (f"자동 검사 완료: 이미지 {total}장 — "
              f"ERROR {count['ERROR']} / WARNING {count['WARNING']} / REVIEW {count['REVIEW']}")
    if not all_issues:
        names = ", ".join(results)
        return (f"자동 검사 완료 — 이상 없음\n\n대상: {names}\n이미지 {total}장\n\n"
                f"상세: {os.path.relpath(REPORT_FILE, BASE_DIR)}"), status + " (이상 없음)", True
    lines = [f"자동 검사 결과 (이미지 {total}장)", "",
             f"  ERROR   : {count['ERROR']:4}건",
             f"  WARNING : {count['WARNING']:4}건",
             f"  REVIEW  : {count['REVIEW']:4}건  (지정 불가 클래스 등 확인 필요)", ""]
    for lv in ("ERROR", "REVIEW"):
        top = [i for i in all_issues if i["level"] == lv][:5]
        if top:
            lines.append(f"주요 {lv} (최대 5건):")
            lines += [f"  {i['file']} → {i['detail']}" for i in top]
            lines.append("")
    lines += ["작업은 계속할 수 있습니다. 해당 이미지를 열어 수정 후 저장하세요.",
              f"상세: {os.path.relpath(REPORT_FILE, BASE_DIR)}"]
    return "\n".join(lines), status, False


def print_console(results):
    for project, lst in results.items():
        print(f"\n{'=' * 60}\n [자동 검사] {project}: {len(lst)}건\n{'=' * 60}")
        for i in lst:
            print(f" [{i['level']:7}] {i['file']}  {i['check']}: {i['detail']}")
