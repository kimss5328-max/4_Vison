"""
라벨링 프로그램이 저장한 '*_labeled' 폴더 → YOLO 학습 → best.pt

사용 예)
    python train_yolo.py --src D:/data/projA_labeled D:/data/projB_labeled
    python train_yolo.py --src D:/data/projA_labeled --epochs 100 --model yolov8s.pt --imgsz 960

결과: (실행한 폴더)/runs/labeling/train/weights/best.pt
      → 라벨링 프로그램의 '모델(best.pt) 불러오기'에서 선택
"""
import argparse
import os
import random
import shutil

IMG_EXTS = (".jpg", ".jpeg", ".png")
CLASS_NAMES = ["나뭇잎·종이류", "플라스틱·돌·금속류", "나뭇가지류", "벌레류",
               "고무장갑(사용 안 함)", "병해·갈변", "파·고추"]   # 라벨링 프로그램과 동일(0~6)


def csv_to_txt(src, dst):
    """라벨링 프로그램의 csv(쉼표) → YOLO 학습용 txt(공백). Class 4 는 학습에서 제외."""
    lines = []
    with open(src, encoding="utf-8") as f:
        for line in f:
            v = line.replace(",", " ").split()
            if len(v) == 5 and int(v[0]) != 4:
                lines.append(" ".join(v))
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def collect(src_dirs):
    """(이미지 경로, 라벨 csv 경로, 고유 이름) 목록"""
    items = []
    for src in src_dirs:
        proj = os.path.basename(os.path.normpath(src))
        img_root, lbl_root = os.path.join(src, "images"), os.path.join(src, "labels")
        for dp, _, files in os.walk(img_root):
            for fn in files:
                if not fn.lower().endswith(IMG_EXTS):
                    continue
                img = os.path.join(dp, fn)
                rel = os.path.splitext(os.path.relpath(img, img_root))[0]
                lbl = os.path.join(lbl_root, rel + ".csv")
                if not os.path.exists(lbl):
                    continue
                uid = f"{proj}__{rel}".replace(os.sep, "_").replace(" ", "_")
                items.append((img, lbl, uid + os.path.splitext(fn)[1].lower()))
    return items


def build_dataset(items, out, val_ratio, seed):
    random.Random(seed).shuffle(items)
    n_val = max(1, int(len(items) * val_ratio)) if len(items) > 1 else 0
    val_items, train_items = items[:n_val], items[n_val:]
    if not val_items:
        # 이미지가 1장뿐이면 검증용이 비어 학습이 멈춘다 → 파이프라인 테스트용으로 같은 이미지를 재사용
        print("⚠ 이미지가 1장뿐입니다. 동작 확인용으로 같은 이미지를 val 로도 사용합니다. "
              "(실제 성능 평가는 불가 - 이미지를 더 저장한 뒤 학습하세요)")
        val_items = list(items)
        train_items = list(items)
    splits = {"val": val_items, "train": train_items}
    if os.path.isdir(out):
        shutil.rmtree(out)
    for sp, lst in splits.items():
        os.makedirs(os.path.join(out, "images", sp))
        os.makedirs(os.path.join(out, "labels", sp))
        for img, lbl, name in lst:
            shutil.copy2(img, os.path.join(out, "images", sp, name))
            csv_to_txt(lbl, os.path.join(out, "labels", sp, os.path.splitext(name)[0] + ".txt"))
    yaml_path = os.path.join(out, "dataset.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"path: {os.path.abspath(out).replace(os.sep, '/')}\n")
        f.write("train: images/train\nval: images/val\n")
        f.write("names:\n")
        for i, n in enumerate(CLASS_NAMES):
            f.write(f"  {i}: \"{n}\"\n")
    print(f"데이터셋 구성 완료: train {len(splits['train'])}장 / val {len(splits['val'])}장")
    return yaml_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", nargs="+", required=True, help="*_labeled 폴더(여러 개 가능)")
    ap.add_argument("--out", default="yolo_dataset", help="생성할 데이터셋 폴더")
    ap.add_argument("--val", type=float, default=0.2, help="검증셋 비율")
    ap.add_argument("--model", default="yolov8n.pt", help="시작 가중치 (yolov8n/s/m.pt 등)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    items = collect(a.src)
    if not items:
        raise SystemExit("학습할 (이미지 + 저장된 라벨) 쌍이 없습니다. 라벨링 프로그램에서 먼저 '저장'하세요.")
    yaml_path = build_dataset(items, a.out, a.val, a.seed)

    from ultralytics import YOLO
    # 절대 경로로 지정해야 runs/detect/ 아래로 중첩되지 않고 runs/labeling/train 에 저장된다.
    project = os.path.abspath(os.path.join("runs", "labeling"))
    model = YOLO(a.model)
    model.train(data=yaml_path, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
                project=project, name="train", exist_ok=True)
    print(f"\n학습 완료 → {os.path.join(project, 'train', 'weights', 'best.pt')}")


if __name__ == "__main__":
    main()