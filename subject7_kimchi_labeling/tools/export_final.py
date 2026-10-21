"""FINAL 모으기 — 데이터셋별 final 결과를 학습용 폴더 하나(visol04/data/final)로 모음

   data/dataset1_result/final/img/train/a.jpg   ┐      data/final/images/train/a.jpg
   data/dataset1_result/final/txt/train/a.txt   │  →   data/final/labels/train/a.txt
   data/dataset2_result/final/img/validation/…  ┘      data/final/images/validation/…
                                                       + classes.txt,
                                                         final_index.csv (파일 → 데이터셋·split),
                                                         dataset_manifest.csv (합친 manifest 사본)

   - train / validation 구조는 원본 그대로 유지
   - YOLO 학습용 train/val/test 와 dataset.yaml 은 tools/build_split.py 로 만듦
   - 이미 있는 파일은 건너뛰고, 새로 final 이 된 것만 추가 · 내용이 바뀐 것은 갱신
   - final 에서 빠진 이미지(view 로 돌려보냄 등)는 data/final 에서도 지움 (final 과 항상 같게)
   - 같은 split 에 같은 파일 이름이 두 데이터셋에 있으면 둘 다 넣지 않고 보고
   - 기본은 미리보기(아무것도 안 바꿈). --apply 를 붙여야 실제로 복사

   사용법 (프로그램 폴더에서):
     python3 tools/export_final.py                        # 미리보기 (final 만, train/validation 폴더 유지)
     python3 tools/export_final.py --apply                # 실제 적용
     python3 tools/export_final.py --all --flat --apply   # 모든 단계 · data/final/images, labels 한 폴더
   --all  : final 만이 아니라 모든 단계 (이미지마다 지금 단계 사본 1개, issues·preview 사본 제외)
   --flat : images·labels 아래 train/validation 폴더 없이 (split 은 final_index.csv 의 original_split)"""
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
                        CLASS_NAMES, MANIFEST_DIR, MANIFEST_FILE)

OUT_DIR = os.path.join(RESULT_DIR, "final")      # visol04/data/final (data/ 는 Git 제외)
REPORT_DIR = "reports/logs/export_final"
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


LOCATION_ORDER = ("final", "view", "review", "edited", "pass")   # 프로그램이 보여주는 우선순위와 같음


def collect(skip_raw, all_stages=False):
    """→ (모을 목록 {rel: [항목...]}, 데이터셋별 진행 수, 경고)
       rel = 'train/a.jpg' (images 아래 경로), 항목 = {dataset, img, txt, stage}
       all_stages=False: final 만 / True: 모든 단계에서 이미지마다 지금 단계의 사본 1개
       (같은 이미지가 여러 단계에 있으면 final > view > review > edited > pass 순으로 1개. issues·preview 사본은 제외)"""
    finals, progress, warn = {}, {}, []
    stages = LOCATION_ORDER if all_stages else ("final",)
    for ds, rd in result_dirs():
        if ds == "raw" and skip_raw:
            n = sum(count_images(os.path.join(rd, *STAGE_DIRS[st], IMG_SUB)) for st in stages)
            if n:
                warn.append(f"raw_result 에 {n}장 — migrate_result.py 로 먼저 옮기세요 (이번에는 제외)")
            continue
        seen, by_stage = set(), {}
        for st in stages:
            img_root = os.path.join(rd, *STAGE_DIRS[st], IMG_SUB)
            txt_root = os.path.join(rd, *STAGE_DIRS[st], TXT_SUB)
            for cur, _, files in os.walk(img_root):
                for f in files:
                    if not f.lower().endswith(IMG_EXTS):
                        continue
                    img = os.path.join(cur, f)
                    rel = os.path.relpath(img, img_root)
                    if rel in seen:                       # 앞선 단계 사본이 이미 있음
                        continue
                    seen.add(rel)
                    txt = os.path.join(txt_root, os.path.splitext(rel)[0] + ".txt")
                    finals.setdefault(rel, []).append({"dataset": ds, "img": img, "stage": st,
                                                       "split": rel.split(os.sep)[0] if os.sep in rel else "",
                                                       "txt": txt if os.path.exists(txt) else None})
                    by_stage[st] = by_stage.get(st, 0) + 1
        n_final = by_stage.get("final", 0) if not all_stages else sum(by_stage.values())
        rest = 0 if all_stages else sum(count_images(os.path.join(rd, *STAGE_DIRS[st], IMG_SUB)) for st in NOT_FINAL)
        progress[ds] = (n_final, rest, by_stage)
    return finals, progress, warn


def flatten(finals):
    """train/validation 폴더 없이 한 폴더로 — 키를 파일 이름으로 (split 이 달라도 이름이 같으면 겹침으로 보고)"""
    flat = {}
    for rel, items in finals.items():
        flat.setdefault(os.path.basename(rel), []).extend(items)
    return flat


def plan(finals, out):
    """→ 할 일 dict: add / update / same / remove / dup / no_txt / empty"""
    todo = {k: [] for k in ("add", "update", "same", "remove", "dup", "no_txt", "empty")}
    keep = set()
    for rel, items in sorted(finals.items()):
        if len(items) > 1:                                  # 같은 split·이름이 두 데이터셋에
            todo["dup"].append((rel, [f"{it['dataset']}/{it['split'] or '-'}/{it['stage']}" for it in items]))
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
    """classes.txt · final_index.csv · manifest 사본 — 매번 새로"""
    # YOLO 학습 설정(dataset.yaml)은 tools/build_split.py 가 train/val/test 로 나눈 뒤 configs/ 에 만듦
    #   (예전에 여기서 만들던 data.yaml 은 train=val 이라 지움)
    old_yaml = os.path.join(out, "data.yaml")
    if os.path.exists(old_yaml):
        os.remove(old_yaml)
    man = os.path.join(BASE, MANIFEST_DIR, MANIFEST_FILE)
    if os.path.exists(man):                       # 출처·상태 정보도 final 과 함께
        shutil.copy2(man, os.path.join(out, MANIFEST_FILE))
    with open(os.path.join(out, "classes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(CLASS_NAMES) + "\n")
    with open(os.path.join(out, "final_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "source_dataset", "original_split", "stage", "boxes"])
        for it, rel, _, dst_txt in sorted(todo["add"] + todo["update"] + todo["same"], key=lambda x: x[1]):
            with open(dst_txt, encoding="utf-8") as t:
                boxes = sum(1 for line in t if line.strip())
            w.writerow([os.path.basename(rel), it["dataset"],
                        it["split"], it["stage"], boxes])


def main():
    ap = argparse.ArgumentParser(description="데이터셋별 final 을 data/final 로 모음")
    ap.add_argument("--apply", action="store_true", help="실제로 복사 (없으면 미리보기)")
    ap.add_argument("--flat", action="store_true",
                    help="images·labels 아래 train/validation 폴더 없이 한 폴더에 (split 은 final_index.csv 에 기록)")
    ap.add_argument("--all", action="store_true",
                    help="final 만이 아니라 모든 단계의 이미지를 모음 (이미지마다 지금 단계 사본 1개)")
    a = ap.parse_args()

    out = os.path.join(BASE, OUT_DIR)
    finals, progress, warn = collect(skip_raw=True, all_stages=a.all)
    if a.flat:
        finals = flatten(finals)
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
        k = (it["dataset"], it["split"] or "(없음)", it["stage"])
        by[k] = by.get(k, 0) + 1
    mode = "적용" if a.apply else "미리보기 (바뀐 것 없음 — 확인 후 --apply)"
    lines = [f"# FINAL 모으기 — {mode}", "",
             f"- 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
             f"- 모을 곳: {OUT_DIR}/ (images·labels " + ("한 폴더 — split 은 final_index.csv" if a.flat else "아래 train/validation 유지") + ")", "",
             "## 진행 현황 (모은 단계: " + ("전체 — 이미지마다 지금 단계 1개" if a.all else "final 만") + ")", "",
             "| 데이터셋 | " + " | ".join(LOCATION_ORDER) + " | 모음 |", "|---|" + "---|" * (len(LOCATION_ORDER) + 1)]
    for ds, (nf, rest, by_stage) in progress.items():
        if a.all:
            cells = [str(by_stage.get(st, 0)) for st in LOCATION_ORDER]
        else:                                   # final 만 모을 때는 나머지 단계는 합계만
            cells = [str(nf)] + ["-"] * (len(LOCATION_ORDER) - 1)
        lines.append(f"| {ds} | " + " | ".join(cells) + f" | {nf} |" + (f" (final 아님 {rest})" if rest else ""))
    lines += ["", f"- data/final 에 들어갈 이미지: **{total}장** / 목표 {TARGET}장 (남은 {max(TARGET - total, 0)}장)",
              "", "## 데이터셋 · split · 단계 별", "", "| 데이터셋 | split | 단계 | 수 |", "|---|---|---|---|"]
    lines += [f"| {d} | {s} | {st} | {n} |" for (d, s, st), n in sorted(by.items())]
    lines += ["", "## 이번에 바뀌는 것", "",
              f"- 새로 추가: {len(todo['add'])}",
              f"- 내용이 바뀌어 갱신: {len(todo['update'])}",
              f"- 그대로 (이미 있음): {len(todo['same'])}",
              f"- final 에서 빠져 지움: {len(todo['remove'])}"]
    lines += [f"  - {os.path.relpath(p, BASE)}" for p in todo["remove"]]
    lines += ["", "## 확인 필요", "",
              f"- 같은 파일 이름 (두 데이터셋/split, 안 넣음): {len(todo['dup'])}"]
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
