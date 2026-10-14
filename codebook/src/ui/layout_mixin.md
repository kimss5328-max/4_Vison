# 1. 개요
라벨링 프로그램의 전체 Tkinter 사용자 인터페이스(UI) 배치를 총괄하는 레이아웃 구성 전담 Mixin 클래스입니다. 루트 윈도우의 그리드(Grid) 격자 구조를 설정하고, 상단 바, 왼쪽 폴더/이미지 사이드바, 중앙 캔버스 및 하단 도구 모음, 그리고 오른쪽의 네비게이션, 클래스 분류, YOLO 자동 라벨링 제어 및 검수/이슈 패널을 체계적으로 조립합니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (GUI 메인 클래스에 다중 상속되어 `LayoutMixin` 형태로 사용됨)
- 외부 의존성 및 호출 관계: 
  - `src.config`의 컬러, 폰트, 단계 필터 상수 참조
  - `src.ui.panels`의 컴포넌트 패널(`PersonPanel`, `ReviewPanel`, `HistoryPanel`, `ScenePanel`) 임포트 및 인스턴스화
  - `src.bbox.workflow`의 `people_labels` 연동
  - `src.validation.rules`의 클래스 유효성 및 표시 이름 함수 활용

# 3. 주요 상태 변수 및 위젯 구조

| 분류 | 주요 위젯 및 인스턴스 변수 | 역할 |
| :--- | :--- | :--- |
| **창 구성** | `self.root`, `self.statusBar` | 메인 윈도우 루트 및 하단 전역 상태 표시줄(Status Bar) |
| **사이드바** | `self.sidebar`, `self.folderSelect`, `self.imageList` | 폴더 분류 선택 콤보박스 및 디렉토리 내 이미지 목록 리스트박스 |
| **캔버스 영역** | `self.imageCanvas`, `self.resetViewBtn`, `self.zoomBtn` | 이미지 렌더링 및 박스 인터랙션용 캔버스, 하단 뷰 조작 버튼 모음 |
| **우측 패널** | `self.classList`, `self.labelList`, `self.labelDetail` | 클래스 선택 리스트박스, BBox 크기 정보 트리뷰 및 상세 스펙 입력 필드 |
| **제어 패널** | `self.reviewPanel`, `self.personPanel`, `self.scenePanel`, `self.issueNote` | 검수 상태, 작업자 정보, 씬 타입(Scene Type), 이슈 노트 입력 영역 |

# 4. 주요 실행 흐름
- **UI 일괄 빌드 (`build_ui`):**
  - 루트 윈도우의 그리드 행/열 가중치(`weight`)를 설정하여 반응형 레이아웃 기반을 마련하고, 상단 바, 사이드바, 센터 캔버스, 우측 제어 패널 순으로 위젯들을 배치합니다.
- **컴포넌트별 배치 세부 로직:**
  - 상단 바(`_build_top_bar`): 사이드바 토글 버튼과 전역 작업 진행률 프로그레스 바를 배치합니다.
  - 왼쪽 사이드바(`_build_sidebar`): 폴더 열기 버튼, 저장 위치 표시, 단계 선택 콤보박스, 그리고 이미지 리스트를 배치합니다.
  - 중앙 영역(`_build_center`): 배경이 어두운 대형 캔버스(`imageCanvas`)와 줌/리셋 하단 도구 모음을 구성하고, 통계 화면 뷰를 겹쳐서 배치합니다.
  - 우측 패널(`_build_right_panel`): 클래스 분류, YOLO 자동 추론 제어, 작업 이력, 검수 상태 및 이슈 노트 패널을 상하로 밀집 배치하고, 최하단에 [이전]/[다음]/[저장]/[저장 후 다음] 네비게이션 버튼을 고정합니다.
- **사이드바 토글 (`toggle_sidebar`):**
  - 사이드바 프레임을 동적으로 숨기거나(`grid_remove`) 다시 표시(`grid`)하며, 화면 크기 변경에 따른 캔버스 리사이즈 이벤트를 즉시 트리거하여 뷰를 재조정합니다.

# 5. 확인 및 개선 사항
- UI 위치와 크기 변경 관련 소스코드가 이 모듈(`LayoutMixin`)에 집중되어 있어 화면 디자인 수정이나 위젯 재배치가 매우 직관적이고 용이합니다.
- 좌우 패널과 하단 네비게이션 버튼들이 그리드 및 팩(Pack) 매니저의 제약 규칙에 맞춰 일관성 있게 정렬되어 높은 UI 완성도를 제공합니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- Tkinter 기반 그리드/팩 레이아웃 전면 모듈화 및 패널 컴포넌트(`PersonPanel`, `ReviewPanel`, `ScenePanel`, `HistoryPanel`) 통합 조립