# 1. 개요
라벨링 애플리케이션의 핵심 컨트롤러인 `LabelingApp` 메인 클래스입니다. Tkinter 루트 윈도우 초기화, 전체 애플리케이션 상태(폴더, 이미지, 뷰, 마우스, YOLO 추론 등) 정의, 다양한 Mixin 기능 컴포넌트들의 다중 상속 조립, 그리고 마우스 휠 이벤트 바인딩 및 프로그램 시작/종료(저장 확인 및 설정 기억) 라이프사이클을 총괄합니다.

# 2. 파일 간 연결 구조
- 상속 관계: `LayoutMixin`, `FolderMixin`, `NavigationMixin`, `ViewMixin`, `EditMixin`, `AutoLabelMixin`, `StorageMixin` 등 모든 기능별 Mixin 클래스를 다중 상속하여 구성됨
- 외부 의존성: `src.yolo.auto_label.YoloAutoLabeler` 모듈을 로드하여 AI 자동 라벨링 기능 연동

# 3. 주요 상태 변수

| 분류 | 주요 인스턴스 변수 | 역할 |
| :--- | :--- | :--- |
| **폴더 / 이미지 상태** | `self.projects`, `self.folders`, `self.images` | 로드된 프로젝트 목록, 디렉토리별 이미지 맵핑 구조, 필터가 적용된 최종 작업 이미지 리스트 |
| **작업 데이터** | `self.annotations`, `self.notes`, `self.review_status` | 이미지별 바운딩 박스 목록, 이슈 노트, 검수 상태(1차/2차 등)를 저장하는 딕셔너리 |
| **진행 관리** | `self.done`, `self.passed` | 저장 완료된 이미지 세트 및 진행률 계산용 통과 이미지 세트 |
| **뷰 / 마우스 상태** | `self.scale`, `self.ox`, `self.oy`, `self.mode`, `self.zoom_mode` | 캔버스 줌 배율, 오프셋, 현재 마우스 상호작용 모드(press, draw, pan 등) 및 확대 모드 플래그 |
| **자동 추론 상태** | `self.labeler`, `self.auto_pred` | YOLO 자동 라벨러 인스턴스 및 일괄 추론 결과 캐시 딕셔너리 |

# 4. 주요 실행 흐름
- **초기화 및 UI 빌드 (`__init__`):**
  - 앱 창 기본 설정(제목, 크기 제한, 창 닫기 프로토콜 설정)을 마치고 각종 상태 변수를 빈 값으로 초기화합니다.
  - `self.build_ui()`를 호출하여 전체 화면 레이아웃을 그리고, 마우스 휠 이벤트(`<MouseWheel>`, `<Button-4>`, `<Button-5>`)를 캔버스에 바인딩합니다.
  - `root.after`를 통해 프로그램 실행 직후 마지막 작업 폴더를 자동으로 불러오는 `_auto_load_last_folder()`를 예약합니다.
- **자동 폴더 로드 (`_auto_load_last_folder`):**
  - 설정 파일에 기록된 마지막 폴더(`picked`)와 보던 이미지(`last_img`) 정보를 읽어와 선택 창 없이 곧바로 이전 작업 환경을 복원합니다.
- **저장 및 종료 관리 (`save`, `save_and_next`, `on_closing`):**
  - 저장 동작 시 수퍼클래스의 저장 로직을 수행하고, 성공 시 현재 열린 폴더와 이미지 상태를 설정 파일에 기억(`remember_folder`)합니다.
  - 창을 닫을 때(`on_closing`) 저장되지 않은 작업물이 있으면 대화상자를 띄워 [예/아니요/취소]에 따라 안전하게 저장 후 종료하거나 취소하도록 처리합니다.

# 5. 확인 및 개선 사항
- 모든 Mixin 클래스들의 상태 변수와 메서드가 `LabelingApp` 인스턴스 하나를 중심으로 유기적으로 공유되도록 구조가 매우 깔끔하게 설계되었습니다.
- 운영체제별(Windows, macOS, Linux/WSL)로 상이한 마우스 휠 이벤트 시퀀스를 모두 포괄하여 바인딩함으로써 크로스 플랫폼 호환성을 높였습니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- ********* (코드 내 명시된 변경 이력 없음)