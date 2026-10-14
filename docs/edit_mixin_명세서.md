# 🛠️edit_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 마우스/키보드 기반 BBox 편집 — 새로 그리기, 선택(단일/다중), 모서리 핸들 크기 조절, Shift+드래그 이동(Pan), 영역 확대 드래그, 휠 확대/축소, 클래스 지정, 삭제, 크기 정보 패널(`labelList`, `labelDetail`) 동기화
* **연동 모듈:**
  * `tkinter.messagebox`: 삭제 확인·안내
  * `src.config`: `CLASS_IDS`, `ISSUE_ID`, `PENDING_COLOR`, `HANDLE_R`, `SHIFT`, `CTRL`, `WHEEL_STEP`
  * 다른 Mixin: `to_canvas`/`to_image`/`clamp_img_pt`/`hit_test`/`redraw_boxes`/`render`/`zoom_at`/`zoom_to_rect`/`set_zoom_mode`(view), `cur_boxes`(navigation), `autosave_work`(외부 저장 Mixin)

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** 마우스 이벤트(Press/Drag/Release/Motion/Wheel), 키(Esc), `classList` 선택, `labelList`(Treeview) 선택
* **Output:**
  * `cur_boxes()` 목록의 BBox dict(`cls`, `x1`, `y1`, `x2`, `y2`, `auto`)를 생성·수정·삭제
  * 선택 상태(`self.selected`), 미지정 박스(`self.pending`), 동작 모드(`self.mode`)
  * `labelList`와 `labelDetail`의 화면 갱신, 상태바 메시지

---

## 3. 주요 기능 및 편집 모드 (Editing Modes)
* **`self.mode` 값:** `press`(클릭 대기) → `draw`(신규 박스) / `resize`(핸들 조절) / `pan`(화면 이동) / `zoomsel`(확대 영역 지정) / `None`
* **press 규칙(`on_press`):** 캔버스 포커스 → 클래스 미지정 박스 자신이 아니면 `discard_pending()` → 핸들 클릭(Shift/Ctrl 없을 때)이면 `resize` → Shift면 `pan` → Ctrl이면 클릭한 박스 선택 토글 → 그 외는 `press`(확대 모드면 `zoomsel`)
* **신규 박스:** 4px(캔버스) 이상 드래그하면 `draw`로 전환되고 점선 가이드(`temp_rect`) 표시. 놓았을 때 **이미지 기준 가로·세로 2px 이상**이면 `cls=None`인 박스를 생성(`pending`)하고 클래스 선택을 안내
* **클릭 선택:** 드래그 없이 놓으면 `hit_test` 결과를 단일 선택하고 `classList`의 해당 클래스 줄을 하이라이트
* **핸들 조절(`resize`):** **박스가 정확히 1개 선택**되고 확대 모드가 아닐 때만 4개 모서리(`nw/ne/sw/se`) 핸들 활성화. 이미지 경계 안으로 제한, 반대편 변과 최소 2px(이미지 기준) 간격 유지. 놓으면 `auto=False`(사람이 확인) 처리
* **Pan:** Shift+드래그. 전체보기(`is_fit`) 상태에서는 차단. 드래그 중 캔버스 항목을 이동시키고 놓을 때 다시 렌더링
* **영역 확대(`zoomsel`):** 가이드 사각형의 캔버스 크기가 가로·세로 8px 이상이면 확대 모드를 끄고 `zoom_to_rect`, 아니면 취소
* **휠(`on_wheel`):** 위 = 확대, 아래 = 축소(포인터 중심, `WHEEL_STEP`). Windows/macOS는 `delta`, Linux는 `Button-4/5`로 방향 판단. 그리기·이동 중에는 무시. (바인딩은 이 파일이 아닌 곳에서 수행)
* **Esc(`on_escape`):** 확대 모드면 해제, 아니면 미지정 박스 삭제
* **클래스 지정(`on_class_select`):** `classList` 줄 번호 → `CLASS_IDS[줄]`로 실제 클래스 번호 변환. `pending`이 있으면 그 박스에 지정, 없고 선택된 박스가 있으면 **선택된 모든 박스**에 지정(`auto=False`). 둘 다 없으면 무시
* **삭제(`delete_selected`):** 선택이 없으면 안내창, 있으면 **확인창(`askyesno`)** 후 삭제
* **정보 패널:** `refresh_info()`가 `labelList`를 다시 채움(자동 BBox는 클래스 뒤에 `*`, 이슈는 "이슈", 미지정은 "?"). `update_detail()`은 **첫 번째 선택 박스**의 값을 읽기 전용 `labelDetail`에 표시. `on_tree_select`는 목록 선택을 캔버스 선택과 동기화

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **최소 크기:** 신규 박스는 이미지 기준 2px 미만이면 생성하지 않음
* **반전 방지:** 크기 조절 시 `x1 ≤ x2-2`, `y1 ≤ y2-2`로 제한
* **경계 제한:** 드래그·조절 좌표는 `clamp_img_pt`로 이미지 영역 안에 고정
* **미지정 박스 정리:** 클래스를 고르지 않고 다른 곳을 누르면 자동 삭제
* **Pan 제한:** 전체보기 상태에서는 이동 불가 안내
* **자동 저장:** 크기 조절 완료, 클래스 지정/변경, 삭제 직후 `autosave_work()` 호출
* **키 바인딩 범위:** Delete/Esc는 `imageCanvas`에만 바인딩되어 이슈 노트 등 입력창 입력과 충돌하지 않음

---

## 5. 핵심 처리 로직 (Logic Flow)
1. Press: 핸들/Shift/Ctrl 여부로 모드 결정
2. Drag: 모드별로 가이드 사각형 표시 / 박스 크기 변경 / 화면 이동
3. Release: 박스 확정(`pending`) 또는 선택 처리, 확대 실행, 자동 저장 호출
4. 클래스 목록 선택 → 클래스 부여 → 다시 그리기 + 정보 패널 갱신 + 자동 저장

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. 드래그로 점선 박스를 만든 뒤 클래스를 고르면 색상이 바뀌며 확정되는지, 고르지 않고 다른 곳을 누르면 박스가 사라지는지 확인
  2. 선택한 박스의 모서리를 드래그해 크기를 바꾸면 `labelList`/`labelDetail` 값이 함께 갱신되는지 확인
  3. `Ctrl+클릭`으로 여러 박스를 선택 → 삭제 시 확인창이 뜨고 선택한 박스만 삭제되는지 확인
  4. 확대 후 `Shift+드래그`로 이동되고, 전체보기에서는 이동이 차단되는지 확인
  5. 휠로 포인터 위치 기준 확대/축소가 되는지 확인
