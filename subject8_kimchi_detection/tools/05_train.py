"""05_train.py — YOLO11 Baseline 학습 실행 (src/detector/trainer.py 호출)

Baseline 확정 조건 (progress_20261014.md § 3 · 가이드 17.1):
  model yolo11n.pt · imgsz 1920 · epochs 100 · patience 30
  batch -1 · cache ram · seed 0
  결과 → runs/baseline_v1/weights/best.pt

[사용법]  (프로젝트 루트에서)
  python tools/05_train.py              # Baseline 학습 실행
  python tools/05_train.py --dry-run    # 조건 확인만 (실행 안 함)

[주의]
  실행 전 runs/baseline_v1/args.yaml 과 조건이 같은지 자동 비교합니다.
  다르면 경고를 출력합니다 (주의 사항 8번).
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.detector.trainer import train  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="YOLO11 Baseline 학습 (src/detector/trainer.py)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="학습 조건만 출력하고 실행하지 않음")
    args = parser.parse_args()
    train(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
