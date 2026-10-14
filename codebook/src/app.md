# 1. 개요
라벨링 애플리케이션의 핵심 컨트롤러이자 진입점인 `LabelingApp` 메인 클래스입니다. Tkinter 루트 윈도우 초기화, 다수의 기능별 Mixin 클래스(`StatsMixin` 포함) 다중 상속 조립, 애플리케이션 전역 상태 변수 관리, 그리고 마우스 휠 이벤트 및 시작·종료 라이프사이클을 총괄합니다.

# 2. 파일 간 연결 구조
- 상속 관계: `LayoutMixin`, `FolderMixin`, `NavigationMixin`, `ViewMixin`, `EditMixin`, `AutoLabelMixin`, `StorageMixin`, `StatsMixin` 등 8개의 Mixin 클래스를 다중 상속하여 구성됨
- 외부 의존성: `src.yolo.auto_label.YoloAutoLabeler` 모듈을 연동하여 AI 자동 라벨링 기능을 지원

# 3. 주요 상태 변수

| 분류 | 주요 인스턴스 변수 | 역할 |
| :--- | :--- | :--- |
| **폴더 / 이미지 상태** | `self.projects`, `self.folders`, `self.images` | 로드된 프로젝트 목록, 디렉토리별 이미지 맵핑 구조, 필터가 적용된 최종 작업 이미지 리스트 |
| **작업 및 이력 데이터** | `self.annotations`, `self.notes`, `self.note_base`, `self.baseline` | 이미지별 바운딩 박스 목록, 이슈 노트, 불러온 이슈 기록, 수정 권한 비교를 위한 원본 박스 기준선 |
| **권한 및 흐름 상태** | `self.cur_flow`, `self.edit_ok`, `self.edit_why` | 현재 이미지의 단계 흐름(`Flow`), 현재 이미지 수정 권한 여부 및 불가능한 이유 메시지 |
| **진행 및 뷰 상태** | `self.done`, `self.passed`, `self.scale`, `self.ox`, `self.oy` | 저장 완료된 이미지 세트, 진행률 계산용 통과 이미지 세트, 캔버스 줌 배율 및 오프셋 좌표 |
| **자동 추론 상태** | `self.labeler`, `self.auto_pred` | YOLO 자동 라벨러 인스턴스 및 일괄 추론 결과 캐시 딕셔너리 |

# 4. 주요 실행 흐름
- **초기화 및 UI 빌드 (`__init__`):**
  - 창 기본 설정(제목, 크기 제한, 창 닫기 프로토콜)을 마치고 각종 상태 변수를 빈 값으로 초기화합니다.
  - `self.build_ui()`를 호출하여 화면 레이아웃을 구성하고, 크로스 플랫폼 마우스 휠 이벤트(`<MouseWheel>`, `<Button-4>`, `<Button-5>`)를 캔버스에 바인딩합니다.
  - `root.after`를 통해 실행 직후 마지막 작업 폴더를 자동으로 불러오는 `_auto_load_last_folder()`를 예약합니다.
- **자동 폴더 로드 (`_auto_load_last_folder`):**
  - 설정 파일에 기록된 마지막 폴더(`picked`)와 보던 이미지(`last_img`) 정보를 읽어와 별도의 선택 창 없이 이전 작업 환경을 즉시 복원합니다.
- **저장 및 종료 관리 (`save`, `save_and_next`, `on_closing`):**
  - 저장 시 수퍼클래스의 저장 동작을 처리하고 열린 폴더 및 보던 이미지 경로를 설정에 기억(`remember_folder`)합니다.
  - 창을 닫을 때(`on_closing`) 저장되지 않은 작업물이나 변경 사항이 존재하면 대화상자를 띄워 [예/아니요/취소] 선택에 따라 안전하게 처리합니다.

# 5. 확인 및 개선 사항
- `StatsMixin`이 새롭게 추가 조립되어 프로젝트 전반의 통계 및 데이터 분석 기능을 유기적으로 뒷받침할 수 있도록 확장되었습니다.
- `note_base` 및 `baseline` 등의 필드가 도입되어 기존 대비 세밀한 이슈 이력 관리와 검수자 수정 내용 추적이 가능해졌습니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- `StatsMixin` 추가 및 상태 변수(`note_base`, `baseline`, `cur_flow`, `edit_ok` 등) 확장 조립