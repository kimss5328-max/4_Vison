# 🛠️ auto_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** Tkinter UI 이벤트와 YOLO 모델 간의 자동 라벨링 제어 및 바인딩. 모델 불러오기 UI, 단일 이미지 추론, 백그라운드 스레딩 기반 미라벨 이미지 일괄(Batch) 추론 및 추론 결과의 BBox 데이터 변환 전담
* **연동 모듈:**
  * `threading`: 비동기 일괄 추론 데몬 스레드 연동
  * `tkinter.filedialog`, `messagebox`: `.pt` 모델 선택 및 경고 다이얼로그
  * `PIL.Image`: 디스크 상의 이미지 로드 및 RGB 변환
  * `src.config.CLASS_NAMES`: 프로그램 내 정의된 전체 클래스 수 및 명칭 참조
  * `src.yolo.auto_label.YoloAutoLabeler`: 실제 YOLO 모델 로드 및 추론 엔진 인스턴스 (`self.labeler`)

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** `.pt` 모델 경로, 신뢰도 임계값(`self.confVar`), 현재 선택된 이미지 또는 미라벨 이미지 경로 리스트
* **Output:**
  * 추론 결과 캐시 (`self.auto_pred`)
  * BBox 리스트 내 자동 BBox 데이터 추가 (`b["auto"] = True`, `b["conf"] = conf`)
  * 모델 라벨(`self.modelLabel`), 상태바 메시지 및 일괄 추론 버튼 상태 업데이트

---

## 3. 주요 기능 및 메서드 (Core Features)
* **신뢰도 설정 정제 (`conf_value`):** UI 입력값을 읽어 `0.01` ~ `0.99` 범주로 Clamp 처리
* **모델 로드 및 클래스 수 검증 (`load_model`):** 모델 로드 후 클래스 수(`n_cls`)와 프로그램 클래스 수(`len(CLASS_NAMES)`)가 다를 경우 경고 모달 출력
* **자동 BBox 반영 (`apply_auto`):** 추론 정규화 좌표를 `yolo_to_box()`로 변환. 수동 작성 박스는 보존하고 기존 자동 생성 박스만 대체
* **단일 이미지 추론 (`run_auto_current`):** 현재 캔버스에 열린 이미지를 대상으로 추론 실행 후 UI 동기화
* **비동기 일괄 추론 (`toggle_batch`, `_batch_work`, `_batch_poll`):**
  * 저장된 적 없고 라벨이 없는 미라벨 이미지를 검색하여 대상 설정
  * 백그라운드 스레드(`_batch_work`)에서 처리하며 300ms 주기 폴링(`_batch_poll`)으로 진행률 및 주황색 리스트 하이라이트 적용

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **`ultralytics` 미설치 대비:** 모델 로드 중 `ImportError` 발생 시 `pip install ultralytics` 안내 다이얼로그 출력
* **스레드 기반 UI 응답성 보장:** 일괄 추론 실행 시 작업 스레드를 데몬(`daemon=True`)으로 분리하고 Tkinter `root.after()` 폴링을 사용해 메인 UI 멈춤 방지
* **중복 실행 방지:** 일괄 추론 진행 중(`_batch_running == True`)에는 단일 추론 버튼 비활성화

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **수동 작성 데이터 보호:** `apply_auto()` 실행 시 작업자가 직접 생성/수정한 수동 BBox(`auto=False`)는 원천적으로 삭제되지 않도록 보호하며, 기존 자동 추론 박스만 세대교체함

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `best.pt` 모델을 로드했을 때 모델 파일명이 UI 패널 상단에 표시되는지 확인
  2. "현재 이미지 추론" 클릭 시 점선 스타일의 자동 BBox가 화면에 생성되는지 확인
  3. "미라벨 이미지 일괄 추론" 실행 시 작업 진행에 따라 이미지 목록 항목이 주황색으로 변경되는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-AUT-01 (중지 요청 응답 지연):** 일괄 추론 중 중지 버튼 클릭 시 `_batch_stop` 플래그가 설정되나, 현재 진행 중인 단일 이미지의 `predict()` 작업이 완료된 후 루프가 탈출하므로 고해상도 이미지 처리 시 중지 지연 반응성 확인 필요
