# 1. 개요
작업 대상 폴더의 구조 분석 및 프로젝트 구성, 이미지 파일 수집, 단계별 필터링(View Filter), 전역 진행률 계산, 그리고 마지막 작업 환경 설정 복원(`save_last_folder` / `load_last_folder`)을 전담하는 폴더 관리 Mixin 클래스입니다. 아울러 백그라운드 스레드 기반의 자동 검증(`start_validation`)을 연동하여 이미지와 라벨의 정합성을 실시간으로 점검합니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (GUI 메인 클래스에 다중 상속되어 `FolderMixin` 형태로 사용됨)
- 외부 의존성 및 호출 관계: 
  - `src.config`의 설정 상수(`IMG_EXTS`, `PICK_START_DIR`, `SETTINGS_PATH`, `DATASET_NAMES`, `RESULT_SUFFIX` 등)를 참조
  - `src.validation.auto_validator` 모듈을 통해 원본 이미지 및 라벨 검사 수행
  - `src.bbox.manifest`의 `split_of` 함수를 활용해 이미지 폴더 구조 분할(`train`/`validation`) 판별

# 3. 주요 상태 변수 및 자료구조

| 분류 | 주요 인스턴스 변수 | 역할 |
| :--- | :--- | :--- |
| **프로젝트 및 폴더 구조** | `self.projects`, `self.proj_of`, `self.folders` | 로드된 프로젝트 메타 dict 리스트, 이미지 파일 경로별 소속 프로젝트 맵핑, 디렉토리별 이미지 리스트 사전 |
| **작업 목록 관리** | `self.folder_images`, `self.images`, `self.view_filter` | 선택된 폴더의 전체 이미지 집합, 현재 필터가 적용된 최종 작업 이미지 리스트, 현재 활성화된 단계 보기 필터 키 |
| **상태 집합** | `self.done`, `self.passed`, `self.auto_pred` | 저장 완료된 이미지 세트, 진행률 계산용 통과 이미지 세트, YOLO 일괄 추론 결과 캐시 |

# 4. 주요 실행 흐름
- **폴더 열기 및 프로젝트 분석 (`open_folder`, `_find_roots`, `bases_of`):**
  - 사용자가 선택한 디렉토리에서 `images`와 `labels` 폴더 구조를 탐색하여 프로젝트 루트를 식별하고, 프로그램 결과 디렉토리(`_result`)나 보호된 시스템 경로는 원본 열기 대상에서 엄격하게 차단합니다.
  - 탐색된 이미지 파일들을 프로젝트별로 그룹화하고, 마지막 작업 폴더 설정을 외부에 JSON(`~/.labeling_tool_config.json`) 형태로 저장(`save_last_folder`)하여 다음 실행 시 자동 복원합니다.
- **백그라운드 자동 검증 (`start_validation`):**
  - 폴더 로드 직후 파이썬 `threading.Thread`를 통해 프로젝트별 이미지-라벨 쌍과 고아(Orphan) 라벨 검사를 비동기로 수행하고, 결과를 `root.after` 풀링을 통해 메인 스레드 안전하게 안내 창으로 띄웁니다.
- **단계 보기 및 필터링 (`apply_filter`, `on_stage_filter_select`):**
  - 전체 이미지 목록에서 각 이미지의 저장 단계(`latest_stage`), 편집 임시 저장 여부(`is_in_progress`), 이슈 기록 여부(`has_issue`)를 분석하여 동적으로 단계별 필터링을 적용합니다.
  - 단계 선택 콤보박스에 각 상태별 개수를 실시간으로 집계하여 표시합니다(`update_stage_counts`).
- **진행률 및 리스트 갱신 (`update_progress`, `refresh_image_list`):**
  - 폴더 전체 기준으로 완료된 이미지 비율을 계산하여 프로그레스 바와 퍼센트 문자열을 갱신하며, 저장 완료된 항목은 초록색(`DONE_LIST_COLOR`), 추론 대기 항목은 주황색(`AUTO_LIST_COLOR`)으로 시각화합니다.

# 5. 확인 및 개선 사항
- 프로그램 폴더 내부의 결과물 디렉토리나 시스템 코드가 원본으로 실수로 열리는 사고를 방지하기 위해 `is_result_path`와 `PROGRAM_ROOT` 기반의 강력한 안전 차단 로직이 구현되어 있습니다.
- 백그라운드 스레드와 `queue.Queue`를 활용해 대용량 이미지 검사 중에도 UI가 멈추지 않는 매끄러운 사용자 경험(UX)을 제공합니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- 외부 설정 파일(`~/.labeling_tool_config.json`)을 이용한 마지막 폴더 자동 복원 및 백그라운드 원본 자동 검증(`run_validation`) 연동 구조 도입