# 🛠️ dataset_audit.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 정답 데이터셋 및 `dataset_manifest.csv` 대상 정밀 감사(Audit) 스크립트. 이미지-TXT 짝 매핑, YOLO 좌표 유효성, 중복 파일, Class 4 오사용, RAW 대비 유실 검사 및 요약 CSV 출력 전담
* **연동 모듈:** `csv`, `hashlib`, `re`, `pathlib.Path`

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** `final/img`, `txt`, `manifests/dataset_manifest.csv`, `raw/img`
* **Output:** `reports/dataset_summary.csv`, `audit_issue.csv`, `bbox_per_image.csv`

---

## 3. 주요 검수 규칙 및 기능 (Audit Rules & Functions)
* **YOLO 라벨 검증 (`validate_yolo_row`):** 컬럼 수(5개), Class ID 범주, 좌표 중심 및 크기 범주(0.0~1.0) 검사
* **중복 및 짝 감사 (`audit_dataset`):** STEM 기준 파일 모음, MD5 해시 비교, 이미지-TXT 짝 누락(`PAIR_ERROR`), Class 4 수집
* **RAW vs FINAL 비교 (`audit_raw_vs_final`):** RAW 원본 대비 최종 결과물 유실 파일 추적

---

## 4. 예외 처리 및 시스템 안정성 (Validation & Safety)
* **UTF-8-BOM 적용:** 출력 CSV에 `utf-8-sig` 인코딩을 적용하여 Excel 한글 깨짐 방지
* **Manifest 부재 Fallback:** `dataset_manifest.csv` 부재 시 `FALLBACK_EXPECTED` 수량 기준(500장/400장)으로 자동 전환

---

## 5. 설계상 확정된 한계 및 제약 (Intentional Constraints)
* **독립 스크립트 실행:** 본 스크립트는 메인 UI 앱과 독립적으로 동작하는 배치 감사용 도구임

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:** `python src/dataset_audit.py` 실행 시 `reports/` 폴더 내 3개 CSV 파일이 정상 생성되는지 확인

---

## 7. 이슈 트래커 이관 목록 (Check Needed)
* **#ISSUE-AUD-01 (대용량 파일 해시 메모리):** `file_hash()` 함수에서 `p.read_bytes()`로 파일 전체를 메모리에 로드하므로, 고용량 이미지 수천 장 검사 시 메모리 점유율 확인 필요
