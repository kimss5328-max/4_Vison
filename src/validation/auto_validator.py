"""src/validation/auto_validator.py

폴더를 열 때 자동으로 원본 이미지·TXT 쌍을 기계적으로 검사합니다.
  - 결과는 tkinter 팝업(요약) + 콘솔 출력(상세) + reports/validation_report.csv 저장
  - 오류가 있어도 프로그램은 계속 동작합니다 (로딩을 막지 않음)
  - 수정이 필요한 파일은 프로그램에서 편집하고 재저장하면 됩니다
"""

import csv
import os
from datetime import datetime
from tkinter import messagebox

from PIL import Image

from src.config import (BASE_DIR, CLASS_IDS, UNUSED_CLASS, IMG_EXTS)

# 허용 클래스: 0~6에서 사용 안 하는 4번 제외
ALLOWED_IDS = set(CLASS_IDS)          # {0,1,2,3,5,6}
C4_ID = UNUSED_CLASS                   # 4 (이제 경고가 아닌 ERROR 처리)

REPORT_DIR = os.path.join(BASE_DIR, "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "validation_report.csv")

REPORT_HEADER = ["checked_at", "img_root", "file", "level",
                 "check", "detail"]

# ── 검사 함수들 (각각 (level, check, detail) 리스트 반환) ──

def _check_pair(stem, img_map, txt_map):
    issues = []
    has_img = stem in img_map
    has_txt = stem in txt_map
    
    # 모두 ERROR로 통일
    if has_img and not has_txt:
        issues.append(("ERROR", "TXT_MISSING",
                        f"이미지만 있고 TXT가 없음: {img_map[stem]}"))
    elif has_txt and not has_img:
        issues.append(("ERROR", "IMG_MISSING",
                        f"TXT만 있고 이미지가 없음: {txt_map[stem]}"))
    return issues


def _check_image(img_path):
    issues = []
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            if w <= 0 or h <= 0:
                issues.append(("ERROR", "IMG_SIZE",
                                f"이미지 크기 이상: {w}×{h}"))
    except Exception as e:
        issues.append(("ERROR", "IMG_OPEN",
                        f"이미지 열기 실패: {e}"))
    return issues


def _check_txt(txt_path, img_path):
    issues = []
    basename = os.path.splitext(os.path.basename(txt_path))[0]
    img_basename = os.path.splitext(os.path.basename(img_path))[0] if img_path else None

    # 파일 기본명 일치 확인
    if img_basename and basename != img_basename:
        issues.append(("ERROR", "NAME_MISMATCH",
                        f"기본명 불일치: img={img_basename}, txt={basename}"))

    try:
        with open(txt_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        issues.append(("ERROR", "TXT_OPEN", f"TXT 읽기 실패: {e}"))
        return issues

    if not lines or all(l.strip() == "" for l in lines):
        return issues   # Empty TXT = 정상 (이물 없는 이미지)

    for ln, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        parts = stripped.split()

        # 열 개수
        if len(parts) != 5:
            issues.append(("ERROR", "FORMAT",
                            f"라인 {ln}: 열이 {len(parts)}개 (5개여야 함) → '{stripped}'"))
            continue

        # 숫자 파싱
        try:
            cid = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:])
        except ValueError:
            issues.append(("ERROR", "PARSE",
                            f"라인 {ln}: 숫자 변환 실패 → '{stripped}'"))
            continue

        # Class ID
        if cid == C4_ID:
            # 기존 REVIEW -> ERROR로 통일
            issues.append(("ERROR", "CLASS_C4",
                            f"라인 {ln}: Class 4(사용 안 함) → 허용되지 않음"))
        elif cid not in ALLOWED_IDS:
            issues.append(("ERROR", "CLASS_ID",
                            f"라인 {ln}: 허용되지 않는 Class ID={cid} (허용: {sorted(ALLOWED_IDS)})"))

        # 좌표 범위 0~1
        if not all(0.0 <= v <= 1.0 for v in (xc, yc, bw, bh)):
            issues.append(("ERROR", "COORD_RANGE",
                            f"라인 {ln}: 좌표 범위 초과 → xc={xc}, yc={yc}, w={bw}, h={bh}"))

        # 너비·높이 양수
        if bw <= 0 or bh <= 0:
            issues.append(("ERROR", "COORD_SIZE",
                            f"라인 {ln}: w·h는 0보다 커야 함 → w={bw}, h={bh}"))

    return issues


# ── 메인 ──

def run_validation(img_root: str, pj: dict, parent_window=None) -> list:
    """
    img_root 와 그에 대응하는 labels 폴더를 검사합니다.
    반환: 발견된 이슈 dict 리스트 (빈 리스트면 이상 없음)
    """
    img_map = {}   # stem → 절대경로
    txt_map = {}

    for cur, dirs, files in os.walk(img_root):
        dirs[:] = [d for d in dirs
                   if not d.endswith("_done") and d not in ("yolo", "review", "labeled")]
        for f in files:
            if f.lower().endswith(IMG_EXTS):
                stem = os.path.splitext(f)[0]
                img_map[stem] = os.path.join(cur, f)

    lbl_root = os.path.join(pj["proj"], "labels") if pj.get("proj") else None
    if lbl_root and os.path.isdir(lbl_root):
        for cur, dirs, files in os.walk(lbl_root):
            dirs[:] = [d for d in dirs if not d.endswith("_done")]
            for f in files:
                if f.lower().endswith(".txt"):
                    stem = os.path.splitext(f)[0]
                    txt_map[stem] = os.path.join(cur, f)
    else:
        for cur, _, files in os.walk(img_root):
            for f in files:
                if f.lower().endswith(".txt"):
                    stem = os.path.splitext(f)[0]
                    txt_map[stem] = os.path.join(cur, f)

    all_stems = sorted(img_map.keys() | txt_map.keys())
    all_issues = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for stem in all_stems:
        img_path = img_map.get(stem)
        txt_path = txt_map.get(stem)
        fname = f"{stem}.*"

        pair_issues = _check_pair(stem, img_map, txt_map)
        for level, check, detail in pair_issues:
            all_issues.append({"checked_at": now, "img_root": img_root,
                                "file": fname, "level": level,
                                "check": check, "detail": detail})

        if not img_path or not txt_path:
            continue   

        for level, check, detail in _check_image(img_path):
            all_issues.append({"checked_at": now, "img_root": img_root,
                                "file": os.path.basename(img_path),
                                "level": level, "check": check, "detail": detail})

        for level, check, detail in _check_txt(txt_path, img_path):
            all_issues.append({"checked_at": now, "img_root": img_root,
                                "file": os.path.basename(txt_path),
                                "level": level, "check": check, "detail": detail})

    # ── 리포트 CSV 저장 ──
    if all_issues:
        os.makedirs(REPORT_DIR, exist_ok=True)
        write_header = not os.path.exists(REPORT_FILE)
        with open(REPORT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REPORT_HEADER)
            if write_header:
                w.writeheader()
            w.writerows(all_issues)

    # ── 콘솔 출력 (전부 ERROR로 단순화) ──
    print(f"\n{'='*60}")
    print(f" [Validation] {img_root}")
    print(f" 총 이미지: {len(img_map)}  TXT: {len(txt_map)}")
    print(f" 발견된 ERROR 수: {len(all_issues)}건")
    print(f"{'='*60}")
    for i in all_issues:
        print(f" [ERROR  ] {i['file']}  {i['check']}: {i['detail']}")
    if not all_issues:
        print(" 이상 없음 ✓")
    print(f"{'='*60}\n")

    # ── 팝업 (오류가 있을 때만) ──
    if all_issues and parent_window:
        lines = [
            f"Validation 결과 — {os.path.basename(img_root)}",
            "",
            f"🚨 총 {len(all_issues)}건의 데이터 오류가 발견되었습니다.",
            "  (로딩은 정상적으로 진행됩니다)",
            "",
            "주요 오류 내역 (최대 5건):"
        ]
        for i in all_issues[:5]:
            lines.append(f"  - {i['file']} → {i['detail']}")
        
        lines += ["",
                  "상세 내용: reports/validation_report.csv 파일을 확인하세요.",
                  "문제가 있는 파일은 라벨링 프로그램 화면에서 직접 수정해 주세요."]

        messagebox.showerror("Validation 오류 발생", "\n".join(lines),
                               parent=parent_window)

    return all_issues