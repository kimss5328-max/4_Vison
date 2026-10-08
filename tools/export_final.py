"""FINAL 모으기 — 데이터셋별 final 결과를 학습용 폴더 하나(visol04/total_final_data)로 모음

   data/dataset1_result/final/img/train/a.jpg   ┐      total_final_data/images/train/a.jpg
   data/dataset1_result/final/txt/train/a.txt   │  →   total_final_data/labels/train/a.txt
   data/dataset2_result/final/img/validation/…  ┘      total_final_data/images/validation/…
                                                       + data.yaml (YOLO 학습 설정), classes.txt,
                                                         final_index.csv (파일 → 데이터셋·split)

   - train / validation 구조는 원본 그대로 유지 (교과 8 에서 바로 학습 가능)
   - 이미 있는 파일은 건너뛰고, 새로 final 이 된 것만 추가 · 내용이 바뀐 것은 갱신
   - final 에서 빠진 이미지(view 로 돌려보냄 등)는 total_final_data 에서도 지움 (final 과 항상 같게)
   - 같은 split 에 같은 파일 이름이 두 데이터셋에 있으면 둘 다 넣지 않고 보고
   - 기본은 미리보기(아무것도 안 바꿈). --apply 를 붙여야 실제로 복사

   사용법 (프로그램 폴더에서):
     python3 tools/export_final.py            # 미리보기
     python3 tools/export_final.py --apply    # 실제 적용"""
import argparse
import csv
import filecmp
import os
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.config import (RESULT_DIR, RESULT_SUFFIX, IMG_SUB, TXT_SUB, STAGE_DIRS, IMG_EXTS,   # noqa: E402
                        CLASS_NAMES)

OUT_DIR = "total_final_data"
REPORT_DIR = "reports"
TARGET = 900                                   # 전체 이미지 수 (수행가이드)
NOT_FINAL = [st for st in STAGE_DIRS if st != "final"]


def result_dirs():
    """data/ 아래의 <데이터셋>_result 폴더 → [(데이터셋 이름, 경로)] (raw_result 는 제외: migrate 먼저)"""
    d = os.path.join(BASE, RESULT_DIR)
    out = []
    for n in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        p = os.path.join(d, n)
        if os.path.isdir(p) and n.endswith(RESULT_SUFFIX):
            out.append((n[:-len(RESULT_SUFFIX)], p))
    return out


def count_images(root):
    n = 0
    for _, _, files in os.walk(root):
        n += sum(f.lower().endswith(IMG_EXTS) for f in files)
    return n


def collect(skip_raw):
    """→ (final 목록 {rel: [항목...]}, 데이터셋별 진행 수, 경고)
       rel = 'train/a.jpg' (images 아래 경로), 항목 = {dataset, img, txt}"""
    finals, progress, warn = {}, {}, []
    for ds, rd in result_dirs():
        if ds == "raw" and skip_raw:
            n = count_images(os.path.join(rd, *STAGE_DIRS["final"], IMG_SUB))
            if n:
                warn.append(f"raw_result 에 final {n}장 — migrate_result.py 로 먼저 옮기세요 (이번에는 제외)")
            continue
        img_root = os.path.join(rd, *STAGE_DIRS["final"], IMG_SUB)
        txt_root = os.path.join(rd, *STAGE_DIRS["final"], TXT_SUB)
        n_final = 0
        for cur, _, files in os.walk(img_root):
            for f in files:
                if not f.lower().endswith(IMG_EXTS):
                    continue
                img = os.path.join(cur, f)
                rel = os.path.relpath(img, img_root)
                txt = os.path.join(txt_root, os.path.splitext(rel)[0] + ".txt")
                finals.setdefault(rel, []).append({"dataset": ds, "img": img,
                                                   "txt": txt if os.path.exists(txt) else None})
                n_final += 1
        rest = sum(count_images(os.path.join(rd, *STAGE_DIRS[st], IMG_SUB)) for st in NOT_FINAL)
        progress[ds] = (n_final, rest)
    return finals, progress, warn


def plan(finals, out):
    """→ 할 일 dict: add / update / same / remove / dup / no_txt / empty"""
    todo = {k: [] for k in ("add", "update", "same", "remove", "dup", "no_txt", "empty")}
    keep = set()
    for rel, items in sorted(finals.items()):
        if len(items) > 1:                                  # 같은 split·이름이 두 데이터셋에
            todo["dup"].append((rel, [it["dataset"] for it in items]))
            continue
        it = items[0]
        if not it["txt"]:
            todo["no_txt"].append((rel, it["dataset"]))
            continue
        if os.path.getsize(it["txt"]) == 0:
            todo["empty"].append(rel)
        stem = os.path.splitext(rel)[0]
        dst_img = os.path.join(out, "images", rel)
        dst_txt = os.path.join(out, "labels", stem + ".txt")
        keep.update({os.path.normpath(dst_img), os.path.normpath(dst_txt)})
        pair = (it, rel, dst_img, dst_txt)
        if not (os.path.exists(dst_img) and os.path.exists(dst_txt)):
            todo["add"].append(pair)
        elif filecmp.cmp(it["img"], dst_img, shallow=False) and filecmp.cmp(it["txt"], dst_txt, shallow=False):
            todo["same"].append(pair)
        else:
            todo["update"].append(pair)
    # final 에서 빠진 것 (예전에 모았던 파일)
    for sub in ("images", "labels"):
        root = os.path.join(out, sub)
        for cur, _, files in os.walk(root):
            for f in files:
                p = os.path.normpath(os.path.join(cur, f))
                if p not in keep:
                    todo["remove"].append(p)
    return todo


def write_extras(out, finals, todo):
    """data.yaml · classes.txt · final_index.csv — 매번 새로"""
    splits = sorted({rel.split(os.sep)[0] for rel in finals if os.sep in rel})
    train = "train" if "train" in splits else (splits[0] if splits else "train")
    val = "validation" if "validation" in splits else train
    with open(os.path.join(out, "data.yaml"), "w", encoding="utf-8") as f:
        f.write(f"# YOLO 학습 설정 — export_final.py 가 {datetime.now():%Y-%m-%d %H:%M} 에 만듦\n")
        f.write(f"path: {os.path.abspath(out)}\n")
        f.write(f"train: images/{train}\nval: images/{val}\n")
        f.write(f"nc: {len(CLASS_NAMES)}\nnames:\n")
        for i, n in enumerate(CLASS_NAMES):
            f.write(f"  {i}: {n}\n")
    with open(os.path.join(out, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(CLASS_NAMES) + "\n")
    with open(os.path.join(out, "final_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "source_dataset", "original_split", "boxes"])
        for it, rel, _, dst_txt in sorted(todo["add"] + todo["update"] + todo["same"], key=lambda x: x[1]):
            with open(dst_txt, encoding="utf-8") as t:
                boxes = sum(1 for line in t if line.strip())
            w.writerow([os.path.basename(rel), it["dataset"],
                        rel.split(os.sep)[0] if os.sep in rel else "", boxes])


def main():
    ap = argparse.ArgumentParser(description="데이터셋별 final 을 total_final_data 로 모음")
    ap.add_argument("--apply", action="store_true", help="실제로 복사 (없으면 미리보기)")
    a = ap.parse_args()

    out = os.path.join(BASE, OUT_DIR)
    finals, progress, warn = collect(skip_raw=True)
    todo = plan(finals, out)

    if a.apply:
        for it, rel, dst_img, dst_txt in todo["add"] + todo["update"]:
            os.makedirs(os.path.dirname(dst_img), exist_ok=True)
            os.makedirs(os.path.dirname(dst_txt), exist_ok=True)
            shutil.copy2(it["img"], dst_img)
            shutil.copy2(it["txt"], dst_txt)
        for p in todo["remove"]:
            os.remove(p)
        os.makedirs(out, exist_ok=True)
        write_extras(out, finals, todo)

    total = len(todo["add"]) + len(todo["update"]) + len(todo["same"])
    by = {}
    for it, rel, _, _ in todo["add"] + todo["update"] + todo["same"]:
        k = (it["dataset"], rel.split(os.sep)[0] if os.sep in rel else "(없음)")
        by[k] = by.get(k, 0) + 1
    mode = "적용" if a.apply else "미리보기 (바뀐 것 없음 — 확인 후 --apply)"
    lines = [f"# FINAL 모으기 — {mode}", "",
             f"- 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
             f"- 모을 곳: {OUT_DIR}/ (images·labels 아래 train/validation 유지)", "",
             "## 진행 현황", "", "| 데이터셋 | final | 아직 final 아님 (pass·edited·review·view) |", "|---|---|---|"]
    lines += [f"| {ds} | {nf} | {rest} |" for ds, (nf, rest) in progress.items()]
    lines += ["", f"- total_final_data 에 들어갈 이미지: **{total}장** / 목표 {TARGET}장 (남은 {max(TARGET - total, 0)}장)",
              "", "## 데이터셋 · split 별", "", "| 데이터셋 | split | 수 |", "|---|---|---|"]
    lines += [f"| {d} | {s} | {n} |" for (d, s), n in sorted(by.items())]
    lines += ["", "## 이번에 바뀌는 것", "",
              f"- 새로 추가: {len(todo['add'])}",
              f"- 내용이 바뀌어 갱신: {len(todo['update'])}",
              f"- 그대로 (이미 있음): {len(todo['same'])}",
              f"- final 에서 빠져 지움: {len(todo['remove'])}"]
    lines += [f"  - {os.path.relpath(p, BASE)}" for p in todo["remove"]]
    lines += ["", "## 확인 필요", "",
              f"- 같은 split 에 같은 파일 이름 (두 데이터셋, 안 넣음): {len(todo['dup'])}"]
    lines += [f"  - {rel}: {' / '.join(ds)}" for rel, ds in todo["dup"]]
    lines += [f"- final 이미지인데 라벨 txt 없음 (안 넣음): {len(todo['no_txt'])}"]
    lines += [f"  - {ds}: {rel}" for rel, ds in todo["no_txt"]]
    lines += [f"- 빈 라벨 (박스 0개 — 정상 김치인지 확인): {len(todo['empty'])}"]
    lines += [f"- {w}" for w in warn]
    text = "\n".join(lines) + "\n"
    print(text)
    os.makedirs(os.path.join(BASE, REPORT_DIR), exist_ok=True)
    rp = os.path.join(BASE, REPORT_DIR, f"export_final_{datetime.now():%Y%m%d_%H%M%S}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"보고서: {os.path.relpath(rp, BASE)}")


if __name__ == "__main__":
    main()
