from pathlib import Path

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main():
    model = YOLO(
        str(PROJECT_ROOT / "models" / "final" / "final_best.pt")   # = baseline_best.pt (c90f9767442e)
    )

    model.predict(
        source=str(PROJECT_ROOT / "data" / "new_unlabeled"),
        imgsz=1920,      # Final Model 학습 해상도와 일치 (예시에는 없음 → 기본 640이 되므로 추가)
        conf=0.25,
        save=True,
        save_txt=True,
        save_conf=False,
        project=str(PROJECT_ROOT / "runs"),
        name="auto_label_candidates",
    )

if __name__ == "__main__":
    main()
