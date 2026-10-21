# 🛠️ auto_validator.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 폴더 오픈 시 데이터셋의 무결성을 기계적으로 자동 검사하는 유효성 검증(Validation) 모듈. 파일 짝 맞춤, 이미지 손상 여부, YOLO 라벨 포맷/클래스 범주/좌표 범주 오류 검사 후 리포트 CSV(`reports/validation_report.csv`) 저장 및 UI 알림 출력 전담
* **연동 모듈:**
  * `PIL.Image`: 이미지 파일 정상 오픈 및 해상도 검증
  * `tkinter.messagebox`: 오류 발생 시 사용자 알림 팝업 출력
  * `src.config`: `BASE_DIR`, `CLASS_IDS`, `UNUSED_CLASS`(4번), `IMG_EXTS` 상수를 참조하여 검사 기준 설정

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** 검사 대상 이미지 루트 경로(`img_root`), 프로젝트 정보 딕셔너리(`pj`), 부모 Tkinter 윈도우 객체(`parent_window`)
* **Output:**
  * 검출된 이슈 딕셔너리 리스트 `[{"checked_at", "img_root", "file", "level", "check", "detail"}, ...]`
  * `reports/validation_report.csv` 누적 기록 및 콘솔 출력 로그

---

## 3. 주요 검사 항목 및 기능 (Validation Checks)
* **이미지-TXT 짝 검사 (`_check_pair`):** 이미지만 존재(`TXT_MISSING`)하거나 TXT만 존재(`IMG_MISSING`)하는 결함 검출
* **이미지 파일 검사 (`_check_image`):** PIL 오픈 실패 (`IMG_OPEN`) 또는 해상도 0 이하 (`IMG_SIZE`) 검출
* **YOLO TXT 라벨 검사 (`_check_txt`):**
  * 이미지-TXT 기본명 불일치 (`NAME_MISMATCH`)
  * 라벨 라인당 열 개수 불일치 (`FORMAT`) 및 숫자 파싱 실패 (`PARSE`)
  * 4번 클래스 사용 (`CLASS_C4`) 및 범주 외 Class ID 사용 (`CLASS_ID`)
  * 정규화 좌표 범위 초과 (`COORD_RANGE`) 및 너비/높이 0 이하 (`COORD_SIZE`)

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **Non-Blocking 데이터 검증:** 검사 결과 오류가 발견되더라도 프로그램 로딩 및 작업을 차단하지 않고 계속 진행하도록 보장
* **요약 팝업 제어:** 오류 발생 시 상위 최대 5건의 내역만 요약 출력하여 UI 가독성 유지
* **CSV 인코딩 보장:** `utf-8-sig` 인코딩을 적용하여 Excel에서 리포트 열람 시 한글 깨짐 방지

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **Empty TXT 정상 인정:** 내용이 완전히 비어있는 TXT 라벨 파일은 학습용 음성 샘플(Negative Sample)로 정상 간주하여 오류로 처리하지 않음

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. 비정상 Class ID가 포함된 `.txt` 파일이 있는 폴더를 열었을 때 Validation 오류 팝업이 출력되는지 확인
  2. 오류 팝업을 닫은 후에도 이미지가 화면에 정상 로드되는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-VAL-01 (리포트 CSV 아펜드 누적):** 동일한 폴더를 반복해서 열 때마다 `validation_report.csv`에 동일한 오류 항목이 중복 덧붙여지는 현상이 발생하므로, 파일별 유니크 키 관리 또는 정기 플러시 정책 검토 필요
