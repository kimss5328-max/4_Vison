import csv
import hashlib
import re
from collections import defaultdict
from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png"}
NUM_CLASSES = 7
FALLBACK_EXPECTED = {1: 500, 2: 400}  # manifest에 해당 데이터셋 행이 없을 때만 사용
ROLE_DIRS = {  # 역할 → (이미지 폴더, 라벨 폴더) — 프로젝트 루트 기준
    "train": ("data/yolo/images/train", "data/yolo/labels/train"),
    "val": ("data/yolo/images/val", "data/yolo/labels/val"),
    "test": ("data/yolo/images/test", "data/yolo/labels/test"),
    "bridge_holdout": ("data/bridge_holdout/images", "data/bridge_holdout/labels"),
}
ROLE_ALIAS = {"validation": "val", "holdout": "bridge_holdout", "bridge": "bridge_holdout"}
EXPECTED_TOTAL = 900

def collect(d: Path, exts=None, suffix=None) -> list[Path]:
    if not d.exists():
        return []
    return [p for p in d.rglob("*") if p.is_file()
            and (not exts or p.suffix.lower() in exts)
            and (not suffix or p.suffix.lower() == suffix)]


def group_by_stem(paths):
    g = defaultdict(list)
    for p in paths:
        g[p.stem].append(p)
    return g


def pick_canonical(paths):
    return sorted(paths, key=lambda p: (-len(p.parts), str(p)))[0]


def split_of(p: Path, base: Path) -> str:
    rel = p.relative_to(base)
    return rel.parts[0] if len(rel.parts) > 1 else "(top)"


def file_hash(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def validate_yolo_row(row: str) -> list[str]:
    parts = row.split()
    if len(parts) != 5:
        return ["COLUMN_COUNT"]
    try:
        cls = int(parts[0])
        x, y, w, h = map(float, parts[1:])
    except ValueError:
        return ["PARSE_ERROR"]
    issues = []
    if not 0 <= cls < NUM_CLASSES:
        issues.append("CLASS_RANGE")
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        issues.append("CENTER_RANGE")
    if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        issues.append("SIZE_RANGE")
    return issues


def load_manifest(path: Path):
    """dataset_manifest.csv -> ({dataset_no: {stem: meta}}, warning|None)"""
    meta = defaultdict(dict)
    if not path.exists():
        return meta, f"manifest 없음: {path}"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        need = {"file_name", "source_dataset", "original_split", "scene_type"}
        if not need <= set(rd.fieldnames or []):
            return meta, f"manifest 컬럼 부족: 필요 {sorted(need)} / 실제 {rd.fieldnames}"
        for r in rd:
            m = re.search(r"\d+", r["source_dataset"] or "")
            stem = Path(r["file_name"] or "").stem
            if m and stem:
                meta[int(m.group())][stem] = {
                    "original_split": r["original_split"] or "unmapped",
                    "scene_type": r["scene_type"] or "unmapped",
                }
    if not any(meta.values()):
        return meta, "manifest에 데이터 행이 없음 (original_split, scene_type 집계 불가)"
    return meta, None


def audit_dataset(name, n, img_dir: Path, txt_dir: Path, meta: dict):
    print(f"\n[{name}]")
    if not img_dir.exists() or not txt_dir.exists():
        print(f"경로 없음: {img_dir} 또는 {txt_dir}")
        return None

    issues = []

    def add(filename, issue_type, detail):
        issues.append({"dataset": name, "filename": filename,
                       "issue_type": issue_type, "detail": detail})

    img_list = collect(img_dir, exts=IMG_EXTS)
    txt_list = collect(txt_dir, suffix=".txt")
    img_g, txt_g = group_by_stem(img_list), group_by_stem(txt_list)

    for kind, g, base in (("IMG", img_g, img_dir), ("TXT", txt_g, txt_dir)):
        for stem, paths in g.items():
            if len(paths) > 1:
                same = len({file_hash(p) for p in paths}) == 1
                locs = ", ".join(split_of(p, base) for p in paths)
                add(stem, f"DUPLICATE_STEM_{kind}",
                    f"{len(paths)} copies [{locs}] / {'SAME_CONTENT' if same else 'DIFFERENT_CONTENT'}")

    total_images, total_txts = len(img_g), len(txt_g)

    if meta:
        expected, basis = len(meta), "manifest"
        for s in sorted(set(meta) - set(img_g)):
            add(s, "MANIFEST_NOT_IN_FINAL_IMG", "manifest에 있으나 final/img에 없음")
        for s in sorted(set(meta) - set(txt_g)):
            add(s, "MANIFEST_NOT_IN_FINAL_TXT", "manifest에 있으나 final/txt에 없음")
        for s in sorted(set(img_g) - set(meta)):
            add(s, "FINAL_NOT_IN_MANIFEST", "final/img에 있으나 manifest에 없음")
    else:
        expected, basis = FALLBACK_EXPECTED[n], "fallback"

    qty_ok = total_images == expected and total_txts == expected
    if not qty_ok:
        add("DATASET_LEVEL", "QUANTITY_MISMATCH",
            f"expected({basis})={expected}, images={total_images}, txts={total_txts}")

    class_counts = defaultdict(int)
    split_counts, scene_counts, folder_counts = (defaultdict(int) for _ in range(3))
    per_image = []
    class4_images = pair_errors = empty_labels = 0
    default_meta = {"original_split": "unmapped", "scene_type": "unmapped"}

    for stem in sorted(set(img_g) | set(txt_g)):
        m = meta.get(stem, default_meta)
        split_counts[m["original_split"]] += 1
        scene_counts[m["scene_type"]] += 1

        if stem not in img_g or stem not in txt_g:
            pair_errors += 1
            add(stem, "PAIR_ERROR", f"image={stem in img_g}, txt={stem in txt_g}")
            continue

        img_p, txt_p = pick_canonical(img_g[stem]), pick_canonical(txt_g[stem])
        img_split, txt_split = split_of(img_p, img_dir), split_of(txt_p, txt_dir)
        folder_counts[img_split] += 1
        if img_split != txt_split:
            add(stem, "SPLIT_FOLDER_MISMATCH", f"img={img_split}, txt={txt_split}")

        try:
            lines = [l.strip() for l in txt_p.read_text(encoding="utf-8").splitlines() if l.strip()]
        except Exception:
            add(stem, "READ_ERROR", str(txt_p))
            continue

        if not lines:
            empty_labels += 1
            add(stem, "EMPTY_LABEL_UNCONFIRMED", "빈 라벨: 교과 7 Negative Sample 기록과 대조 필요")
            per_image.append({"dataset": name, "stem": stem, "split": img_split,
                              "bbox_count": 0, "class4_bbox": 0})
            continue

        n_box = c4 = 0
        for idx, line in enumerate(lines, 1):
            errs = validate_yolo_row(line)
            for e in errs:
                add(stem, e, f"line {idx}: {line}")
            if errs:
                continue
            cls = int(line.split()[0])
            class_counts[cls] += 1
            n_box += 1
            c4 += cls == 4
        class4_images += c4 > 0
        per_image.append({"dataset": name, "stem": stem, "split": img_split,
                          "bbox_count": n_box, "class4_bbox": c4})

    counts = [r["bbox_count"] for r in per_image]
    dup_img = sum(len(p) > 1 for p in img_g.values())
    dup_txt = sum(len(p) > 1 for p in txt_g.values())

    S = []

    def row(cat, metric, value):
        S.append({"Dataset": name, "Category": cat, "Metric": metric, "Value": value})

    row("Basic", "Expected Basis", basis)
    row("Basic", "Expected Count", expected)
    row("Basic", "Image Files", len(img_list))
    row("Basic", "TXT Files", len(txt_list))
    row("Basic", "Unique Images", total_images)
    row("Basic", "Unique TXT", total_txts)
    row("Basic", "Quantity Status", "PASS" if qty_ok else "FAIL")
    row("Quality", "Duplicate Stem (IMG)", dup_img)
    row("Quality", "Duplicate Stem (TXT)", dup_txt)
    row("Quality", "Pair Error", pair_errors)
    row("Quality", "Empty Label", empty_labels)
    row("BBox Stats", "Total BBoxes", sum(class_counts.values()))
    row("BBox Stats", "Avg per Image", f"{sum(counts) / len(counts):.2f}" if counts else 0)
    row("BBox Stats", "Max per Image", max(counts, default=0))
    row("BBox Stats", "Min per Image", min(counts, default=0))
    row("Class 4", "Exists", "YES" if class_counts[4] else "NO")
    row("Class 4", "BBoxes", class_counts[4])
    row("Class 4", "Images", class4_images)
    for c in range(NUM_CLASSES):
        row("Class Distribution", f"Class {c}", class_counts[c])
    for k, v in sorted(split_counts.items()):
        row("Original Split", k, v)
    for k, v in sorted(scene_counts.items()):
        row("Scene Type", k, v)
    for k, v in sorted(folder_counts.items()):
        row("Folder Split", k, v)

    print(f"  images {total_images} / txt {total_txts} (expected {expected}, {basis}) -> {'PASS' if qty_ok else 'FAIL'}")
    print(f"  dup {dup_img}/{dup_txt}, pair error {pair_errors}, empty label {empty_labels}, issues {len(issues)}")
    print(f"  class dist {[class_counts[c] for c in range(NUM_CLASSES)]}, class4 {class_counts[4]} bbox / {class4_images} images")
    return {"stems": set(img_g), "summary": S, "issues": issues, "per_image": per_image}


def audit_raw_vs_final(raw_dir: Path, finals: dict, search_roots: list) -> list:
    print("\n[raw vs final]")
    raw_stems = set(group_by_stem(collect(raw_dir, exts=IMG_EXTS)))
    if not raw_stems:
        print(f"  raw 이미지 0개: {raw_dir}")
        return [{"dataset": "RAW_VS_FINAL", "filename": "RAW",
                 "issue_type": "RAW_EMPTY", "detail": str(raw_dir)}]

    final_all = set().union(*finals.values()) if finals else set()
    issues = []

    def add(stem, t, d=""):
        issues.append({"dataset": "RAW_VS_FINAL", "filename": stem, "issue_type": t, "detail": d})

    names = list(finals)
    if len(names) == 2:
        for s in sorted(finals[names[0]] & finals[names[1]]):
            add(s, "IN_BOTH_DATASETS")

    missing = sorted(raw_stems - final_all)
    if missing:
        index = defaultdict(list)
        for root in search_roots:
            for p in collect(root):
                index[p.stem].append(str(p))
        for s in missing:
            add(s, "RAW_NOT_IN_FINAL", " | ".join(index.get(s, [])) or "NOT FOUND")
    for s in sorted(final_all - raw_stems):
        add(s, "FINAL_NOT_IN_RAW")

    print(f"  raw {len(raw_stems)} / final {len(final_all)} / raw only {len(missing)} / final only {len(final_all - raw_stems)}")
    return issues

def audit_split_roles(root: Path):
    """split_manifest.csv와 실제 폴더로 네 역할 수량 확인 (16.8)"""
    print("\n[split roles]")
    summary, issues = [], []

    def row(metric, value):
        summary.append({"Dataset": "ALL", "Category": "Split Role", "Metric": metric, "Value": value})

    def add(filename, issue_type, detail):
        issues.append({"dataset": "SPLIT_ROLE", "filename": filename,
                       "issue_type": issue_type, "detail": detail})

    # 1. manifest에서 역할별 장수
    manifest_counts = defaultdict(int)
    mpath = root / "manifests" / "split_manifest.csv"
    if not mpath.exists():
        add("MANIFEST", "SPLIT_MANIFEST_MISSING", str(mpath))
    else:
        with open(mpath, newline="", encoding="utf-8-sig") as f:
            rd = csv.DictReader(f)
            col = next((c for c in ("split", "role") if c in (rd.fieldnames or [])), None)
            if col is None:
                add("MANIFEST", "SPLIT_COLUMN_MISSING", f"columns={rd.fieldnames}")
            else:
                for r in rd:
                    v = (r[col] or "").strip().lower()
                    manifest_counts[ROLE_ALIAS.get(v, v)] += 1

    # 2. 역할별 실제 이미지·라벨 수 + 짝 확인
    role_stems = {}
    for role, (img_rel, lbl_rel) in ROLE_DIRS.items():
        imgs = group_by_stem(collect(root / img_rel, exts=IMG_EXTS))
        lbls = group_by_stem(collect(root / lbl_rel, suffix=".txt"))
        n_m = manifest_counts.get(role, 0)
        role_stems[role] = set(imgs)
        row(role, len(imgs))
        if not (n_m == len(imgs) == len(lbls)):
            add(role, "ROLE_COUNT_MISMATCH", f"manifest={n_m}, images={len(imgs)}, txts={len(lbls)}")
        for s in sorted(set(imgs) ^ set(lbls)):
            add(s, "ROLE_PAIR_ERROR", f"role={role}, image={s in imgs}, txt={s in lbls}")

    # 3. 두 역할에 같은 이미지 이름이 있는지 (11.4)
    roles = list(role_stems)
    for i, a in enumerate(roles):
        for b in roles[i + 1:]:
            for s in sorted(role_stems[a] & role_stems[b]):
                add(s, "ROLE_OVERLAP", f"{a} & {b}")

    # 4. 알 수 없는 역할 값 · 합계
    for k in sorted(set(manifest_counts) - set(ROLE_DIRS)):
        add(k, "UNKNOWN_ROLE", f"{manifest_counts[k]} rows")
    total = sum(len(s) for s in role_stems.values())
    total_ok = total == EXPECTED_TOTAL == sum(manifest_counts.values()) and not issues
    row("Total", total)
    row("Total Status", "PASS" if total_ok else "FAIL")

    print("  " + " / ".join(f"{r} {len(s)}" for r, s in role_stems.items())
          + f" = {total} -> {'PASS' if total_ok else 'FAIL'} (issues {len(issues)})")
    return summary, issues


def write_csv(path: Path, fields: list, rows: list):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)


def main():
    root = Path(__file__).resolve().parents[1]
    data, reports = root / "data", root / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    manifest_p = data / "subject7_final" / "dataset_manifest.csv"
    if not manifest_p.exists():
        manifest_p = root / "manifests" / "dataset_manifest.csv"
    manifest, warn = load_manifest(manifest_p)
    all_summary, all_issues, all_per_image, finals = [], [], [], {}

    if warn:
        print(f"manifest 경고: {warn}")
        all_issues.append({"dataset": "ALL", "filename": "MANIFEST",
                           "issue_type": "MANIFEST_WARNING", "detail": warn})

    subject7_dir = data / "subject7_final"
    for n in (1, 2):
        name = f"Dataset {n}"
        if (subject7_dir / f"dataset{n}").exists():
            img_p = subject7_dir / f"dataset{n}" / "images"
            txt_p = subject7_dir / f"dataset{n}" / "labels"
        elif (subject7_dir / "images").exists():
            img_p = subject7_dir / "images"
            txt_p = subject7_dir / "labels"
        else:
            res = data / f"dataset{n}_result"
            img_p = res / "final" / "img"
            txt_p = res / "final" / "txt"

        r = audit_dataset(name, n, img_p, txt_p, manifest.get(n, {}))
        if r is None:
            continue
        finals[name] = r["stems"]
        all_summary += r["summary"]
        all_issues += r["issues"]
        all_per_image += r["per_image"]

    raw_dir = subject7_dir / "raw" / "images"
    if not raw_dir.exists():
        raw_dir = data / "raw" / "images"
    roots = [data / f"dataset{n}_result" / s for n in (1, 2) for s in ("work", "issues", "view")
             if (data / f"dataset{n}_result" / s).exists()]
    all_issues += audit_raw_vs_final(raw_dir, finals, roots)

    role_summary, role_issues = audit_split_roles(root)  # ← 네 역할 수량 (16.8)
    all_summary += role_summary
    all_issues += role_issues

    write_csv(reports / "dataset_summary.csv", ["Dataset", "Category", "Metric", "Value"], all_summary)
    write_csv(reports / "audit_issue.csv", ["dataset", "filename", "issue_type", "detail"], all_issues)
    write_csv(reports / "bbox_per_image.csv",
              ["dataset", "stem", "split", "bbox_count", "class4_bbox"], all_per_image)

    print(f"\nsaved: {reports}/dataset_summary.csv, audit_issue.csv ({len(all_issues)}), bbox_per_image.csv ({len(all_per_image)})")


if __name__ == "__main__":
    main()