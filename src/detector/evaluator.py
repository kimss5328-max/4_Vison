"""Baseline 모델 검증 지표 평가 및 reports/baseline_metrics.csv 저장 (가이드 18.4)

Baseline 확정 지표 (progress_20261014.md § 3):
    val 100장 · 박스 501
    P 0.926 · R 0.849 · mAP50 0.889 · mAP50-95 0.780
    약점: Class 5 병해·갈변 — P 0.739 · R 0.367 · mAP50 0.427

공개 함수:
    evaluate(weight_path, dry_run=False)
        → ultralytics val 실행 후 reports/baseline_metrics.csv 저장
    load_metrics()
        → 기존 reports/baseline_metrics.csv 읽기 (list[dict])
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.common.paths import (
    PROJECT_ROOT, BASELINE_WEIGHT, BASELINE_METRICS_CSV,
    DATASET_YAML, BASELINE_DIR, reports_log_dir,
)
from src.common.manifest import write_csv

# CSV 헤더 (reports/baseline_metrics.csv)
METRICS_HEADER = [
    "class", "images", "instances",
    "precision", "recall", "map50", "map50_95",
]


def _metrics_to_rows(results: Any) -> List[Dict[str, str]]:
    """ultralytics Results → CSV rows (all + class별)."""
    rows = []
    # all 행
    m = results.results_dict
    rows.append({
        "class":     "all",
        "images":    str(results.val_dataset_size if hasattr(results, "val_dataset_size") else ""),
        "instances": "",
        "precision": f"{m.get('metrics/precision(B)', 0):.4f}",
        "recall":    f"{m.get('metrics/recall(B)', 0):.4f}",
        "map50":     f"{m.get('metrics/mAP50(B)', 0):.4f}",
        "map50_95":  f"{m.get('metrics/mAP50-95(B)', 0):.4f}",
    })
    # class별 행
    if hasattr(results, "ap_class_index") and results.ap_class_index is not None:
        names = results.names
        for i, cls_idx in enumerate(results.ap_class_index):
            rows.append({
                "class":     names.get(int(cls_idx), str(cls_idx)),
                "images":    "",
                "instances": "",
                "precision": f"{results.box.p[i]:.4f}" if hasattr(results.box, "p") else "",
                "recall":    f"{results.box.r[i]:.4f}" if hasattr(results.box, "r") else "",
                "map50":     f"{results.box.ap50[i]:.4f}" if hasattr(results.box, "ap50") else "",
                "map50_95":  f"{results.box.ap[i]:.4f}" if hasattr(results.box, "ap") else "",
            })
    return rows


def evaluate(
    weight_path: Optional[str | Path] = None,
    data_yaml:   Optional[str | Path] = None,
    dry_run: bool = False,
) -> None:
    """Baseline val 실행 → reports/baseline_metrics.csv 저장.

    Args:
        weight_path: 가중치 경로. 미지정 시 BASELINE_WEIGHT 사용.
        data_yaml:   dataset.yaml 경로. 미지정 시 DATASET_YAML 사용.
        dry_run:     True 이면 경로 확인만 하고 실행하지 않음.
    """
    weight = Path(weight_path) if weight_path else BASELINE_WEIGHT
    data   = Path(data_yaml)   if data_yaml   else DATASET_YAML

    print(f"\n[Baseline 평가]")
    print(f"  가중치  : {weight}")
    print(f"  데이터  : {data}")
    print(f"  결과 저장: {BASELINE_METRICS_CSV}")

    # 입력 존재 확인 (주의 사항 4번)
    missing = [p for p in (weight, data) if not p.exists()]
    if missing:
        for p in missing:
            print(f"[ERROR] 파일 없음: {p}")
        sys.exit(1)

    if dry_run:
        print("\n[dry_run] 평가를 실행하지 않습니다.")
        return

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics 가 설치되지 않았습니다: pip install ultralytics")
        sys.exit(1)

    model   = YOLO(str(weight))
    results = model.val(data=str(data), imgsz=1920, split="val")

    rows = _metrics_to_rows(results)
    write_csv(BASELINE_METRICS_CSV, rows, METRICS_HEADER)
    print(f"\n[완료] {BASELINE_METRICS_CSV}  ({len(rows)}행 저장)")

    # 주요 지표 요약 출력
    if rows:
        r = rows[0]
        print(f"  all → P {r['precision']}  R {r['recall']}"
              f"  mAP50 {r['map50']}  mAP50-95 {r['map50_95']}")


def load_metrics() -> List[Dict[str, str]]:
    """기존 reports/baseline_metrics.csv 읽기."""
    from src.common.manifest import read_csv
    return read_csv(BASELINE_METRICS_CSV)
