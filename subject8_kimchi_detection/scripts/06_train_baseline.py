"""Baseline 학습 실행 (교과8 17.3)

Baseline 조건을 이 파일 한 곳에 고정한다. 7일차 실험은 이 조건에서 한 항목만 바꾼다 (20.2).

프로젝트 루트에서 실행 (9.0):
  시험 실행  python -u tools/06_train_baseline.py --epochs 1 --name baseline_dryrun 2>&1 | tee runs/baseline_dryrun.log
  본 학습    python -u tools/06_train_baseline.py 2>&1 | tee runs/baseline_v1.log
"""
import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train_detector import train_detector  # noqa: E402

# Baseline 조건 (reports/baseline_training_condition.md 17.1 에 같은 값 기록)
BASELINE = {
    "model_name": "yolo11n.pt",
    "data_yaml": "configs/dataset.yaml",
    "epochs": 100,
    "imgsz": 1920,
    "batch": 3,            # 이전 CLI 학습에서 AutoBatch(-1)가 고른 값으로 고정
    "seed": 0,             # Ultralytics 기본값 · 이전 CLI 학습과 같음 (분할 seed 42와 별개)
    "project": "runs",
    "name": "baseline_v1",
    "patience": 30,
    "cache": "ram",
    "optimizer": "auto",
}
EXPECTED_IMAGES = {"train": 600, "val": 100}
IMG_EXTS = {".jpg", ".jpeg", ".png"}


def parse_args():
    p = argparse.ArgumentParser(description="Baseline 학습 (17.3)")
    p.add_argument("--epochs", type=int, default=BASELINE["epochs"], help="시험 실행 때만 바꿈")
    p.add_argument("--name", default=BASELINE["name"], help="시험 실행 때만 바꿈")
    return p.parse_args()


def check_inputs(cfg):
    """학습 전 입력 확인 (9.0 · 9.3). 문제가 있으면 학습을 시작하지 않는다."""
    if Path.cwd().resolve() != PROJECT_ROOT:
        raise RuntimeError(f"프로젝트 루트에서 실행하세요: cd {PROJECT_ROOT}")

    for rel in (cfg["model_name"], cfg["data_yaml"]):
        if not (PROJECT_ROOT / rel).exists():
            raise FileNotFoundError(f"입력 파일이 없습니다: {PROJECT_ROOT / rel}")

    for split, expected in EXPECTED_IMAGES.items():
        img_dir = PROJECT_ROOT / "data" / "yolo" / "images" / split
        if not img_dir.exists():
            raise FileNotFoundError(f"이미지 폴더가 없습니다: {img_dir}")
        n = sum(1 for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXTS)
        if n != expected:
            raise ValueError(f"{split} 이미지 수가 다릅니다: {n}장 (기대 {expected}장)")

    save_dir = PROJECT_ROOT / cfg["project"] / cfg["name"]
    if save_dir.exists():
        raise FileExistsError(f"이미 있는 실행 폴더입니다 (덮어쓰기 방지): {save_dir}")
    return save_dir


def find_save_dir(expected, name):
    """실제 저장 위치 확인 — 예상 위치에 없으면 runs/ 아래에서 찾는다."""
    if expected.exists():
        return expected
    found = sorted((PROJECT_ROOT / "runs").rglob(name), key=lambda p: p.stat().st_mtime)
    if not found:
        raise FileNotFoundError(f"실행 폴더를 찾을 수 없습니다: {name}")
    print(f"[주의] 예상 위치와 다릅니다: {found[-1]} (예상 {expected})")
    return found[-1]


def check_outputs(save_dir, epochs):
    """학습 후 결과 확인 (17.4)."""
    best = save_dir / "weights" / "best.pt"
    results = save_dir / "results.csv"
    for path in (best, results):
        if not path.exists():
            raise FileNotFoundError(f"결과 파일이 생성되지 않았습니다: {path}")

    with open(results, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != epochs:
        print(f"[주의] results.csv {len(rows)}행 / epochs {epochs} (patience 조기 종료 가능)")

    nan_rows = [r for r in rows if any((v or "").strip().lower() == "nan" for v in r.values())]
    if nan_rows:
        raise ValueError(f"Loss·지표에 NaN이 있습니다: {len(nan_rows)}행")

    print(f"best.pt     : {best}")
    print(f"results.csv : {len(rows)}행")


def main():
    args = parse_args()
    cfg = {**BASELINE, "epochs": args.epochs, "name": args.name}

    expected_dir = check_inputs(cfg)
    print("학습 조건:", cfg)

    train_detector(
        model_name=cfg["model_name"],
        data_yaml=cfg["data_yaml"],
        epochs=cfg["epochs"],
        imgsz=cfg["imgsz"],
        batch=cfg["batch"],
        seed=cfg["seed"],
        project=str(PROJECT_ROOT / cfg["project"]),
        name=cfg["name"],
        patience=cfg["patience"],
        cache=cfg["cache"],
        optimizer=cfg["optimizer"],
        exist_ok=False,
    )

    save_dir = find_save_dir(expected_dir, cfg["name"])
    check_outputs(save_dir, cfg["epochs"])
    print(f"저장 위치: {save_dir}")


if __name__ == "__main__":
    main()