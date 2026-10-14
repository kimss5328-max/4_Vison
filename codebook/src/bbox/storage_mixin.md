# 1. 개요
데이터셋별 결과 디렉토리(ex: `visol04/data/<데이터셋>_result/`)를 관리하고, 이미지별 바운딩 박스 라벨 및 이슈 노트를 단계별 폴더(`work/pass`, `edited`, `review`, `view`, `final`, `working` 등)로 이동·저장하며, 이미지별 이력(CSV)과 전역 데이터 대장(`manifest`)을 안전하게 업서트(Upsert)하는 영속성 및 저장 전담 Mixin 클래스입니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (GUI 메인 클래스에 다중 상속되어 `StorageMixin` 형태로 사용됨)
- 외부 모듈 및 라이브러리 의존성: 
  - `src.bbox.manifest` 모듈의 데이터 대장 처리 함수(`find_row`, `build_row`, `upsert`, `split_of`) 호출
  - `src.bbox.workflow`의 `Flow`, `read_events` 등을 통한 작업 권한 및 단계 검증
  - `src.validation.rules`의 클래스 검증 및 잠금(Locked) 처리 규칙 활용
  - `PIL.ImageDraw`, `ImageFont` 등을 통한 시각화 프리뷰 이미지 생성

# 3. 주요 상태 변수 및 헤더 구조

| 분류 | 주요 상수 및 변수 | 역할 |
| :--- | :--- | :--- |
| **인증 및 역할** | `WHO_COLS` | 작업자 및 검수자 정보(이름, ID 등)를 기록하기 위한 동적 열 이름 리스트 |
| **이력 구조** | `CSV_HEADER` | 이미지별 이력 CSV 파일의 열 구성 정의 (`image`, `stage`, `from`, `class_id`, `x_center`, `review_action`, `saved_at` 등) |
| **상태 변수** | `self.baseline`, `self.note_base` | 검수자 수정 내용 비교를 위한 원본 박스 기준선(`oid`, 클래스, YOLO 좌표) 및 불러온 이슈 기록 베이스 딕셔너리 |

# 4. 주요 실행 흐름
- **결과 폴더 및 구조 준비 (`prepare_out_dir`, `set_out_dir`):**
  - 데이터셋별 결과 디렉토리 구조를 생성하며, Git 추적을 위한 `.gitkeep` 파일 및 클래스 정의 파일(`classes.txt`)을 자동으로 배치합니다.
- **임시 작업 저장 (`autosave_work`):**
  - 사용자가 편집을 진행할 때마다 원본 이미지를 건드리지 않고 `working/txt` 경로에 현재 박스 상태를 실시간으로 임시 저장하여 예기치 않은 종료 시에도 작업을 복구할 수 있게 합니다.
- **저장 및 커밋 (`save`, `_commit`):**
  - `workflow.Flow`를 통해 현재 사용자의 역할과 상태 변경 권한을 확인하고, `scene_type` 및 필수 사유(REVIEW 등)를 검증합니다.
  - 지정 불가 클래스 검증(`_ready_boxes`)을 거친 뒤, 이미지별 이력 CSV에 박스별 변경 사항을 추가(`_append_history`)합니다.
  - 선택된 단계 폴더로 이미지 사본과 YOLO 텍스트, 그리고 클래스 이름이 그려진 프리뷰 이미지(`_write_preview`)를 안전하게 이동·저장합니다.
  - 데이터 대장(`dataset_manifest.csv`)을 최신 상태로 업서트(`_update_manifest`)하고 임시 작업 파일을 정리합니다.
- **이슈 노트 관리 (`issue_log`, `_append_issue`):**
  - 기존에 기록된 이슈 로그 뒤에 이번에 새로 작성한 내용을 시간대별로 덧붙이며, 사본 이미지와 라벨을 `issues/` 폴더에 누적 보존합니다.

# 5. 확인 및 개선 사항
- 원본 데이터 폴더는 읽기 전용으로 엄격하게 다루며, 모든 결과물과 이력은 독립된 결과 디렉토리에 격리 저장하여 원본 손상을 원천 방지합니다.
- 기존 이력(CSV, 이슈 로그)을 절대 덮어쓰거나 지우지 않고 행 단위로 덧붙이는(Append) 방식으로 기록하여 완벽한 감사 추적(Audit Trail)을 보장합니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- 데이터셋별 결과 폴더 분리 (`visol04/data/<dataset>_result/`) 및 전역 `manifest` 업서트 구조 전면 도입