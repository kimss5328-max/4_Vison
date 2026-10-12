"""학습용 분할 — data/final 을 train / val / test (+ Bridge Holdout) 로 나눠 YOLO 학습 폴더를 만듦

   만드는 것 (수행가이드 구조)
     전체 (옵션 없음)                       표본 (--limit 50)
     data/yolo/images/train·val·test        data/smoke/images/train·val·test
     data/yolo/labels/train·val·test        data/smoke/labels/train·val·test
     data/bridge_holdout/images·labels      (holdout 없음)
     configs/dataset.yaml                   configs/smoke_dataset.yaml
     manifests/split_manifest.csv           manifests/smoke_split_manifest.csv
     manifests/train·val·test·bridge_holdout.csv
   data/final 은 읽기만 함 (이미지·라벨을 복사) · Bridge Holdout 은 dataset.yaml 에 넣지 않음 (교과 14 보존용)

   분류 (final_index.csv + 이력 csv + manifest)
     pool     : pass · edited 에서 바로 final 이 된 이미지
     review   : 이력 csv 에 review 단계 기록이 있거나 manifest 에 review_reason 이 있는 final
     excluded : final_index.csv 의 stage 가 final 이 아닌 이미지 (아직 검수 중)
     missing  : data/final 에 이미지 또는 라벨 없음 (항상 제외)
   --include 로 split 에 넣을 대상을 고름
     pool (기본) = pool 만 · final = pool + review · all = pool + review + excluded (missing 제외 전부)
   나누기
     이미지마다 '대표 클래스'(그 이미지 박스 중 가장 드문 클래스, 박스 없음은 empty)를 정하고
     대표 클래스별로 비율을 맞춰 배정. seed 고정 → 몇 번 돌려도 같은 결과
     --ratio 7 2 1           : train·val·test 비율 (holdout 없음)
     --counts 600 100 100 100: train·val·test·holdout 개수 지정 (대상 수와 합이 같아야 함)
   Split Freeze
     split_manifest.csv 가 이미 있으면 그 배정을 그대로 사용 (폴더만 다시 맞춤)
     새로 나누려면 --force

   사용법 (프로그램 폴더에서):
     python3 tools/build_split.py --limit 50            # 미리보기 (50장 → 35/10/5)
     python3 tools/build_split.py --limit 50 --apply    # data/smoke + configs/smoke_dataset.yaml
     python3 tools/build_split.py --include all --counts 600 100 100 100            # 미리보기 (900장)
     python3 tools/build_split.py --include all --counts 600 100 100 100 --apply    # data/yolo + data/bridge_holdout
   학습 (예):
     yolo detect train model=yolo11n.pt data=configs/smoke_dataset.yaml single_cls=True epochs=10 project=runs name=smoke_single"""
import argparse
import csv
import filecmp
import os
import random
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.config import (RESULT_DIR, RESULT_SUFFIX, CSV_DIR, CLASS_NAMES,   # noqa: E402
                        MANIFEST_DIR, MANIFEST_FILE)

FINAL_DIR = os.path.join(BASE, RESULT_DIR, "final")
INDEX_FILE = "final_index.csv"
CONFIG_DIR = os.path.join(BASE, "configs")
REPORT_DIR = "reports"
SPLITS = ("train", "val", "test")          # dataset.yaml 에 들어가는 역할
ROLES = SPLITS + ("holdout",)               # + Bridge Holdout (yaml 제외)
INCLUDE = {"pool": ("pool",), "final": ("pool", "review"), "all": ("pool", "review", "excluded")}
EMPTY = "empty"
MAN_HEADER = ["file_name", "source_dataset", "original_split", "group", "split",
              "primary_class", "classes", "boxes", "note"]
# 예전 버전(목록 txt 방식)이 data/final 에 만든 파일 — 새 구조로 옮긴 뒤 지움 (실행한 쪽 것만)
#   data.yaml 은 export_final 예전 버전이 만든 것 (train=val 이라 학습에 쓰면 안 됨)
def old_files(prefix):
    return ([f"{prefix}{s}.txt" for s in SPLITS + ("review",)]
            + [f"{prefix}dataset.yaml", f"{prefix}split_manifest.csv", "data.yaml", "labels.cache"])


# ── 읽기 ──
def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def label_classes(name):
    """data/final/labels/<이름>.txt → 박스 클래스 번호 목록 (파일 없으면 None)"""
    p = os.path.join(FINAL_DIR, "labels", os.path.splitext(name)[0] + ".txt")
    if not os.path.exists(p):
        return None
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if parts:
                try:
                    out.append(int(float(parts[0])))
                except ValueError:
                    pass
    return out


def went_review(ds, split, name):
    """이력 csv 에 review 단계(저장 또는 review 에서 옮김) 기록이 있는지"""
    p = os.path.join(BASE, RESULT_DIR, ds + RESULT_SUFFIX, *CSV_DIR, split,
                     os.path.splitext(name)[0] + ".csv")
    return any(r.get("stage") == "review" or r.get("from") == "review" for r in read_csv(p))


def load_items():
    """final_index.csv + 이력 csv + manifest → 이미지 목록 (분류 포함)"""
    index = read_csv(os.path.join(FINAL_DIR, INDEX_FILE))
    if not index:
        sys.exit(f"{os.path.relpath(FINAL_DIR, BASE)}/{INDEX_FILE} 이 없습니다. "
                 f"export_final.py --all --flat --apply 를 먼저 실행하세요.")
    reasons = {(r["source_dataset"], r["original_split"], r["file_name"]): r.get("review_reason", "")
               for r in read_csv(os.path.join(BASE, MANIFEST_DIR, MANIFEST_FILE))}
    items = []
    for r in index:
        name, ds, split = r["file_name"], r["source_dataset"], r["original_split"]
        it = {"file_name": name, "source_dataset": ds, "original_split": split,
              "stage": r.get("stage", ""), "classes": label_classes(name)}
        if not os.path.exists(os.path.join(FINAL_DIR, "images", name)) or it["classes"] is None:
            it["group"], it["why"] = "missing", "data/final 에 이미지 또는 라벨 없음"
        elif it["stage"] != "final":
            it["group"], it["why"] = "excluded", f"아직 final 아님 ({it['stage']})"
        else:
            hist = went_review(ds, split, name)
            reason = reasons.get((ds, split, name), "")
            if hist or reason:
                it["group"] = "review"
                it["why"] = "이력 csv" * hist + (" + " if hist and reason else "") + (f"manifest({reason})" if reason else "")
            else:
                it["group"], it["why"] = "pool", ""
        items.append(it)
    return items


# ── 나누기 ──
def set_primary(pool):
    """대표 클래스 = 이미지 안에서 학습 풀 전체 기준 가장 드문 클래스 (박스 없으면 empty)"""
    freq = {}
    for it in pool:
        for c in set(it["classes"]):
            freq[c] = freq.get(c, 0) + 1
    for it in pool:
        cs = set(it["classes"])
        it["primary"] = str(min(cs, key=lambda c: (freq[c], c))) if cs else EMPTY


def largest_remainder(total, weights):
    """total 을 weights 비율로 정수 배분 (합 = total)"""
    s = sum(weights)
    raw = [total * w / s for w in weights]
    out = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[:total - sum(out)]:
        out[i] += 1
    return out


def by_primary(items, rng):
    groups = {}
    for it in sorted(items, key=lambda x: x["file_name"]):
        groups.setdefault(it["primary"], []).append(it)
    for g in groups.values():
        rng.shuffle(g)
    # 드문 대표 클래스부터 (empty 는 마지막)
    return sorted(groups.items(), key=lambda kv: (kv[0] == EMPTY, len(kv[1]), kv[0]))


def sample(pool, limit, rng):
    """대표 클래스별로 고르게 limit 장 뽑기 (클래스마다 최소 1장, 나머지는 비율대로)"""
    groups = by_primary(pool, rng)
    if limit >= len(pool):
        return list(pool)
    take = {k: 0 for k, _ in groups}
    left = limit
    for k, g in groups:                       # 최소 1장씩
        if left and g:
            take[k] += 1
            left -= 1
    rest = [len(g) - take[k] for k, g in groups]
    if left and sum(rest):
        extra = largest_remainder(left, rest)
        for (k, g), e in zip(groups, extra):
            take[k] += min(e, len(g) - take[k])
    out = [it for k, g in groups for it in g[:take[k]]]
    if len(out) < limit:                      # 반올림으로 모자라면 남은 것에서 채움
        used = {id(it) for it in out}
        out += [it for _, g in groups for it in g if id(it) not in used][:limit - len(out)]
    return out


def assign(items, weights, rng):
    """weights = ROLES 순서 4개 (holdout 0 이면 없음)
       전체 수는 weights 비율대로 정확히 (개수 지정이면 그 개수 그대로), 대표 클래스마다 비율이 최대한 같도록"""
    cap = dict(zip(ROLES, largest_remainder(len(items), weights)))
    w = dict(zip(ROLES, weights))
    tot = sum(weights)
    for _, g in by_primary(items, rng):
        have = {s: 0 for s in ROLES}
        for it in g:
            open_ = [s for s in ROLES if cap[s] > 0]
            # 이 그룹에서 목표 대비 가장 모자란 역할 (같으면 비율이 큰 쪽)
            s = max(open_, key=lambda s: (len(g) * w[s] / tot - have[s], w[s]))
            it["split"] = s
            have[s] += 1
            cap[s] -= 1


def frozen_split(man_path, old_path, pool):
    """이미 만든 split → (배정된 이미지 목록, 읽은 파일, 지금 대상에 없어 빠진 이름들) / 없으면 None"""
    src = man_path if os.path.exists(man_path) else (old_path if old_path and os.path.exists(old_path) else None)
    if not src:
        return None
    by_name = {it["file_name"]: it for it in pool}
    chosen, lost = [], []
    for r in read_csv(src):
        if r.get("split") not in ROLES:
            continue
        it = by_name.get(r["file_name"])
        if it is None:
            lost.append(r["file_name"])
            continue
        it["split"] = r["split"]
        chosen.append(it)
    return chosen, src, lost


# ── 쓰기 ──
def targets(limit):
    if limit:
        return {"data": os.path.join(BASE, RESULT_DIR, "smoke"),
                "yaml": os.path.join(CONFIG_DIR, "smoke_dataset.yaml"),
                "manifest": os.path.join(BASE, MANIFEST_DIR, "smoke_split_manifest.csv"),
                "holdout": None, "lists": None, "old": os.path.join(FINAL_DIR, "smoke_split_manifest.csv")}
    return {"data": os.path.join(BASE, RESULT_DIR, "yolo"),
            "holdout": os.path.join(BASE, RESULT_DIR, "bridge_holdout"),
            "yaml": os.path.join(CONFIG_DIR, "dataset.yaml"),
            "manifest": os.path.join(BASE, MANIFEST_DIR, "split_manifest.csv"),
            "lists": {s: os.path.join(BASE, MANIFEST_DIR, ("bridge_holdout" if s == "holdout" else s) + ".csv")
                      for s in ROLES},
            "old": os.path.join(FINAL_DIR, "split_manifest.csv")}


def plan_copy(t, chosen):
    """→ (복사할 [(src, dst)], 그대로 수, 지울 [path]) — 폴더를 split 과 똑같이 맞춤"""
    copy, same, keep = [], 0, set()
    for it in chosen:
        stem = os.path.splitext(it["file_name"])[0]
        for sub, name in (("images", it["file_name"]), ("labels", stem + ".txt")):
            src = os.path.join(FINAL_DIR, sub, name)
            if it["split"] == "holdout":
                if not t["holdout"]:
                    raise SystemExit("표본(smoke) 모드에는 holdout 이 없습니다.")
                dst = os.path.join(t["holdout"], sub, name)
            else:
                dst = os.path.join(t["data"], sub, it["split"], name)
            keep.add(os.path.normpath(dst))
            if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
                same += 1
            else:
                copy.append((src, dst))
    remove = []
    for sub, root in [(s, r) for r in (t["data"], t["holdout"]) if r for s in ("images", "labels")]:
        for cur, _, files in os.walk(os.path.join(root, sub)):
            for f in files:
                p = os.path.normpath(os.path.join(cur, f))
                if p not in keep:
                    remove.append(p)          # 이전 배정 사본 · labels 캐시 등
    return copy, same, remove


def row(it):
    cs = it["classes"] or []
    return [it["file_name"], it["source_dataset"], it["original_split"], it["group"],
            it.get("split", ""), it.get("primary", ""),
            " ".join(map(str, sorted(set(cs)))), len(cs), it["why"]]


def write_all(t, chosen, rest, args, copy, remove):
    for src, dst in copy:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    for p in remove:
        os.remove(p)
    for sub in ("images", "labels"):
        for s in SPLITS:
            os.makedirs(os.path.join(t["data"], sub, s), exist_ok=True)
        if t["holdout"] and any(it["split"] == "holdout" for it in chosen):
            os.makedirs(os.path.join(t["holdout"], sub), exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(t["yaml"], "w", encoding="utf-8") as f:
        f.write(f"# YOLO 학습 설정 — tools/build_split.py 가 {datetime.now():%Y-%m-%d %H:%M} 에 만듦\n"
                f"# {split_desc(args)} · seed {args.seed}"
                + (f" · {args.limit}장 표본" if args.limit else "") + "\n"
                "# 단일 클래스 학습은 이 파일 그대로 + 학습 옵션 single_cls=True\n"
                "# Bridge Holdout(data/bridge_holdout)은 교과 14 보존용 — 여기에 넣지 않음\n"
                f"path: {t['data']}\n")
        for s in SPLITS:
            f.write(f"{s}: images/{s}\n")
        f.write(f"nc: {len(CLASS_NAMES)}\nnames:\n")
        f.writelines(f"  {i}: \"{n}\"\n" for i, n in enumerate(CLASS_NAMES))
    os.makedirs(os.path.dirname(t["manifest"]), exist_ok=True)
    with open(t["manifest"], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(MAN_HEADER)
        w.writerows(row(it) for it in sorted(chosen + rest, key=lambda x: x["file_name"]))
    if t["lists"]:
        for s, path in t["lists"].items():
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(MAN_HEADER)
                w.writerows(row(it) for it in sorted(chosen, key=lambda x: x["file_name"]) if it["split"] == s)
    # 예전 버전이 data/final 에 만든 파일 정리
    removed_old = []
    for n in old_files("smoke_" if args.limit else ""):
        p = os.path.join(FINAL_DIR, n)
        if os.path.exists(p):
            os.remove(p)
            removed_old.append(n)
    return removed_old


# ── 보고 ──
def split_desc(a):
    if a.counts:
        return "개수 " + " / ".join(f"{r} {n}" for r, n in zip(ROLES, a.counts))
    return "비율 " + ":".join(map(str, a.ratio))


def class_table(chosen, roles):
    rows = ["| 클래스 | " + " | ".join(roles) + " | 합계 (장 / 박스) |", "|---|" + "---|" * (len(roles) + 1)]
    for c in list(range(len(CLASS_NAMES))) + [EMPTY]:
        img = {s: 0 for s in roles}
        box = 0
        for it in chosen:
            cs = it["classes"]
            hit = (not cs) if c == EMPTY else (c in cs)
            if hit:
                img[it["split"]] += 1
                box += 0 if c == EMPTY else cs.count(c)
        name = "박스 없음" if c == EMPTY else f"{c}: {CLASS_NAMES[c]}"
        rows.append(f"| {name} | " + " | ".join(str(img[s]) for s in roles)
                    + f" | {sum(img.values())} / {box} |")
    return rows


def main():
    ap = argparse.ArgumentParser(description="data/final 을 train/val/test(+holdout) 로 나눠 YOLO 학습 폴더를 만듦")
    ap.add_argument("--limit", type=int, default=0, help="대상에서 이만큼만 뽑아 data/smoke 로 (예: 50)")
    ap.add_argument("--ratio", type=int, nargs=3, default=[7, 2, 1], metavar=("TRAIN", "VAL", "TEST"))
    ap.add_argument("--counts", type=int, nargs=4, metavar=("TRAIN", "VAL", "TEST", "HOLDOUT"),
                    help="역할별 개수 지정 (예: 600 100 100 100) — 대상 수와 합이 같아야 함")
    ap.add_argument("--include", choices=list(INCLUDE), default="pool",
                    help="split 대상: pool(기본) / final(+review) / all(+아직 final 아님)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--apply", action="store_true", help="실제로 만듦 (없으면 미리보기)")
    ap.add_argument("--force", action="store_true", help="이미 만든 split 을 버리고 새로 나눔 (Split Freeze 해제)")
    a = ap.parse_args()
    if a.limit < 0 or min(a.ratio) < 0 or sum(a.ratio) == 0:
        sys.exit("--limit 은 0 이상, --ratio 는 0 이상이고 합이 0 보다 커야 합니다.")
    if a.counts and (a.limit or min(a.counts) < 0):
        sys.exit("--counts 는 --limit 과 같이 쓸 수 없고, 0 이상이어야 합니다.")

    rng = random.Random(a.seed)
    items = load_items()
    groups = {g: [it for it in items if it["group"] == g] for g in ("pool", "review", "excluded", "missing")}
    cand = [it for it in items if it["group"] in INCLUDE[a.include]]
    rest = [it for it in items if it["group"] not in INCLUDE[a.include]]
    set_primary(cand)
    t = targets(a.limit)
    if a.counts and len(cand) != sum(a.counts):
        sys.exit(f"대상 {len(cand)}장 (--include {a.include}) ≠ 지정 개수 합 {sum(a.counts)}장. "
                 f"분류: pool {len(groups['pool'])} · review {len(groups['review'])} · "
                 f"excluded {len(groups['excluded'])} · missing {len(groups['missing'])}")

    fz = None if a.force else frozen_split(t["manifest"], t["old"], cand)
    if fz:
        chosen, fz_src, lost = fz
        have = [sum(it["split"] == r for it in chosen) for r in ROLES]
        if a.counts:
            ok = have == list(a.counts)
        else:
            ok = len(chosen) == (min(a.limit, len(cand)) if a.limit else len(cand))
        if not ok:
            sys.exit(f"이미 만든 split ({os.path.relpath(fz_src, BASE)}: "
                     + " / ".join(f"{r} {n}" for r, n in zip(ROLES, have))
                     + f") 이 이번 요청({split_desc(a)} · 대상 {len(cand)}장)과 다릅니다.\n"
                     "Split Freeze 상태라 자동으로 바꾸지 않습니다. 새로 나누려면 --force 를 붙이세요.")
    else:
        chosen = sample(cand, a.limit, rng) if a.limit else list(cand)
        assign(chosen, a.counts or (a.ratio + [0]), rng)
        fz_src, lost = None, []
    picked = {id(it) for it in chosen}
    rest = rest + [it for it in cand if id(it) not in picked]
    copy, same, remove = plan_copy(t, chosen)

    removed_old = []
    if a.apply and chosen:
        removed_old = write_all(t, chosen, rest, a, copy, remove)

    rel = lambda p: os.path.relpath(p, BASE)    # noqa: E731
    roles = [r for r in ROLES if r != "holdout" or any(it["split"] == "holdout" for it in chosen)]
    n = {s: sum(it["split"] == s for it in chosen) for s in ROLES}
    if a.apply and chosen:
        mode = "적용"
    elif a.apply:
        mode = "적용 안 함 — 대상이 비어 있음"
    else:
        mode = "미리보기 (바뀐 것 없음 — 확인 후 --apply)"
    made = f"{rel(t['data'])}/images·labels/train·val·test"
    if "holdout" in roles:
        made += f", {rel(t['holdout'])}/images·labels"
    made += f", {rel(t['yaml'])}, {rel(t['manifest'])}"
    if t["lists"]:
        made += ", manifests/" + "·".join(os.path.basename(p) for p in t["lists"].values())
    L = [f"# 학습용 분할 — {mode}", "",
         f"- 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
         f"- 대상: data/final {len(items)}장 중 --include {a.include} → {len(cand)}장 · {split_desc(a)} · seed {a.seed}"
         + (f" · 표본 {a.limit}장" if a.limit else ""),
         ("- split: 이미 만든 배정 사용 (" + rel(fz_src) + ") — 새로 나누려면 --force") if fz_src
         else "- split: 새로 나눔",
         f"- 만드는 것: {made}", "",
         "## 분류", "", "| 분류 | 장 | split 대상 |", "|---|---|---|",
         f"| pool (pass·edited → final) | {len(groups['pool'])} | {'O' if 'pool' in INCLUDE[a.include] else '-'} |",
         f"| review (review 를 거친 final) | {len(groups['review'])} | {'O' if 'review' in INCLUDE[a.include] else '-'} |",
         f"| excluded (아직 final 아님) | {len(groups['excluded'])} | {'O' if 'excluded' in INCLUDE[a.include] else '-'} |",
         f"| missing (파일 없음) | {len(groups['missing'])} | - |",
         f"| 합계 | {len(items)} | {len(cand)} |", "",
         f"## split — 사용 {len(chosen)}장", "", "| " + " | ".join(roles) + " |", "|" + "---|" * len(roles),
         "| " + " | ".join(str(n[r]) for r in roles) + " |", "",
         "## 클래스별 (장 수: 그 클래스 박스가 있는 이미지)", ""] + class_table(chosen, roles)
    L += ["", "## 폴더 변경", "",
          f"- 복사: {len(copy)} 파일 · 그대로: {same} · 지움(split 에 없는 사본): {len(remove)}"]
    if removed_old:
        L.append("- data/final 에서 정리한 예전 파일: " + ", ".join(removed_old))
    present = {c for it in chosen for c in (it["classes"] or [])}
    grp = {}
    for it in chosen:
        grp[(it["group"], it["split"])] = grp.get((it["group"], it["split"]), 0) + 1
    L += ["", "## 분류별 배정", "", "| 분류 | " + " | ".join(roles) + " |", "|---|" + "---|" * len(roles)]
    L += [f"| {g} | " + " | ".join(str(grp.get((g, r), 0)) for r in roles) + " |"
          for g in ("pool", "review", "excluded") if any(k[0] == g for k in grp)]
    L += ["", "## 확인 필요", "",
          "- split 에 한 장도 없는 클래스: "
          + (", ".join(str(c) for c in range(len(CLASS_NAMES)) if c not in present) or "없음")]
    if any(it["group"] == "excluded" for it in chosen):
        L.append(f"- 아직 final 이 아닌 이미지 {sum(it['group'] == 'excluded' for it in chosen)}장 포함 "
                 "— 검수 확정 후 export_final 을 다시 하면 라벨이 바뀔 수 있음 (배정은 유지됨)")
    if lost:
        L.append(f"- 이전 split 에 있었지만 지금 대상에 없는 이미지 (빠짐): {len(lost)} — " + ", ".join(lost[:10]))
    if groups["missing"]:
        L += [f"- 파일 없음: {it['file_name']}" for it in groups["missing"][:20]]
    text = "\n".join(L) + "\n"
    print(text)
    os.makedirs(os.path.join(BASE, REPORT_DIR), exist_ok=True)
    rp = os.path.join(BASE, REPORT_DIR, f"build_split_{datetime.now():%Y%m%d_%H%M%S}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"보고서: {rel(rp)}")


if __name__ == "__main__":
    main()
