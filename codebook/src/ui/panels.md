# 1. 개요
라벨링 프로그램 우측 패널에서 독립적으로 동작하는 4개의 핵심 GUI 위젯 컴포넌트 클래스(`PersonPanel`, `ReviewPanel`, `HistoryPanel`, `ScenePanel`)를 정의한 모듈입니다. 작업자 선택, 검수 상태 라디오버튼 제어, 읽기 전용 작업 이력 표시, 그리고 `Scene Type` 및 `REVIEW` 사유 선택을 위한 드롭다운 컴포넌트들을 모듈화하여 재사용성과 가독성을 높였습니다.

# 2. 파일 간 연결 구조
- 상속 관계: 모든 패널 클래스가 `tk.LabelFrame`을 상속하여 독립적인 프레임 위젯으로 동작함
- 외부 의존성 및 호출 관계: `src.config`의 `FONT`, `FONT_B`, `FONT_S` 공통 폰트 상수를 참조하며, 주로 `LayoutMixin` 및 `NavigationMixin` 등에서 인스턴스화되어 상태 값 조회 및 갱신에 호출됨

# 3. 주요 클래스 및 컴포넌트

| 클래스명 | 부모 클래스 | 역할 및 주요 메서드 |
| :--- | :--- | :--- |
| `PersonPanel` | `tk.LabelFrame` | 작업자 정보 선택 콤보박스 및 역할 힌트 텍스트 제공 (`get_label`, `set_label`, `set_hint`) |
| `ReviewPanel` | `tk.LabelFrame` | 저장 단계(Pass, Edited, Review 등) 선택 라디오버튼 그리드 배치 및 활성화 제어 (`get_state`, `set_state`, `set_current`, `set_enabled`) |
| `HistoryPanel` | `tk.LabelFrame` | 단계별 최초 저장자(`top`) 및 이후 이동 기록(`log`)을 텍스트 영역에 읽기 전용으로 시각화 (`show`) |
| `ScenePanel` | `tk.LabelFrame` | 이미지 유형(`Scene Type`)과 리뷰 사유(`REVIEW 사유`) 선택용 드롭다운 관리 (`get_scene`, `get_reason`, `set_values`) |

# 4. 주요 실행 흐름
- **작업자 패널 (`PersonPanel`):**
  - 드롭다운을 통해 작업자를 선택하면 바인딩된 `_changed` 콜백을 통해 상위 앱의 권한 및 선택지를 즉시 재판정합니다.
- **검수 상태 패널 (`ReviewPanel`):**
  - 주어진 단계 목록(`states`)을 지정된 열 개수(`per_row=3`)에 맞춰 라디오버튼으로 자동 분할 정렬하고, 사용자 권한에 따라 특정 단계 버튼의 활성/비활성(`set_enabled`)을 동적으로 제어합니다.
- **작업 이력 패널 (`HistoryPanel`):**
  - 상단 고정 영역에는 단계별 최초 저장자 정보를 표시하고, 하단 텍스트 위젯에는 이후의 이동 및 수정 이력을 갱신하며 항상 최신 기록이 보이도록 자동 스크롤(`see("end")`)합니다.
- **씬 타입 패널 (`ScenePanel`):**
  - 표시용 문자열과 실제 기록값 간의 매핑 딕셔너리를 구성하여 오타를 방지하고, 이미지를 전환할 때마다 매니페스트 데이터를 기반으로 값을 안전하게 채워 넣습니다(`set_values`).

# 5. 확인 및 개선 사항
- UI 컴포넌트들을 각각 독립된 클래스로 분리하여 레이아웃 코드의 복잡성을 크게 낮추고 유지보수성을 극대화했습니다.
- 텍스트 위젯과 라디오버튼 등의 상태 조작 메서드가 직관적으로 인터페이스화되어 있어 외부 Mixin에서 간편하게 제어할 수 있습니다.
- 그 외 내부적으로 연동되는 구체적인 클래스나 호출 로직 관련 개선 사항: *********

# 6. 변경 이력
- 독립 위젯 패널(`PersonPanel`, `ReviewPanel`, `HistoryPanel`, `ScenePanel`) 컴포넌트 클래스 모듈화 구조 확립