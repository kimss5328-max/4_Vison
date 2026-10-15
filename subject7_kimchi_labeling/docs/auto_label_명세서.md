# 🛠️ auto_label.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** UI 독립형 YOLO 모델 로드 및 이미지 추론 전담 엔진 클래스 (`YoloAutoLabeler`). PIL 이미지 객체를 입력받아 YOLO 추론 및 정규화 좌표 변환 결과만 반환
* **연동 모듈:**
  * `ultralytics.YOLO`: PyTorch/YOLO 모델 추론 실행 (동적 지연 Import 적용)
  * `src.config`: `CLASS_NAMES`, `UNUSED_CLASS`(4번) 상수를 참조하여 유효성 필터링 수행

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** `.pt` 파일 경로 (`load`), PIL Image 객체 및 신뢰도 임계값 (`predict`)
* **Output:** 
  * `load()`: 모델 내 정의된 전체 클래스 수 (`int`)
  * `predict()`: 추론 결과 튜플 리스트 `[(class_id, (center_x, center_y, width, height), confidence)]` (`0.0` ~ `1.0` 정규화 비율)

---

## 3. 주요 기능 및 메서드 (Core Features)
* **지연 로딩 (Lazy Import):** `ultralytics` 패키지를 `load()` 메서드 호출 시점에 동적 import하여 패키지 미설치 환경에서도 메인 프로그램 실행이 가능하도록 보장
* **로드 상태 속성 (`loaded`):** `@property`를 활용해 모델 객체의 로드 완료 여부(`self.model is not None`) 반환
* **추론 및 좌표 정규화 (`predict`):**
  * `model.predict()` 결과에서 BBox 경계 좌표(`xyxy`), Class ID(`cls`), Confidence(`conf`) 추출
  * 원본 해상도(`iw`, `ih`)로 나누어 YOLO 포맷의 정규화 중심 좌표 `(xc, yc)` 및 너비/높이 `(w, h)`로 변환

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **빈 추론 결과 방어:** 모델이 이미지 내에서 객체를 감지하지 못한 경우 에러 없이 빈 리스트(`[]`) 반환
* **무효 및 미사용 클래스 필터링:** 추론된 Class ID가 `UNUSED_CLASS`(4번)이거나 전체 클래스 범주(`0` ~ `len(CLASS_NAMES)-1`)를 벗어날 경우 렌더링 대상에서 원천 제외

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **GUI 상태 미참조:** 본 클래스는 Tkinter UI 위젯 및 인스턴스 상태를 일절 알지 못하도록 완전히 분리 설계됨

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `YoloAutoLabeler` 인스턴스 생성 직후 `loaded` 속성이 `False`를 반환하는지 확인
  2. 올바른 `best.pt` 경로를 전달하여 `load()` 실행 시 정수형 클래스 개수가 반환되고 `loaded`가 `True`로 변경되는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-YOL-01 (GPU/CPU 장치 명시):** `model.predict()` 호출 시 CUDA GPU / CPU 장치 할당 파라미터가 명시되지 않아, 사용자 환경에 따른 추론 속도 차이 발생 여부 확인 필요
