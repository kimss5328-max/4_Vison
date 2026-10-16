from pathlib import Path

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    model = YOLO(
        str(PROJECT_ROOT / "models" / "final" / "final_best.pt")   # = baseline_best.pt (c90f9767442e)
    )

    metrics = model.val(
        data=str(PROJECT_ROOT / "configs" / "dataset.yaml"),
        split="test",
        imgsz=1920,   # Baseline 학습·평가 조건과 일치 (args.yaml)
        batch=3,      # Baseline 학습·평가 조건과 일치 (args.yaml)
        plots=True,
        project=str(PROJECT_ROOT / "runs"),
        name="final_test",
    )

    print("Test Precision:", metrics.box.mp)
    print("Test Recall:", metrics.box.mr)
    print("Test mAP50:", metrics.box.map50)
    print("Test mAP50-95:", metrics.box.map)

if __name__ == "__main__":
    main()
