# 🛠️ layout_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 전체 Tkinter UI 위젯 생성·배치 전담 (위치·크기·그리드 변경은 이 파일만 수정). 위젯별 버튼 `command`와 캔버스 이벤트 바인딩, 사이드바 토글, 상태바 메시지 출력(`status()`)도 이 파일에 있음
* **연동 모듈:**
  * `src.config`: `CLASS_NAMES`, `CLASS_IDS`, `COLORS`, `STAGES`, `STAGE_FILTERS`, `FONT`, `FONT_B`, `FONT_S`
  * `src.ui.panels`: `InfoPanel`, `ReviewPanel`, `SceneTypePanel`
  * 다른 Mixin 핸들러 (이 파일에는 정의 없음):
    * folder_mixin: `open_folder`, `on_folder_select`, `on_stage_filter_select`, `on_image_list_select`
    * view_mixin: `on_canvas_resize`, `reset_view`, `toggle_zoom_mode`, `zoom_out`
    * edit_mixin: `on_press`, `on_drag`, `on_release`, `on_motion`, `on_escape`, `delete_selected`, `on_class_select`, `on_tree_select`
    * navigation_mixin: `prev_image`, `next_image`, `on_review_select`, `update_review_buttons`
    * 외부(저장·자동 라벨링 Mixin): `change_out_dir`, `save`, `save_and_next`, `load_model`, `run_auto_current`, `toggle_batch`

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** `self.root`(최상위 윈도우), config 상수, 서브 패널 클래스, `self.sidebar_on`(토글 상태. 초기값은 다른 파일에서 설정)
* **Output:** `self`에 등록되는 위젯
  * 상단: `sidebarToggleBtn`, `progressBar`, `progressText`
  * 사이드바: `sidebar`, `openFolderBtn`, `outDirLabel`, `outDirChangeBtn`, `folderSelect`, `stageRow`, `stageSelect`, `imageList`
  * 중앙: `imageCanvas`, `resetViewBtn`, `zoomBtn`, `zoomOutBtn`, `deleteBtn`
  * 오른쪽: `classList`, `labelList`(Treeview), `labelDetail`(dict of StringVar), `loadModelBtn`, `modelLabel`, `confVar`, `autoOnOpen`, `autoCurBtn`, `autoBatchBtn`, `workerVar`, `reviewPanel`, `workerInfo`, `reviewerInfo`, `sceneTypePanel`, `issueNote`, `prevBtn`, `nextBtn`, `saveBtn`, `saveNextBtn`
  * 하단: `statusBar`

---

## 3. UI 구성 요소 및 레이아웃 구조 (Layout Breakdown)

```
[ Root Grid (3행 x 3열) ]  — 1열, 1행만 weight=1 (늘어남)
Row 0 : [ 상단 바 (Col 0~1)                        ] [ 오른쪽 패널 (Row 0~1, Col 2) ]
Row 1 : [ 사이드바 (Col 0) ] [ 중앙 캔버스 (Col 1) ] [                              ]
Row 2 : [ 상태바 (Col 0~2)                                                          ]
```

```
오른쪽 패널 (pack, 위 → 아래)
├─ 클래스 영역(upper): [ 클래스 분류 classList ] | [ 클래스 크기 정보: labelList + labelDetail ]
├─ 자동 라벨링 (YOLO)
├─ lower  ┬ 왼쪽 절반: 작성자 Entry → 검수 상태 → 작업자 정보 → 검수자 정보
│         └ 오른쪽 절반: 이슈 노트
├─ Scene Type 패널 (right에 직접 pack → lower 아래 전체 폭)
└─ 네비게이션 (side=bottom, 맨 아래 고정): 이전 | 다음 | 저장 | 저장 후 다음
```

* **상단 바 (`_build_top_bar`):** 사이드바 토글 버튼, 진행률 `ttk.Progressbar`, 진행 텍스트. 토글 버튼을 0열 밖(상단 바)에 둬서 사이드바를 숨겨도 버튼이 사라지지 않음
* **사이드바 (`_build_sidebar`):** 폴더 열기, 저장 위치 표시 + [변경], 폴더 Combobox, 단계 선택 행(`stageRow`, "(전체 이미지)" 선택 시에만 pack), 이미지 `Listbox` + 스크롤바
* **중앙 (`_build_center`):** `imageCanvas`(어두운 배경), 하단 버튼(원상태 / 확대 / 축소 / 삭제)
* **오른쪽 패널 (`_build_right_panel`):** 네비게이션을 `side="bottom"`으로 먼저 pack한 뒤 클래스 → 자동 라벨링 → 하단 패널 순서로 생성
* **캔버스 바인딩:** `<Configure>`, `<ButtonPress-1>`, `<B1-Motion>`, `<ButtonRelease-1>`, `<Delete>`, `<Escape>`, `<Motion>`. **마우스 휠 바인딩은 이 파일에 없음**(`on_wheel`은 edit_mixin에 있고 바인딩 위치는 메인 파일 확인 필요)

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **클래스 번호 매핑:** 목록 줄 순서 ≠ 클래스 번호(4번이 빠짐). `CLASS_IDS`를 직접 순회해 `"{cid}: 이름"`을 넣고 색상은 `COLORS[cid % len(COLORS)]`로 지정
* **사이드바 토글:** `grid_remove()`/`grid()` 후 `update_idletasks()` → `on_canvas_resize()`를 즉시 호출해 캔버스 폭 재계산 오류 방지
* **하단 패널 1:1 폭:** `lower.columnconfigure`에 `uniform="half"`를 적용해 창 크기와 무관하게 왼쪽/오른쪽 절반 폭 고정
* **입력 위젯 폭 보정:** Entry/Text에 `width=1` + `fill` 조합을 써서 창이 좁아져도 패널이 밀려나지 않게 함

---

## 5. 핵심 처리 로직 (Logic Flow)
1. `build_ui()`: 루트 가중치 설정(`columnconfigure(1)`, `rowconfigure(1)`)
2. 생성 순서: 상단 바 → 사이드바 → 중앙 → 오른쪽 패널 → 상태바(마지막). 각 `_build_*` 안에서 버튼 `command`와 이벤트 바인딩이 함께 이루어짐
3. `_build_lower_panel` 끝에서 `update_review_buttons()`를 한 번 호출해 검수 단계 선택지를 전부 비활성으로 시작 (이 시점에는 `statusBar`가 아직 없음)
4. `toggle_sidebar()`: `sidebar_on` 반전, 버튼 문구(`◀ 사이드바 off` / `▶ 사이드바 on`) 교체

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. 앱 실행 시 상단 바, 사이드바, 캔버스, 오른쪽 패널, 상태바가 깨짐 없이 표시되는지 확인
  2. `◀ 사이드바 off` 클릭 → 사이드바가 숨겨지고 캔버스가 가로로 넓어지는지, 다시 눌러 원복되는지 확인
  3. 창 크기 변경 시 중앙 캔버스만 늘어나고 오른쪽 패널 폭은 유지되는지 확인
  4. 클래스 목록에 4번이 없고, 목록에서 항목을 클릭했을 때 올바른 Class ID가 적용되는지 확인
  5. 처음 실행 시 검수 상태 라디오 버튼이 전부 비활성인지 확인
