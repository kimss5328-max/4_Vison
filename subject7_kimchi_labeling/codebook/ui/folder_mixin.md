# 1. 개요
프로젝트 폴더 구성, 디렉토리 파싱, 마지막으로 작업한 폴더 경로 기억, 작업 목록(TreeView) 갱신, 단계별(1차, 2차 등) 보기 필터링, 그리고 백그라운드 데이터 검증(Validation) 실행 등 폴더 관리와 목록 UI를 전담하는 Mixin 클래스입니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (GUI 메인 클래스에 다중 상속되어 `FolderMixin` 형태로 사용됨)
- 외부 함수 호출: `src.validation.auto_validator`의 `run_validation`을 백그라운드 스레드에서 호출

# 3. 주요 상태 변수

| 분류 | 주요 변수 / 리스트 | 역할 |
| :--- | :--- | :--- |
| **프로젝트 정보** | `self.projects`, `self.proj_of` | 로드된 프로젝트들의 정보(dict) 리스트 및 각 이미지 경로(`p`)가 어떤 프로젝트에 속하는지 매핑한 딕셔너리 |
| **폴더 구성** | `self.folders`, `self.folder_keys` | 선택된 프로젝트 내의 하위 디렉토리별 이미지 리스트 및 UI 콤보박스 선택을 위한 키 리스트 |
| **작업 대상** | `self.folder_images`, `self.images` | 현재 선택된 폴더의 전체 이미지 리스트 및 단계 필터(`self.view_filter`)가 적용되어 화면 목록(Listbox)에 표시될 이미지 리스트 |
| **필터 상태** | `self.view_filter` | 단계 보기 콤보박스의 현재 선택 값 (`"all"`, `"1차"`, `"2차"`, `"review"`, `"final"`) |

# 4. 주요 실행 흐름
- **폴더 찾기 및 열기 (`open_folder`, `_find_roots`):**
  - 사용자가 선택한 디렉토리를 탐색하여 `images`와 `labels` 폴더가 동시에 존재하는 유효한 프로젝트 구조를 재귀적으로 찾습니다.
  - 선택한 경로의 원본 파일 및 이미지를 스캔하여 `self.projects`와 `self.folders` 구조로 맵핑합니다.
- **백그라운드 검증 (Validation):**
  - 폴더를 열 때 `_run_val_bg()` 내부 함수를 통해 데몬 스레드(Daemon Thread)에서 `run_validation`을 호출, UI 블로킹 없이 데이터 무결성을 검증합니다.
- **마지막 상태 저장/불러오기 (`remember_folder`, `save_last_folder`, `load_last_folder`):**
  - 작업 폴더 경로와 마지막으로 보던 이미지 경로를 `~/.labeling_tool_config.json`(`SETTINGS_PATH`)에 저장하고 프로그램 재시작 시 자동으로 불러옵니다.
- **단계별 필터 및 카운트 (`apply_filter`, `update_stage_counts`):**
  - `STAGE_FILTERS` 기준(전체, 1차, 2차 등)으로 `self.folder_images`를 필터링하여 작업 리스트(`self.images`)를 구성하고 우측 UI의 카운트와 Listbox를 즉시 갱신합니다.
- **진행률 표시 (`update_progress`):**
  - 필터 적용 여부와 관계없이 현재 선택된 폴더 내 전체 이미지 대비 통과(`self.passed`)된 이미지의 비율을 계산하여 Progress Bar에 표시합니다.

# 5. 확인 및 개선 사항
- 이미지 리스트 및 폴더 스캔 시 프로그램이 자체적으로 생성한 결과 폴더(ex: `*_labeled`, `train_done` 등)는 제외(`self.is_output_dir`)하여 중복 데이터 로드를 방지합니다.
- 폴더가 변경되거나 리스트가 갱신되기 직전, 현재 화면에 임시로 그려진 박스(`pending`)를 삭제하고(`discard_pending`) 작성 중인 이슈 노트를 임시 저장(`save_current_note`)하여 안전하게 화면을 전환합니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- 백그라운드에서 Validation 자동 실행 추가 (`threading.Thread` 활용)