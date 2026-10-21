# 🛠️ config.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 프로그램 전체에서 공통 참조하는 경로, 디렉터리 구조, 클래스 체계, 검수 단계, UI 색상, 폰트, 조작 파라미터를 단일 출처(Single Source of Truth)로 관리
* **연동 모듈:** `os` 모듈을 사용해 시스템 경로 및 홈 디렉터리 경로 계산

---

## 2. 주요 상수 그룹 (Defined Constants)
* **경로:** `BASE_DIR`, `SETTINGS_PATH`(`~/.labeling_tool_config.json`), `STAGE_DIRS`, `MANIFEST_FILE`
* **클래스:** `CLASS_NAMES`, `UNUSED_CLASS`(4번), `CLASS_IDS`(`[0, 1, 2, 3, 5, 6]`)
* **단계/권한:** `STAGES`, `WORKER_STAGES`, `REVIEWER_STAGES`, `STAGE_STATUS`
* **UI/조작:** `COLORS`, `PREVIEW_FONTS`, `HANDLE_R`(7px), `MAX_ZOOM`(20배), `WHEEL_STEP`(1.2배)

---

## 3. 예외 처리 및 시스템 안정성 (Validation & Safety)
* **YOLO Class ID 일치 유지:** 4번 클래스를 UI 선택 목록(`CLASS_IDS`)에서는 제외하되 전체 배열(`CLASS_NAMES`) 인덱스는 유지하여 YOLO 모델 ID 파이프라인의 깨짐 방지
* **멀티 OS 폰트 폴백:** Windows, WSL, Ubuntu 환경의 한글 폰트 경로(`PREVIEW_FONTS`)를 다중 정의하여 폰트 부재 예외 방지

---

## 4. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **경로 구조 고정:** 결과 저장 디렉터리 체계는 프로젝트 규격에 고정되어 있어 임의 변경을 허용하지 않음

---

## 5. 테스트 및 확인 방법 (Test)
* **Smoke Test:** `config.py` 임포트 시 `CLASS_IDS` 리스트에 `4`가 제외된 `[0, 1, 2, 3, 5, 6]`이 생성되는지 확인

---

## 6. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-CFG-01 (시작 디렉터리 하드코딩):** `PICK_START_DIR` 경로(`~/exe_01`)가 특정 환경 위주로 설정되어 있어 존재하지 않을 경우 홈 디렉터리로 전환되는 로직의 유연성 점검 필요
