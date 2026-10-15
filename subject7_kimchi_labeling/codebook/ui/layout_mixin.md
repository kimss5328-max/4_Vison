# 1. 개요
프로그램의 메인 윈도우 레이아웃과 UI 위젯(버튼, 패널, 캔버스 등)의 배치를 전담하는 Mixin 클래스입니다. Tkinter의 `grid`와 `pack`을 사용하여 전체 화면을 상단, 좌측 사이드바, 중앙(이미지 캔버스), 우측 정보 패널로 분할 구성합니다.

# 2. 파일 간 연결 구조
- 상속 관계: 없음 (GUI 메인 클래스에 다중 상속되어 `LayoutMixin` 형태로 사용됨)
- 컴포넌트 의존성: `src.ui.panels` 모듈의 `InfoPanel`, `ReviewPanel` 클래스를 사용하여 정보 입력란과 검수 단계 버튼 그룹을 구성합니다.

# 3. 주요 상태 변수

| 분류 | 주요 인스턴스 변수 | 역할 |
| :--- | :--- | :--- |
| **상단/하단** | `self.progressBar`, `self.statusBar` | 전체 진행률 표시바 및 하단 상태 메시지 출력 라벨 |
| **사이드바** | `self.sidebar`, `self.sidebar_on` | 좌측 패널(폴더/이미지 목록) 프레임 객체 및 토글(숨김/표시) 상태 여부(bool) |
| **중앙 (캔버스)** | `self.imageCanvas` | 실제 이미지를 그리고 사용자가 바운딩 박스를 조작하는 Tkinter Canvas 위젯 |
| **우측 패널** | `self.classList`, `self.labelList`, `self.labelDetail` | 지원하는 클래스 목록(Listbox), 현재 이미지에 그려진 박스 정보 표(Treeview) 및 상세 좌표값 출력 딕셔너리 |
| **우측 하단** | `self.workerVar`, `self.issueNote` | 작업자명 문자열 변수 및 이슈 내용을 입력하는 Text 위젯 |
| **검수 패널** | `self.reviewPanel`, `self.workerInfo`, `self.reviewerInfo` | 단계 설정 라디오 버튼 패널 및 작업자/검수자 정보(이름, ID) 입력 패널 객체 (`InfoPanel`, `ReviewPanel`) |

# 4. 주요 실행 흐름
- **전체 UI 빌드 (`build_ui`):** 
  - `_build_top_bar`, `_build_sidebar`, `_build_center`, `_build_right_panel`을 순차적으로 호출하여 전체 프레임을 초기 구성합니다.
- **사이드바 토글 (`toggle_sidebar`):**
  - 사이드바 버튼 클릭 시 좌측 프레임을 숨기거나 나타나게(`grid_remove` / `grid`) 처리하며, 캔버스 크기 변화를 갱신(`on_canvas_resize`)합니다.
- **오른쪽 패널 구성 (`_build_right_panel` 관련):**
  - 우측 패널은 상단부터 차례대로 클래스 선택(Listbox), 좌표 정보 뷰(Treeview), 자동 라벨링(YOLO) 도구, 그리고 하단의 작성자·검수 상태/정보 및 이슈 노트(Text) 입력창으로 레이아웃을 분할합니다.

# 5. 확인 및 개선 사항
- 4번(사용 안 함) 클래스는 `CLASS_IDS` 리스트를 기반으로 UI 목록에 추가하므로, 시각적으로 목록에서 자연스럽게 제외되도록 설계되었습니다.
- UI 배치 관련 로직이 이 파일에 격리되어 있어 뷰(View)의 변경이나 위치 조절 시 이 파일만 수정하면 되도록 관심사가 분리되어 있습니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- ********* (코드 내 명시된 변경 이력 없음)