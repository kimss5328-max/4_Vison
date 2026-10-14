# 🛠️ app.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 전체 라벨링 애플리케이션의 엔트리 포인트 및 상태(변수) 중앙 관리. 다중 상속을 통해 기능별 Mixin 클래스들을 하나로 조립하고 앱의 시작 및 종료 처리 전담
* **연동 모듈:**
  * `tkinter.messagebox`: 종료 시 저장 확인 다이얼로그
  * `src.yolo.auto_label.YoloAutoLabeler`: YOLO 모델 추론 엔진 인스턴스화
  * `src.ui.*` 및 `src.bbox.*` Mixin 클래스 전체

---

## 2. 주요 상태 변수 (State Variables)
* **폴더/프로젝트:** `projects`, `proj_of`, `folders`, `folder_images`, `images`, `view_filter`, `idx`
* **데이터 메모리:** `annotations`, `notes`, `review_status`, `done`, `passed`
* **뷰 & 편집:** `img`, `tkimg`, `scale`, `ox`, `oy`, `selected`, `pending`, `mode`
* **자동 추론:** `labeler`, `auto_pred`, `_batch_*`

---

## 3. 주요 기능 및 메서드 (Core Features)
* **앱 초기화 (`__init__`):** 메인 창 크기/최소 크기(`1100x680`) 설정, 상태 변수 초기화, `build_ui()` 호출, 글로벌 마우스 휠 이벤트 바인딩, `after(150, ...)` 비동기 세션 자동 복원
* **세션 연동 저장 (`save`, `save_and_next`):** 저장 실행 후 `remember_folder()`를 호출해 세션 위치 기록
* **안전 종료 처리 (`on_closing`):** 윈도우 X 버튼 클릭 시 미저장 작업물이 있을 경우 `askyesnocancel` 다이얼로그 출력

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **저장 실패 시 종료 방지:** 종료 다이얼로그에서 "예(저장)" 선택 후 입력값 누락 등으로 저장 실패 시 앱 종료 절차 즉시 중단
* **멀티 플랫폼 휠 바인딩:** Windows/macOS(`<MouseWheel>`) 및 Linux/WSL(`<Button-4>`, `<Button-5>`) 바인딩을 모두 제공하여 Cross-Platform 호환성 확보

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **비동기 세션 복원 타이밍:** UI 위젯의 레이아웃 및 크기 계산이 완료된 후 이전 폴더를 열기 위해 `after(150)` 지연 호출 방식을 사용함

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. 앱 실행 시 최소 크기 이상으로 메인 창이 정상 생성되는지 확인
  2. BBox 수정 후 미저장 상태에서 X 버튼 클릭 시 저장 확인 다이얼로그가 발생하는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-APP-01 (다중 상속 메서드 충돌 검증):** Python MRO(Method Resolution Order)에 따라 7개 Mixin 클래스가 상속되므로, 동일한 이름의 내부 메서드 정의 시 의도치 않은 오버라이딩이 발생하는지 점검 필요
