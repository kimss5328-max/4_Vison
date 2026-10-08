"""manifest 합치기 — 팀원들의 dataset_manifest.csv 를 내 manifest 하나로 합침

   - 이미지 1장당 1행 (키: source_dataset · original_split · file_name)
   - 같은 이미지가 여러 파일에 있으면 (겹침) 아래 순서로 한 행을 고름
       1) 내 PC 결과 폴더(data/<데이터셋>_result)에서 지금 있는 단계와 status 가 맞는 행
       2) 그 이미지의 이력 csv 에서 가장 최근 저장 시각을 가진 사람의 행
       3) 단계가 더 진행된 행 (FINAL > REVIEW > EDITED > DONE)
     worker 는 이력 csv 상 가장 먼저 저장한 사람 (이력이 없으면 비어 있지 않은 첫 값) — 처음 작업자 고정
     scene_type · review_reason 은 고른 행이 비어 있으면 다른 행 값으로 채움
   - dataset1/2 가 아니거나 split 이 빈 행(raw 테스트 등)은 합치지 않고 보고
   - --origin 을 주면 원본 900장 중 아직 행이 없는 이미지도 빈 상태로 추가 (대장 900행 완성)
   - 결과 폴더의 단계와 status 가 다른 행은 보고 (고치지는 않음)
   - 기본은 미리보기. --apply 를 붙이면 기존 manifest 를 manifests/backup/ 에 복사한 뒤 덮어씀

   사용법 (프로그램 폴더에서):
     python3 tools/merge_manifest.py 받은파일1.csv 받은파일2.csv                 # 미리보기
     python3 tools/merge_manifest.py 받은파일1.csv 받은파일2.csv --apply
     python3 tools/merge_manifest.py 받은파일*.csv --origin ~/exe_01 --apply      # 900행 채우기까지"""
import argparse
import csv
import os
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from src.config import (RESULT_DIR, RESULT_SUFFIX, IMG_SUB, STAGE_DIRS, CSV_DIR, IMG_EXTS,   # noqa: E402
                        DATASET_NAMES, MANIFEST_DIR, MANIFEST_FILE, MANIFEST_HEADER, STAGE_STATUS)
from src.bbox import manifest                                                              # noqa: E402

REPORT_DIR = "reports"
LOCATION_ORDER = ("final", "view", "review", "edited", "pass")
RANK = {"FINAL": 4, "REVIEW": 3, "EDITED": 2, "DONE": 1, "": 0}
VALID_DS = set(DATASET_NAMES.values())
SKIP_TAILS = ("_labeled", "_done", RESULT_SUFFIX)


def key(r):
    return (r.get("source_dataset", ""), r.get("original_split", ""), r.get("file_name", ""))


def read_any(path):
    """manifest csv → 행 목록 (열 구성이 달라도 아는 열만 읽음)"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        missing = [c for c in MANIFEST_HEADER if c not in (rd.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: 열이 없습니다 {missing}")
        return [{c: (r.get(c) or "").strip() for c in MANIFEST_HEADER} for r in rd]


# ── 내 PC 결과 폴더 ──
def result_dir(ds):
    return os.path.join(BASE, RESULT_DIR, ds + RESULT_SUFFIX)


def location(ds, split, name):
    """결과 폴더에서 이 이미지가 지금 있는 단계 ('' = 저장본 없음)"""
    for st in LOCATION_ORDER:
        if os.path.exists(os.path.join(result_dir(ds), *STAGE_DIRS[st], IMG_SUB, split, name)):
            return st
    return ""


def saves(ds, split, name, first=False):
    """이력 csv → {저장한 사람 이름: 가장 최근(first=True 면 가장 처음) 저장 시각}"""
    p = os.path.join(result_dir(ds), *CSV_DIR, split, os.path.splitext(name)[0] + ".csv")
    out = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                who = r.get("reviewer_name") or r.get("worker_name") or ""
                t = r.get("saved_at") or ""
                if who and t and (who not in out or (t < out[who] if first else t > out[who])):
                    out[who] = t
    return out


def expected_status(stage, prev=""):
    if stage in STAGE_STATUS:
        return STAGE_STATUS[stage][0]
    return prev                                   # view: status 유지


# ── 원본 900장 ──
def origin_keys(origins):
    keys = set()
    for o in origins:
        o = os.path.abspath(os.path.expanduser(o))
        for cur, dirs, _ in os.walk(o):
            dirs[:] = sorted(d for d in dirs if not d.endswith(SKIP_TAILS))
            folder = os.path.basename(cur)
            if folder in DATASET_NAMES and os.path.isdir(os.path.join(cur, "images")):
                dirs[:] = []
                img_base = os.path.join(cur, "images")
                for c2, d2, files in os.walk(img_base):
                    d2[:] = [d for d in d2 if not d.endswith(SKIP_TAILS)]
                    for f in files:
                        if f.lower().endswith(IMG_EXTS):
                            keys.add((DATASET_NAMES[folder], manifest.split_of(os.path.join(c2, f)), f))
    return keys


def choose(cands):
    """겹친 행들 → (고른 행, 고른 이유)"""
    ds, split, name = key(cands[0][1])
    stage = location(ds, split, name)
    if stage:
        ok = [c for c in cands if c[1]["status"] == expected_status(stage, c[1]["status"])
              and (stage != "final" or c[1]["qa_status"] == "PASS")]
        if len(ok) == 1:
            return ok[0], f"결과 폴더 단계({stage})와 일치"
        if ok:
            cands = ok
    last = saves(ds, split, name)
    if last:
        latest = max(last, key=last.get)
        hit = [c for c in cands if c[1]["worker"] == latest]
        if hit:
            return hit[0], f"최근 저장자({latest})"
    best = max(cands, key=lambda c: RANK.get(c[1]["status"], 0))
    return best, "더 진행된 단계"


def first_worker(k, cands):
    """겹친 행들의 worker 중 이력상 가장 먼저 저장한 사람 (이력이 없으면 비어 있지 않은 첫 값)"""
    names = [c[1]["worker"] for c in cands if c[1]["worker"]]
    first = saves(*k, first=True)
    known = [n for n in names if n in first]
    if known:
        return min(known, key=first.get)
    return names[0] if names else ""


def main():
    ap = argparse.ArgumentParser(description="팀원 manifest 를 내 manifest 로 합침")
    ap.add_argument("files", nargs="*", help="받은 manifest csv (여러 개)")
    ap.add_argument("--origin", action="append", default=[], help="원본 상위 폴더 — 행이 없는 이미지도 빈 행으로 추가")
    ap.add_argument("--apply", action="store_true", help="실제로 덮어씀 (없으면 미리보기)")
    a = ap.parse_args()

    mine = os.path.join(BASE, MANIFEST_DIR, MANIFEST_FILE)
    sources = ([("내 manifest", mine)] if os.path.exists(mine) else []) + [(os.path.basename(f), f) for f in a.files]
    if not sources:
        sys.exit("합칠 manifest 가 없습니다.")

    groups, order, bad, errors = {}, [], [], []
    for label, path in sources:
        try:
            rows = read_any(path)
        except (OSError, ValueError) as e:
            errors.append(str(e))
            continue
        for r in rows:
            if r["source_dataset"] not in VALID_DS or not r["original_split"]:
                bad.append((label, r))
                continue
            k = key(r)
            if k not in groups:
                groups[k] = []
                order.append(k)
            if not any(c[1] == r for c in groups[k]):        # 완전히 같은 행은 한 번만
                groups[k].append((label, r))

    merged, conflicts, mismatch = [], [], []
    for k in order:
        cands = groups[k]
        if len(cands) == 1:
            row = dict(cands[0][1])
        else:
            (lab, row), why = choose(cands)
            row = dict(row)
            row["worker"] = first_worker(k, cands) or row["worker"]
            for col in ("scene_type", "review_reason"):
                if not row[col]:
                    row[col] = next((c[1][col] for c in cands if c[1][col]), "")
            conflicts.append((k, [(c[0], c[1]["worker"], c[1]["status"]) for c in cands], lab, why))
        stage = location(*k)
        if stage and row["status"] != expected_status(stage, row["status"]):
            mismatch.append((k, stage, row["status"]))
        merged.append(row)

    added = 0
    if a.origin:
        have = {key(r) for r in merged}
        for k in sorted(origin_keys(a.origin) - have):
            merged.append({"file_name": k[2], "source_dataset": k[0], "original_split": k[1],
                           "scene_type": "", "worker": "", "status": "", "qa_status": "", "review_reason": ""})
            added += 1

    if a.apply and not errors:
        bdir = os.path.join(BASE, MANIFEST_DIR, "backup")
        os.makedirs(bdir, exist_ok=True)
        if os.path.exists(mine):
            shutil.copy2(mine, os.path.join(bdir, f"dataset_manifest_{datetime.now():%Y%m%d_%H%M%S}.csv"))
        tmp = mine + ".tmp"
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=MANIFEST_HEADER)
            w.writeheader()
            w.writerows(merged)
        os.replace(tmp, mine)

    # 보고
    stat = {}
    for r in merged:
        k2 = (r["source_dataset"], r["original_split"], r["status"] or "(미작업)")
        stat[k2] = stat.get(k2, 0) + 1
    mode = "적용 (이전 파일은 manifests/backup/)" if a.apply and not errors else "미리보기 (바뀐 것 없음 — 확인 후 --apply)"
    L = [f"# manifest 합치기 — {mode}", "", f"- 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
         "- 합친 파일: " + ", ".join(lab for lab, _ in sources),
         f"- 합친 결과: **{len(merged)}행**" + (f" (원본에서 빈 행 {added}개 추가)" if a.origin else ""), "",
         "## 데이터셋 · split · 상태별", "", "| 데이터셋 | split | status | 수 |", "|---|---|---|---|"]
    L += [f"| {d} | {s} | {st} | {n} |" for (d, s, st), n in sorted(stat.items())]
    L += ["", f"## 겹친 이미지 (여러 파일에 있음): {len(conflicts)}"]
    L += [f"- {k[0]}/{k[1]}/{k[2]} → **{lab}** 의 행 사용 ({why}) · 후보: "
          + ", ".join(f"{l}[{w or '-'}:{s or '-'}]" for l, w, s in c) for k, c, lab, why in conflicts]
    L += ["", f"## 합치지 않은 행 (dataset1/2 아님 또는 split 빈칸): {len(bad)}"]
    L += [f"- {lab}: {r['file_name']} ({r['source_dataset'] or '-'}/{r['original_split'] or '빈칸'})" for lab, r in bad]
    L += ["", f"## 결과 폴더 단계와 status 가 다름 (확인 필요): {len(mismatch)}"]
    L += [f"- {k[0]}/{k[1]}/{k[2]}: 폴더={st}, manifest={s or '-'}" for k, st, s in mismatch]
    if errors:
        L += ["", "## 읽지 못한 파일 (적용 안 함)"] + [f"- {e}" for e in errors]
    text = "\n".join(L) + "\n"
    print(text)
    os.makedirs(os.path.join(BASE, REPORT_DIR), exist_ok=True)
    rp = os.path.join(BASE, REPORT_DIR, f"merge_manifest_{datetime.now():%Y%m%d_%H%M%S}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"보고서: {os.path.relpath(rp, BASE)}")


if __name__ == "__main__":
    main()
