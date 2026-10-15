"""YOLO11 Baseline 학습 재현 (progress_20261014.md § 3 · 가이드 17.1)

Baseline 확정 조건:
    model    : yolo11n.pt  (7클래스, Class 4 고무장갑 포함)
    imgsz    : 1920
    epochs   : 100  (patience 30)
    batch    : -1   (AutoBatch)
    cache    : ram
    seed     : 0
    project  : runs/baseline_v1
    name     : weights  (→ runs/baseline_v1/weights/best.pt)

실행 전 확인:
    runs/baseline_v1/args.yaml 이 있으면 조건 비교 후 경고 출력
    (재현 학습 시 같은 조건이어야 함 — 주의 사항 8번)

공개 함수:
    train(dry_run=False)   → 학습 실행. dry_run=True 이면 조건만 출력
    compare_args(yaml_path)→ args.yaml 과 Baseline 조건 비교 결과 반환
"""
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from src.common.paths import (
    PROJECT_ROOT, BASELINE_DIR, BASELINE_WEIGHT,
    BASELINE_ARGS_YAML, DATASET_YAML,
)

# ── Baseline 확정 학습 조건 (17.1) ───────────────────────────────────────────
BASELINE_TRAIN_ARGS: Dict[str, Any] = {
    "model":    "yolo11n.pt",
    "data":     str(DATASET_YAML),
    "imgsz":    1920,
    "epochs":   100,
    "patience": 30,
    "batch":    -1,
    "cache":    "ram",
    "seed":     0,
    "project":  str(BASELINE_DIR),
    "name":     "weights",          # → runs/baseline_v1/weights/
    "exist_ok": True,
}


def compare_args(yaml_path: str | Path | None = None) -> Tuple[bool, Dict[str, Tuple]]:
    """args.yaml 의 조건을 BASELINE_TRAIN_ARGS 와 비교.

    반환: (all_match: bool, diff: {key: (expected, actual)})
    """
    path = Path(yaml_path) if yaml_path else BASELINE_ARGS_YAML
    if not path.exists():
        return True, {}   # args.yaml 없으면 비교 생략 (첫 실행)

    try:
        import yaml  # PyYAML (ultralytics 설치 시 포함)
        with open(path, encoding="utf-8") as f:
            recorded: Dict[str, Any] = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[WARN] args.yaml 읽기 실패: {e}")
        return True, {}

    keys_to_check = ("imgsz", "epochs", "patience", "batch", "cache", "seed")
    diff = {}
    for k in keys_to_check:
        expected = BASELINE_TRAIN_ARGS.get(k)
        actual   = recorded.get(k)
        if expected != actual:
            diff[k] = (expected, actual)
    return len(diff) == 0, diff


def train(dry_run: bool = False) -> None:
    """Baseline 학습 실행.

    Args:
        dry_run: True 이면 학습 조건만 출력하고 실행하지 않음.
    """
    print("\n[Baseline 학습 조건]")
    for k, v in BASELINE_TRAIN_ARGS.items():
        print(f"  {k:<12}: {v}")

    # args.yaml 조건 비교 (주의 사항 8번)
    match, diff = compare_args()
    if diff:
        print("\n[WARN] 기존 args.yaml 과 다른 조건:")
        for k, (exp, act) in diff.items():
            print(f"  {k}: 기대={exp!r}  실제={act!r}")
        print("       runs/baseline_v1/args.yaml 을 확인하세요.")
    elif BASELINE_ARGS_YAML.exists():
        print("\n[OK] args.yaml 조건 일치 — Baseline 재현 가능")

    # 입력 파일 존재 확인 (주의 사항 4번)
    if not DATASET_YAML.exists():
        print(f"\n[ERROR] dataset.yaml 없음: {DATASET_YAML}")
        sys.exit(1)

    if dry_run:
        print("\n[dry_run] 학습을 실행하지 않습니다.")
        return

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics 가 설치되지 않았습니다: pip install ultralytics")
        sys.exit(1)

    model = YOLO(BASELINE_TRAIN_ARGS["model"])
    args = {k: v for k, v in BASELINE_TRAIN_ARGS.items() if k != "model"}
    print("\n[학습 시작]")
    model.train(**args)
    print(f"\n[완료] 가중치: {BASELINE_DIR / 'weights' / 'best.pt'}")
