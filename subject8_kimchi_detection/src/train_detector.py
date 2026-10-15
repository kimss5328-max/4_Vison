"""YOLO 학습 기능 (교과8 17.2)

tools/ 의 실행 Script가 불러 쓰는 재사용 함수만 둔다. 실행 코드는 넣지 않는다 (8절).
"""
from ultralytics import YOLO


def train_detector(
    model_name: str,
    data_yaml: str,
    epochs: int,
    imgsz: int,
    batch: int,
    seed: int,
    project: str,
    name: str,
    **kwargs,
):
    """YOLO 모델을 학습하고 Ultralytics 학습 결과를 돌려준다.

    kwargs: patience, cache, optimizer, exist_ok 처럼
            model.train() 에 그대로 넘길 추가 옵션
    """
    model = YOLO(model_name)

    return model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        seed=seed,
        project=project,
        name=name,
        **kwargs,
    )