"""06_evaluate.py — Baseline 결과 평가 및 리포트 생성 (src/detector/evaluator.py 호출)

결과:
  reports/baseline_metrics.csv — all + class 0~6 (8행)

[사용법]  (프로젝트 루트에서)
  python tools/06_evaluate.py                     # Baseline weight 로 val 실행
  python tools/06_evaluate.py --dry-run           # 경로 확인만
  python tools/06_evaluate.py --weight <경로>     # 다른 가중치 사용
  python tools/06_evaluate.py --show              # 기존 CSV 출력 (재실행 안 함)
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector.evaluator import evaluate, load_metrics  # noqa: E402


def _show_existing() -> None:
    rows = load_metrics()
    if not rows:
        print("[INFO] reports/baseline_metrics.csv 가 없거나 비어 있습니다.")
        return
    header = list(rows[0].keys())
    widths = [max(len(h), max((len(str(r.get(h, ""))) for r in rows), default=0))
              for h in header]
    sep = "  ".join("-" * w for w in widths)
    hdr = "  ".join(h.ljust(w) for h, w in zip(header, widths))
    print(f"\n{hdr}\n{sep}")
    for r in rows:
        print("  ".join(str(r.get(h, "")).ljust(w) for h, w in zip(header, widths)))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Baseline 평가 + reports/baseline_metrics.csv 저장",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="경로 확인만 (평가 실행 안 함)")
    parser.add_argument("--weight", metavar="PATH",
                        help="가중치 경로 (기본: runs/baseline_v1/weights/baseline_best.pt)")
    parser.add_argument("--show", action="store_true",
                        help="기존 CSV 내용만 출력 (재평가 안 함)")
    args = parser.parse_args()

    if args.show:
        _show_existing()
        return

    evaluate(
        weight_path=args.weight,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
