"""YOLO 모델 로드 / 추론 전담 클래스 (화면과 무관 — 모델만 다룸)"""
import os

from src.config import CLASS_NAMES, UNUSED_CLASS


class YoloAutoLabeler:
    def __init__(self):
        self.model = None
        self.name = ""

    @property
    def loaded(self):
        return self.model is not None

    def load(self, path):
        """best.pt 로드. 실패 시 예외 발생(ImportError 포함). 반환값 = 모델 클래스 수"""
        from ultralytics import YOLO      # 이 시점에 처음 import
        model = YOLO(path)                # 성공했을 때만 아래에서 교체
        self.model = model
        self.name = os.path.basename(path)
        names = getattr(model, "names", None) or {}
        return len(names)

    def predict(self, im, conf):
        """PIL(RGB) 이미지 1장 추론 → [(cls, (xc,yc,w,h) 정규화, conf)]"""
        iw, ih = im.size
        res = self.model.predict(im, conf=conf, verbose=False)[0]
        out = []
        if res.boxes is None or len(res.boxes) == 0:
            return out
        xyxy = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy().astype(int)
        cfs = res.boxes.conf.cpu().numpy()
        for (x1, y1, x2, y2), c, s in zip(xyxy, cls, cfs):
            c = int(c)
            if c == UNUSED_CLASS or not 0 <= c < len(CLASS_NAMES):
                continue
            out.append((c, (((x1 + x2) / 2) / iw, ((y1 + y2) / 2) / ih,
                            (x2 - x1) / iw, (y2 - y1) / ih), float(s)))
        return out
