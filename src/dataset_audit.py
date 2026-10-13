import csv
from pathlib import Path
from collections import defaultdict

def validate_yolo_row(row: str) -> list[str]:
    issues = []
    parts = row.strip().split()

    if len(parts) != 5:
        return ["COLUMN_COUNT"]

    try:
        cls = int(parts[0])
        x, y, w, h = map(float, parts[1:])
    except ValueError:
        return ["PARSE_ERROR"]

    if cls < 0 or cls > 6:
        issues.append("CLASS_RANGE")

    if cls == 4:
        issues.append("CLASS4_REVIEW")  # 고무장갑 감지 시 리뷰 태그 부여

    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        issues.append("CENTER_RANGE")

    if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
        issues.append("SIZE_RANGE")

    return issues

def audit_dataset(dataset_name: str, img_dir: Path, txt_dir: Path, output_dir: Path):
    print(f"\n🔍 [{dataset_name}] 수행가이드 15.1 정밀 Audit 시작...")
    
    if not img_dir.exists() or not txt_dir.exists():
        print(f"⚠️ 경로를 찾을 수 없습니다: {img_dir} 또는 {txt_dir}")
        return

    img_extensions = {'.jpg', '.jpeg', '.png'}
    img_files = {p.stem: p for p in img_dir.rglob("*.*") if p.suffix.lower() in img_extensions}
    txt_files = {p.stem: p for p in txt_dir.rglob("*.txt")}

    all_stems = sorted(list(set(img_files.keys()) | set(txt_files.keys())))
    
    total_images = len(img_files)
    total_txts = len(txt_files)
    pair_errors = 0
    empty_labels = 0
    negative_samples = 0  # 정상 김치 등 Negative Sample (빈 텍스트 파일 허용)
    
    class_counts = defaultdict(int)
    bbox_counts_per_image = []
    issues_records = []

    for stem in all_stems:
        has_img = stem in img_files
        has_txt = stem in txt_files
        
        if not (has_img and has_txt):
            pair_errors += 1
            issues_records.append({
                "dataset": dataset_name,
                "filename": stem,
                "issue_type": "PAIR_ERROR",
                "detail": f"Image exists: {has_img}, Txt exists: {has_txt}"
            })
            continue

        txt_path = txt_files[stem]
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            issues_records.append({
                "dataset": dataset_name,
                "filename": stem,
                "issue_type": "READ_ERROR",
                "detail": "Failed to read txt file"
            })
            continue

        # Empty TXT 검사 규칙 적용 (무조건 오류로 단정하지 않음)
        if not lines:
            empty_labels += 1
            # FINAL 기록이나 네거티브 샘플 판단 (여기서는 빈 라벨 파일 정상 허용 케이스로 분기 관리)
            negative_samples += 1
            bbox_counts_per_image.append(0)
            continue

        img_bboxes = 0
        for line_idx, line in enumerate(lines):
            row_issues = validate_yolo_row(line)
            if row_issues:
                for issue in row_issues:
                    # Class 4 감지는 리뷰용 태그이므로 에러 카운트에서 제외하고 기록만 수행 가능
                    if issue == "CLASS4_REVIEW":
                        class_counts[4] += 1
                        img_bboxes += 1
                        continue
                        
                    issues_records.append({
                        "dataset": dataset_name,
                        "filename": stem,
                        "issue_type": issue,
                        "detail": f"Line {line_idx+1}: {line}"
                    })
            else:
                parts = line.split()
                cls = int(parts[0])
                class_counts[cls] += 1
                img_bboxes += 1

        bbox_counts_per_image.append(img_bboxes)

    # 출력 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. dataset_summary.csv 저장
    summary_path = output_dir / f"{dataset_name.lower().replace(' ', '_')}_dataset_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Dataset Name", dataset_name])
        writer.writerow(["Total Images", total_images])
        writer.writerow(["Total TXT", total_txts])
        writer.writerow(["Pair Error", pair_errors])
        writer.writerow(["Empty Label (Potential Negative)", empty_labels])
        writer.writerow(["Confirmed Negative Samples", negative_samples])
        writer.writerow(["Total BBoxes", sum(class_counts.values())])
        for c in range(7):
            writer.writerow([f"Class {c} Count", class_counts[c]])

    # 2. audit_issue.csv 저장
    issue_path = output_dir / f"{dataset_name.lower().replace(' ', '_')}_audit_issue.csv"
    with open(issue_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["dataset", "filename", "issue_type", "detail"])
        writer.writeheader()
        writer.writerows(issues_records)

    print(f" ✅ 요약 CSV 저장 완료: {summary_path.relative_to(Path.cwd())}")
    print(f" ✅ 이슈 CSV 저장 완료: {issue_path.relative_to(Path.cwd())}")
    print(f"   - 총 이미지: {total_images}, 총 TXT: {total_txts}, Pair Error: {pair_errors}, Empty(Negative): {empty_labels}")
    print(f"   - 클래스별 분포: Dict({dict(class_counts)})")

def main():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    reports_dir = PROJECT_ROOT / "reports"

    # Dataset 1 Audit
    audit_dataset(
        dataset_name="Dataset 1",
        img_dir=PROJECT_ROOT / "data" / "dataset1_result" / "final" / "img",
        txt_dir=PROJECT_ROOT / "data" / "dataset1_result" / "final" / "txt",
        output_dir=reports_dir
    )

    # Dataset 2 Audit
    audit_dataset(
        dataset_name="Dataset 2",
        img_dir=PROJECT_ROOT / "data" / "dataset2_result" / "final" / "img",
        txt_dir=PROJECT_ROOT / "data" / "dataset2_result" / "final" / "txt",
        output_dir=reports_dir
    )

if __name__ == "__main__":
    main()
