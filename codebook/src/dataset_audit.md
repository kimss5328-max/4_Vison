# 1. 개요
최종 승인된 데이터셋(`final/img` 및 `final/txt`)을 대상으로 전수 검증 및 품질 감사를 수행하는 독립형 감사(Audit) 스크립트 모듈입니다. 전역 데이터 대장(`dataset_manifest.csv`)과 연동하여 데이터 수량 일치 여부, 중복 스템, YOLO 포맷 및 바운딩 박스 정합성, 그리고 원본(`raw`) 대조군과의 누락 여부를 종합적으로 분석하고 리포트 CSV 파일들을 생성합니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (독립 실행형 감사 스크립트)
- 외부 의존성 및 호출 관계: 프로젝트 루트의 `manifests/dataset_manifest.csv`, `data/` 아래의 결과 폴더 구조(`datasetX_result/final`, `raw/img` 등)를 참조하며, 실행 결과로 `reports/` 디렉토리에 요약 및 이슈 리포트 CSV를 출력

# 3. 주요 상태 변수 및 핵심 함수

| 분류 | 함수 / 상수 | 역할 |
| :--- | :--- | :--- |
| **파일 수집 및 그룹화** | `collect`, `group_by_stem`, `pick_canonical` | 지정된 경로에서 이미지 및 텍스트 파일을 재귀적으로 수집하고, 파일 스템(Stem) 기준으로 그룹화하여 중복 파일을 식별 |
| **포맷 검증** | `validate_yolo_row` | 개별 YOLO 라벨 행의 컬럼 수, 클래스 범위(`0 ~ NUM_CLASSES-1`), 중심 좌표 및 너비/높이 정규화 범위(`0.0 ~ 1.0`) 검증 |
| **대장 로드** | `load_manifest` | `dataset_manifest.csv`를 읽어 데이터셋별 스템 메타인데스(`original_split`, `scene_type`) 구축 |
| **감사 및 비교** | `audit_dataset`, `audit_raw_vs_final` | 데이터셋별 수량 일치성, 짝(Pair) 오류, 빈 라벨, 클래스 분포, 스플릿 및 씬 타입 집계를 수행하고 원본(`raw`)과 최종본 간 누락 대조 분석 |

# 4. 주요 실행 흐름
- **대장 로드 및 검증 (`load_manifest`):**
  - 전역 데이터 대장에서 필요한 컬럼 유무를 확인하고, 각 이미지별 원본 분할 정보와 씬 유형 메타데이터를 메모리에 로드합니다.
- **데이터셋 감사 (`audit_dataset`):**
  - `final/img`와 `final/txt` 경로를 대상으로 스템 중복(`DUPLICATE_STEM`), 페어 누락(`PAIR_ERROR`), YOLO 라벨 문법 및 범위 오류(`CLASS_RANGE`, `CENTER_RANGE`, `SIZE_RANGE`) 등을 탐지합니다.
  - 매니페스트 기대값과 실제 발견된 파일 개수를 비교하여 수량 일치 여부(`QUANTITY_MISMATCH`)를 판정합니다.
- **원본 대조 (`audit_raw_vs_final`):**
  - `raw/img`의 전체 스템 목록과 최종 승인된 데이터셋(`final_all`)을 교차 비교하여 누락된 파일(`RAW_NOT_IN_FINAL`)이나 불필요한 파일을 추적합니다.
- **리포트 출력 (`main` 및 `write_csv`):**
  - 감사 결과를 집계하여 `dataset_summary.csv`, `audit_issue.csv`, `bbox_per_image.csv` 파일로 안전하게 기록합니다.

# 5. 확인 및 개선 사항
- 엄격한 YOLO 바운딩 박스 규격 검증과 스템 해시 비교(`file_hash`)를 통해 데이터 무결성과 중복 여부를 정밀하게 감시합니다.
- 매니페스트가 없을 경우 기존 폴백(Fallback) 개수 기준으로 유연하게 방어 동작을 수행하도록 설계되었습니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- 데이터셋별 최종 결과물 감사, 매니페스트 메타데이터 연동 및 `reports/` 내 CSV 감사 리포트 자동 생성 기능 추가