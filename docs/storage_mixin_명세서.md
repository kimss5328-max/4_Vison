# 🛠️ storage_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 라벨링 결과물의 단계별 폴더 이동(`data/raw`, `work/1차`, `work/2차`, `final`, `issues`), 이력 관리(`data/csv/`), 검수 오버레이 이미지 생성(`reviews/`) 및 대장 기록(`manifests/dataset_manifest.csv`) 전담
* **연동 모듈:**
  * `functools.lru_cache`: 한글 폰트 로딩 성능 최적화
  * `PIL (ImageDraw, ImageFont)`: 검수용 이미지(`reviews/`) 내 BBox 및 한글 클래스 오버레이 렌더링
  * `src.config`: 저장 경로 구조(`STAGE_DIRS`, `RAW_DIR` 등), 폰트 경로, Class 목록 참조
  * `src.bbox.geometry`: 좌표 저장 및 복원 시 YOLO 정규화 변환 함수 참조

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** BBox 리스트, 현재 이미지 경로, 작업자/검수자 정보, 작성된 이슈 노트 텍스트, 설정된 검수 단계
* **Output:**
  * 단계별 이미지 및 YOLO `.txt` 라벨 파일
  * 검수 바운딩 박스가 주입된 `.jpg` 오버레이 이미지 (`reviews/`)
  * 이미지별 이력 기록 CSV (`data/csv/파일명.csv`)
  * 데이터셋 대장 파일 (`manifests/dataset_manifest.csv`)

---

## 3. 주요 기능 및 메서드 (Core Features)
* **결과 저장소 자동 구축 (`prepare_out_dir`, `ensure_out_dir`):**
  * 폴더 로드 시 `data/(raw, work, final, issues, csv)`, `reviews/`, `manifests/` 디렉터리 구조 자동 준비 및 원본 `data/raw` 동기화
* **자동 작업 저장 (`autosave_work`):**
  * 이미지 편집 및 BBox 변경 시 이력 기록 없이 `data/work/1차/txt` 내 정규화 라벨 파일만 백그라운드에서 실시간 갱신
* **정식 저장 프로세스 (`save`, `save_and_next`):**
  * 4번(고무장갑 - 미사용 클래스) BBox 검출 시 삭제 동의 확인 후 저장 진행
  * `_append_history`: 이미지별 이력 CSV 파일에 저장 시점, 좌표, 작업자/검수자 ID 덧붙이기(Append) 기록
  * `_append_manifest`: Master 대장 파일(`dataset_manifest.csv`) 내 해당 파일 행 갱신(Upsert)
  * `_write_preview`: `reviews/` 폴더 저장 시 한글 라벨 폰트(`PREVIEW_FONTS`)를 찾아 이미지 위에 BBox를 그려 렌더링
  * 이전 파일 위치 삭제 및 신규 단계 폴더로 파일 이동

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **BBox 오버레이 위치 자동 보정:** `_write_preview` 실행 시 이름표가 이미지 상단 경계를 벗어날 경우 박스 아래쪽으로 자동 전환
* **Strict 데이터 덧붙이기(Append-Only):** 이력 CSV 및 이슈 기록 시 기존 데이터를 수정/삭제하지 않고 덧붙여 작업 이력 손실 방지
* **무효 클래스 원천 차단:** 클래스가 미지정되었거나 `ISSUE_ID`인 BBox는 `_label_boxes()` 필터를 거쳐 학습용 YOLO txt 파일에 저장되는 것을 차단
* **한글 폰트 Fallback:** 시스템 내 지정된 한글 폰트(`PREVIEW_FONTS`)가 존재하지 않을 경우 기본 폰트로 안전 전환하여 프로그램 작동 유지

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **결과 저장소 구조 고정:** 프로그램 결과물 저장 구조(`data/raw`, `data/work`, `reviews`, `data/final`)는 프로젝트 데이터 규격에 고정되어 있으므로 폴더 구조 변경을 허용하지 않음
* **작업 중 자동 저장 제한:** `review` 및 `final` 단계에 있는 이미지는 완료된 검수 승인 기록을 보호하기 위해 `autosave_work` 대상에서 제외됨

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. 이미지를 1차 상태로 저장 시 `data/work/1차/` 경로로 이미지 및 `.txt` 라벨이 생성되는지 확인
  2. review 상태로 저장 시 `reviews/` 폴더 내에 바운딩 박스 및 한글 클래스 명칭이 그려진 오버레이 이미지가 정상 생성되는지 확인
  3. `manifests/dataset_manifest.csv` 파일을 열었을 때 방금 작업한 파일의 상태가 `status` 컬럼에 업데이트되었는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-STO-01 (동기 I/O 지연 검증):** `save()` 실행 시 이력 CSV, YOLO txt, `reviews/` 오버레이 렌더링, `dataset_manifest.csv` 생성을 단일 메인 스레드에서 순차 처리하므로, 고해상도 이미지 동기 저장 시 프레임 지연 측정 필요
* **#ISSUE-STO-02 (트랜잭션 미지원 예외):** 저장 도중 Disk Full 등 `OSError` 발생 시 일부 파일만 생성된 상태로 중단될 수 있으므로, 원자성(Atomicity) 보장을 위한 파일 작성 예외 처리 강화 검토 필요
