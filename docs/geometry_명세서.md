# 🛠️ geometry.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** BBox 좌표계 간 수학적 단방향/양방향 변환을 처리하는 순수 기하학 함수(Pure Functions) 모듈. UI나 화면 종속성 없이 픽셀 단위 박스(Dict)와 YOLO 정규화 좌표 튜플 간 상호 변환 전담
* **연동 모듈:**
  * `src.ui.view_mixin`: 캔버스 BBox 렌더링 좌표 계산 시 호출
  * `src.ui.edit_mixin`: 마우스 편집/드래그 시 BBox 좌표 변환에 활용
  * `src.bbox.storage_mixin`: 라벨 저장 및 이력 CSV 기록 시 좌표 변환에 활용

---

## 2. 입출력 데이터 (Input & Output)
* **Input:**
  * `box_to_yolo`: BBox 픽셀 딕셔너리 `b={"x1", "y1", "x2", "y2"}` 및 원본 이미지 해상도 `(iw, ih)`
  * `yolo_to_box`: Class ID `cls`, YOLO 정규화 중심 좌표 및 크기 `(xc, yc, w, h)` (`0.0` ~ `1.0`), 이미지 해상도 `(iw, ih)`
* **Output:**
  * `box_to_yolo`: YOLO 정규화 튜플 `(center_x, center_y, width, height)`
  * `yolo_to_box`: 픽셀 단위 BBox 딕셔너리 `{"cls": cls, "x1": x1, "y1": y1, "x2": x2, "y2": y2}`

---

## 3. 주요 기능 및 계산 공식 (Core Mathematics)
* **픽셀 $\rightarrow$ YOLO 정규화 (`box_to_yolo`):**
  $$x_c = \frac{x_1 + x_2}{2 \cdot iw}, \quad y_c = \frac{y_1 + y_2}{2 \cdot ih}, \quad w = \frac{x_2 - x_1}{iw}, \quad h = \frac{y_2 - y_1}{ih}$$
* **YOLO 정규화 $\rightarrow$ 픽셀 (`yolo_to_box`):**
  $$x_1 = \left(x_c - \frac{w}{2}\right) \cdot iw, \quad y_1 = \left(y_c - \frac{h}{2}\right) \cdot ih$$
  $$x_2 = \left(x_c + \frac{w}{2}\right) \cdot iw, \quad y_2 = \left(y_c + \frac{h}{2}\right) \cdot ih$$

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **UI 독립성 보장:** 외부 라이브러리(PIL, Tkinter)나 클래스 상태(State)를 일절 참조하지 않는 순수 함수로 구현되어 테스트 및 타 모듈 재사용성 극대화

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **상태 미보존 (Stateless):** 입력 인자 외의 외부 상태를 저장하거나 수정하지 않으며, 부동소수점 오차 범위 내의 순수 산술 변환만 수행함

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `yolo_to_box`로 변환된 BBox 딕셔너리를 다시 `box_to_yolo`로 변환했을 때 원래의 정규화 좌표가 복원되는지 단위 테스트(Unit Test)로 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-GEO-01 (핸들 크기 상수 분리):** `view_mixin`에서 선택 하이라이트 핸들 크기(8px)가 `geometry.py` 또는 `config.py`의 `HANDLE_R`과 파편화되어 사용되는 부분에 대한 수치 통일성 검토 필요
