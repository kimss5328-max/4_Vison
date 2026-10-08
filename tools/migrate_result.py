"""결과 폴더 옮기기 — 원본 구조 없이 작업한 결과(예: data/raw_result)를 원래 데이터셋 결과로 옮김

   예) data/raw_result/work/review/img/a.jpg
       → data/dataset1_result/work/review/img/train/a.jpg
       (a.jpg 가 원본 '이물검출_학습데이터1/images/train/' 에 있을 때)

   - 파일 이름으로 원본 폴더를 찾아 데이터셋·train/validation 을 정함
   - 단계 img·txt, review preview, working, issues(사본·이슈 기록), 이미지별 이력 csv 모두 옮김
     (이력 csv 의 image 열도 'train/a.jpg' 로 고침)
   - manifest 의 해당 행: source_dataset·original_split 을 고침
   - 원본(images·labels)과 옮기기 전 결과 폴더는 건드리지 않음 (복사) → 확인 후 직접 삭제
   - 기본은 미리보기(아무것도 안 바꿈). --apply 를 붙여야 실제로 복사·수정

   사용법 (프로그램 폴더에서):
     python3 tools/migrate_result.py --src raw --origin ~/exe_01/원본폴더            # 미리보기
     python3 tools/migrate_result.py --src raw --origin ~/exe_01/원본폴더 --apply    # 실제 적용
   --origin : 원본 데이터셋 폴더(images·labels 가 있는 폴더) 또는 그 상위 폴더. 여러 번 써도 됨"""
import argparse
import csv
import filecmp
import io
import os
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.config import (RESULT_DIR, RESULT_SUFFIX, IMG_SUB, TXT_SUB, PREVIEW_SUB, STAGE_DIRS,   # noqa: E402
                        PREVIEW_STAGES, WORKING_DIR, ISSUES_DIR, CSV_DIR, IMG_EXTS,
                        DATASET_NAMES, MANIFEST_DIR, MANIFEST_FILE, MANIFEST_HEADER)
from src.bbox import manifest                                                                 # noqa: E402

ISSUE_TAIL = "_issue"
REPORT_DIR = "reports"


# ── 결과 폴더 안의 묶음 (결과 폴더 기준 경로) ──
def groups():
    """(경로 튜플, 종류) — 종류: img / txt / csv. 긴 경로부터 (preview 가 img 보다 먼저 맞도록)"""
    g = []
    for loc in list(STAGE_DIRS.values()) + [ISSUES_DIR]:
        g += [(loc + (IMG_SUB,), "img"), (loc + (TXT_SUB,), "txt")]
    g += [(STAGE_DIRS[st] + (PREVIEW_SUB,), "img") for st in PREVIEW_STAGES]
    g += [(WORKING_DIR + (TXT_SUB,), "txt"), (CSV_DIR, "csv")]
    return sorted(g, key=lambda x: -len(x[0]))


# ── 원본 색인: 파일 이름(확장자 뺀 것) → 데이터셋·split ──
SKIP_TAILS = ("_labeled", "_done", RESULT_SUFFIX)    # 예전 버전·프로그램이 만든 결과 폴더는 원본으로 보지 않음
MAX_DEPTH = 3


def dataset_dirs(origin):
    """origin 과 그 아래(최대 3단계)에서 데이터셋 폴더 찾기
       — 이름이 config.DATASET_NAMES 에 있고 images 폴더가 있는 것만 (예: 이물검출_학습데이터1)"""
    origin = os.path.abspath(os.path.expanduser(origin))
    found = []
    base_depth = origin.rstrip(os.sep).count(os.sep)
    for cur, dirs, _ in os.walk(origin):
        dirs[:] = sorted(d for d in dirs if not d.endswith(SKIP_TAILS))
        if os.path.basename(cur) in DATASET_NAMES and os.path.isdir(os.path.join(cur, "images")):
            found.append(cur)
            dirs[:] = []                                 # 데이터셋 안쪽은 더 찾지 않음
        elif cur.count(os.sep) - base_depth >= MAX_DEPTH:
            dirs[:] = []
    return found


def build_index(origins):
    """→ (색인 {stem: info}, 중복 {stem: [경로...]}, 데이터셋 폴더 목록)
       info = {"dataset": dataset1, "rel_dir": 'train', "split": 'train', "file": 'a.jpg'}"""
    index, dup, found = {}, {}, []
    for origin in origins:
        for ds_dir in dataset_dirs(origin):
            folder = os.path.basename(ds_dir)
            found.append(ds_dir)
            img_base = os.path.join(ds_dir, "images")
            for cur, dirs, files in os.walk(img_base):
                dirs[:] = [d for d in dirs if not d.endswith(SKIP_TAILS)]
                for f in files:
                    if not f.lower().endswith(IMG_EXTS):
                        continue
                    full = os.path.join(cur, f)
                    stem = os.path.splitext(f)[0]
                    info = {"dataset": DATASET_NAMES.get(folder, folder),
                            "rel_dir": os.path.relpath(cur, img_base),
                            "split": manifest.split_of(full), "file": f, "path": full}
                    if stem in index:
                        dup.setdefault(stem, [index[stem]["path"]]).append(full)
                    else:
                        index[stem] = info
    for stem in dup:
        index.pop(stem, None)
    return index, dup, found


# ── 옮길 목록 만들기 ──
def plan(src_dir, index):
    """→ (작업 목록 [(원래 경로, 새 경로, 종류, info)], 못 찾음 [경로], 다른 내용이 이미 있음 [(원래, 새)],
          이미 옮김 [경로])"""
    jobs, missing, exists, done = [], [], [], []
    data_dir = os.path.dirname(src_dir)
    gs = groups()
    for cur, _, files in os.walk(src_dir):
        for f in files:
            if f in (".gitkeep", "classes.txt"):
                continue
            full = os.path.join(cur, f)
            rel = os.path.relpath(full, src_dir).split(os.sep)
            hit = next(((loc, kind) for loc, kind in gs if tuple(rel[:len(loc)]) == loc), None)
            if not hit:
                missing.append(full)            # 결과 구조 밖의 파일
                continue
            loc, kind = hit
            stem = os.path.splitext(f)[0]
            if kind == "txt" and stem.endswith(ISSUE_TAIL) and loc[:len(ISSUES_DIR)] == ISSUES_DIR:
                stem = stem[:-len(ISSUE_TAIL)]
            info = index.get(stem)
            if not info:
                missing.append(full)
                continue
            new_dir = os.path.join(data_dir, info["dataset"] + RESULT_SUFFIX, *loc)
            new = os.path.normpath(os.path.join(new_dir, info["rel_dir"], f))
            if os.path.exists(new):
                if same(full, new, kind, info):
                    done.append(full)           # 이미 옮겨 둔 것 (다시 실행한 경우)
                else:
                    exists.append((full, new))
                continue
            jobs.append((full, new, kind, info))
    return jobs, missing, exists, done


# ── 적용 ──
def csv_text(old, info):
    """이력 csv 를 옮긴 뒤의 내용 — image 열을 'train/a.jpg' 로"""
    new_rel = os.path.normpath(os.path.join(info["rel_dir"], info["file"]))
    with open(old, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for r in rows:
        if "image" in r:
            r["image"] = new_rel
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def same(old, new, kind, info):
    """옮길 곳의 파일이 옮긴 결과와 같은지"""
    if kind != "csv":
        return filecmp.cmp(old, new, shallow=False)
    with open(new, encoding="utf-8-sig", newline="") as f:
        return f.read() == csv_text(old, info)


def copy_job(old, new, kind, info):
    os.makedirs(os.path.dirname(new), exist_ok=True)
    if kind != "csv":
        shutil.copy2(old, new)
        return
    with open(new, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_text(old, info))


def fix_manifest(src_name, index, apply):
    """manifest 에서 source_dataset == src_name 인 행 → 원래 데이터셋·split 으로. → (고친 수, 충돌 목록)"""
    path = os.path.join(BASE, MANIFEST_DIR, MANIFEST_FILE)
    if not os.path.exists(path):
        return 0, []
    rows = manifest.read_rows(path)
    keys = {(r["source_dataset"], r["original_split"], r["file_name"]) for r in rows}
    changed, conflict, out = 0, [], []
    for r in rows:
        if r["source_dataset"] == src_name:
            info = index.get(os.path.splitext(r["file_name"])[0])
            if info:
                key = (info["dataset"], info["split"], r["file_name"])
                if key in keys:                      # 이미 정상 행이 있음 → 그대로 두고 보고
                    conflict.append(r["file_name"])
                else:
                    r = dict(r, source_dataset=info["dataset"], original_split=info["split"])
                    keys.add(key)
                    changed += 1
        out.append(r)
    if apply and changed:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_HEADER)
            w.writeheader()
            w.writerows({c: r.get(c, "") for c in MANIFEST_HEADER} for r in out)
        os.replace(tmp, path)
    return changed, conflict


def main():
    ap = argparse.ArgumentParser(description="결과 폴더를 원래 데이터셋 구조로 옮김")
    ap.add_argument("--src", required=True, help="옮길 결과 이름 (예: raw → data/raw_result)")
    ap.add_argument("--origin", required=True, action="append", help="원본 데이터셋 폴더 또는 상위 폴더")
    ap.add_argument("--apply", action="store_true", help="실제로 복사·수정 (없으면 미리보기)")
    a = ap.parse_args()

    src_dir = os.path.join(BASE, RESULT_DIR, a.src + RESULT_SUFFIX)
    if not os.path.isdir(src_dir):
        sys.exit(f"결과 폴더가 없습니다: {src_dir}")
    index, dup, found = build_index(a.origin)
    if not found:
        sys.exit("원본 데이터셋 폴더를 찾지 못했습니다: " + ", ".join(a.origin)
                 + "\n  찾는 이름: " + ", ".join(DATASET_NAMES) + " (안에 images 폴더가 있어야 함)")

    jobs, missing, exists, done = plan(src_dir, index)
    if a.apply:
        for old, new, kind, info in jobs:
            copy_job(old, new, kind, info)
    m_changed, m_conflict = fix_manifest(a.src, index, a.apply)

    # 보고
    mode = "적용" if a.apply else "미리보기 (바뀐 것 없음 — 확인 후 --apply)"
    by = {}
    for old, new, kind, info in jobs:
        k = (info["dataset"], info["split"] or "(빈칸)", kind)
        by[k] = by.get(k, 0) + 1
    lines = [f"# 결과 폴더 옮기기 — {mode}", "",
             f"- 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
             f"- 옮길 결과: {os.path.relpath(src_dir, BASE)}",
             "- 원본: " + ", ".join(os.path.basename(d) for d in found) + f" (이미지 {len(index)}장 색인)",
             "", "## 옮길 파일", "", "| 데이터셋 | split | 종류 | 수 |", "|---|---|---|---|"]
    lines += [f"| {d} | {s} | {k} | {n} |" for (d, s, k), n in sorted(by.items())]
    lines += ["", f"합계 {len(jobs)}개" + (f" (이미 옮겨 둔 파일 {len(done)}개는 건너뜀)" if done else ""), "",
              "## manifest", "", f"- 고칠 행: {m_changed}",
              f"- 이미 정상 행이 있어 그대로 둔 행: {len(m_conflict)}"]
    lines += [f"  - {n}" for n in m_conflict]
    lines += ["", "## 확인 필요", "",
              f"- 원본에서 찾지 못한 파일 (안 옮김): {len(missing)}"]
    lines += [f"  - {os.path.relpath(p, BASE)}" for p in missing]
    lines += [f"- 옮길 곳에 다른 내용의 파일이 이미 있음 (안 옮김): {len(exists)}"]
    lines += [f"  - {os.path.relpath(o, BASE)} → {os.path.relpath(n, BASE)}" for o, n in exists]
    lines += [f"- 원본에 같은 이름이 여러 개 (안 옮김): {len(dup)}"]
    lines += [f"  - {s}: " + " / ".join(ps) for s, ps in dup.items()]
    if a.apply:
        lines += ["", f"옮기기 전 폴더 {os.path.relpath(src_dir, BASE)} 는 그대로 있습니다. "
                      "프로그램에서 원본을 열어 확인한 뒤 직접 지우세요."]
    text = "\n".join(lines) + "\n"
    print(text)
    os.makedirs(os.path.join(BASE, REPORT_DIR), exist_ok=True)
    rp = os.path.join(BASE, REPORT_DIR, f"migrate_{a.src}_{datetime.now():%Y%m%d_%H%M%S}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"보고서: {os.path.relpath(rp, BASE)}")


if __name__ == "__main__":
    main()
