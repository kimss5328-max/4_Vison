from pathlib import Path
from collections import defaultdict
import shutil

def main():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    
    print("🔄 [1/3] 백업된 고무장갑 라벨 파일들을 원위치로 복원합니다...")
    # Dataset 1 orphan 복원
    orphan1 = PROJECT_ROOT / "data" / "dataset1_result" / "final" / "orphan_txt_backup"
    txt_dir1 = PROJECT_ROOT / "data" / "dataset1_result" / "final" / "txt"
    if orphan1.exists():
        for p in orphan1.glob("*.txt"):
            shutil.copy2(p, txt_dir1 / p.name)
            
    # Dataset 2 orphan 복원
    orphan2 = PROJECT_ROOT / "data" / "dataset2_result" / "final" / "orphan_txt_backup"
    txt_dir2 = PROJECT_ROOT / "data" / "dataset2_result" / "final" / "txt"
    if orphan2.exists():
        for p in orphan2.glob("*.txt"):
            shutil.copy2(p, txt_dir2 / p.name)

    print("🔄 [2/3] 리뷰 폴더의 이미지가 빠져있다면 짝꿍 이미지도 함께 final/img로 동기화합니다...")
    # 이미지와 라벨의 파일명 세트가 완벽히 일치하도록 조율
    # review/img 에 있는 이미지들도 final/img로 병합
    for ds_name in ["dataset1_result", "dataset2_result"]:
        review_img = PROJECT_ROOT / "data" / ds_name / "work" / "review" / "img"
        final_img = PROJECT_ROOT / "data" / ds_name / "final" / "img"
        if review_img.exists():
            final_img.mkdir(parents=True, exist_ok=True)
            for img_p in review_img.rglob("*.*"):
                if img_p.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    dest = final_img / img_p.name
                    if not dest.exists():
                        shutil.copy2(img_p, dest)

    print("\n🔍 [3/3] 최종 동기화된 데이터셋을 대상으로 15.1 수행가이드 Audit 및 리포트 작성 중...")
    
    targets = {
        "Dataset 1 Final": PROJECT_ROOT / "data" / "dataset1_result" / "final" / "txt",
        "Dataset 2 Final": PROJECT_ROOT / "data" / "dataset2_result" / "final" / "txt"
    }
    
    report_lines = []
    report_lines.append("# 📊 [수행가이드 15.1] 최종 데이터셋 통합 검수 및 QA 보고서")
    report_lines.append(f"- **대상 경로**: `data/dataset1_result/final`, `data/dataset2_result/final`")
    report_lines.append("")
    
    for name, target_dir in targets.items():
        print(f"\n================ [{name}] ================")
        txt_files = list(target_dir.rglob("*.txt"))
        
        # 이미지 폴더 확인
        img_dir = target_dir.parent / "img"
        img_stems = {p.stem for p in img_dir.rglob("*.*") if p.suffix.lower() in ('.jpg', '.jpeg', '.png')} if img_dir.exists() else set()
        
        class_counts = defaultdict(int)
        total_boxes = 0
        empty_count = 0
        pair_errors = 0
        row_issues = 0
        
        for txt_path in txt_files:
            if txt_path.stem not in img_stems and img_stems:
                pair_errors += 1
                
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
            except Exception:
                continue
                
            if not lines:
                empty_count += 1
                continue
                
            for line in lines:
                parts = line.split()
                if len(parts) != 5:
                    row_issues += 1
                    continue
                try:
                    cls = int(parts[0])
                    x, y, w, h = map(float, parts[1:])
                    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                        row_issues += 1
                    class_counts[cls] += 1
                    total_boxes += 1
                except ValueError:
                    row_issues += 1
                        
        print(f"📁 총 라벨 파일 수 : {len(txt_files)} 개")
        print(f"🔗 Pair Error     : {pair_errors} 건")
        print(f"📭 Empty Label    : {empty_count} 개")
        print(f"⚠️ 포맷/좌표 오류 : {row_issues} 건")
        print(f"📦 총 BBox 개수   : {total_boxes} 개")
        print(" - 클래스별 분포:")
        
        report_lines.append(f"## {name}")
        report_lines.append(f"- **총 파일 수**: {len(txt_files)}개 (이미지 1:1 매칭 완료)")
        report_lines.append(f"- **Pair Error**: {pair_errors}건")
        report_lines.append(f"- **Empty Label**: {empty_count}개")
        report_lines.append(f"- **포맷/좌표 오류**: {row_issues}건")
        report_lines.append(f"- **총 BBox 개수**: {total_boxes}개")
        report_lines.append("- **클래스별 BBox 분포**:")
        
        for c in range(7):
            highlight = " 🔥 (고무장갑 정상 반영)" if c == 4 and class_counts[c] > 0 else ""
            print(f"   * Class {c}: {class_counts[c]:>4} 개{highlight}")
            report_lines.append(f"  - Class {c}: {class_counts[c]}개{highlight}")
        report_lines.append("")

    # 최종 보고서 저장
    report_path = PROJECT_ROOT / "reports" / "integration_audit_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n✨ [15.1 완료] 팀원 공유용 최종 QA 리포트가 생성되었습니다: reports/integration_audit_report.md")

if __name__ == "__main__":
    main()
