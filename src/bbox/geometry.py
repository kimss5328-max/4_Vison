"""박스 좌표 변환 (순수 함수 — tkinter 와 무관)"""


def box_to_yolo(b, iw, ih):
    """픽셀 박스 dict → YOLO 정규화 좌표 (xc, yc, w, h)"""
    return ((b["x1"] + b["x2"]) / 2 / iw, (b["y1"] + b["y2"]) / 2 / ih,
            (b["x2"] - b["x1"]) / iw, (b["y2"] - b["y1"]) / ih)


def yolo_to_box(cls, xc, yc, w, h, iw, ih):
    """YOLO 정규화 좌표 → 픽셀 박스 dict"""
    return {"cls": cls,
            "x1": (xc - w / 2) * iw, "y1": (yc - h / 2) * ih,
            "x2": (xc + w / 2) * iw, "y2": (yc + h / 2) * ih}
