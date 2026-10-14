# 🛠️ view_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 이미지 ↔ 캔버스 좌표 변환, 확대/축소/이동(Zoom & Pan), 캔버스 렌더링(이미지 + BBox 오버레이), 클릭 위치의 BBox 찾기(Hit-Test), 캔버스 리사이즈 대응
* **연동 모듈:**
  * `PIL (Image, ImageTk)`: 보이는 영역 크롭·리사이즈, Tk 이미지 변환
  * `src.bbox.geometry`: `box_to_yolo`, `yolo_to_box` (실제 변환은 여기에 위임)
  * `src.config`: `CLASS_NAMES`, `COLORS`, `ISSUE_ID`, `ISSUE_COLOR`, `PENDING_COLOR`, `FONT_B`, `MAX_ZOOM`
  * 다른 Mixin: `cur_boxes()`(navigation), `status()`(layout), `selected`/`pending`(edit)

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** `self.img`(PIL), 뷰 상태(`scale`, `ox`, `oy`, `fit_scale`, `is_fit`, `zoom_mode`), 현재 BBox 목록, 캔버스 좌표 `(cx, cy)`
* **Output:**
  * 캔버스에 그려지는 이미지, BBox 사각형, 이름표, 선택 핸들
  * 변환 좌표(`to_canvas`, `to_image`, `box_to_yolo`, `yolo_to_box`)
  * `hit_test()`가 반환하는 BBox dict(없으면 `None`)
  * 내부 상태: `self.tkimg`(PhotoImage 참조 유지), `self._label_hits`(이름표 영역 목록), `self.temp_rect`

---

## 3. 주요 기능 및 구성 (Core Features)
* **좌표 변환:** `to_canvas`/`to_image`는 `scale`과 오프셋(`ox`, `oy`)으로 직접 계산. `box_to_yolo`/`yolo_to_box`는 이미지 크기를 넘겨 `geometry`에 위임. `clamp_img_pt`는 이미지 경계로 좌표를 제한
* **뷰 제어:** `fit_view`(전체 맞춤·중앙 정렬), `zoom_at`(포인터 중심 확대/축소), `zoom_to_rect`(영역 확대), `clamp_view`(이미지가 화면 밖으로 벗어나지 않게 제한), `reset_view`(원상태), `zoom_out`(캔버스 중심 1/1.25배)
* **확대 모드:** `toggle_zoom_mode`/`set_zoom_mode`로 확대 버튼 상태(눌림 표시)와 커서(`plus`/`crosshair`) 전환
* **캔버스 리사이즈:** `on_canvas_resize` — 전체보기 상태면 `fit_view`, 확대 상태면 `clamp_view` 후 다시 그림
* **렌더링:** `visible_rect(margin)`으로 화면에 보이는 이미지 영역만 계산 → `crop` + `resize`(배율 3 이상 NEAREST, 미만 BILINEAR) → `draw_boxes`
* **BBox 그리기:** 클래스 색상/이름(`color_of`, `name_of`). 미지정·이슈 박스는 점선(6,3), 자동 BBox는 점선(4,3)과 `AI xx%` 이름표. 선택 박스는 굵은 선 + 4개 모서리 핸들(한 변 8px, **하드코딩이며 edit_mixin의 `HANDLE_R`과 별개**)
* **Hit-Test:** 이름표 영역을 먼저 검사(나중에 그린 것 우선) → 박스 내부, 겹치면 면적이 가장 작은 박스 선택
* **`redraw_boxes`:** 이미지는 유지하고 `box` 태그 항목만 지우고 다시 그림(빠른 갱신용)

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **렌더링 최적화:** 보이는 영역만 크롭·리사이즈하여 4K 이미지에서도 부하 최소화
* **줌 한계:** 배율을 `fit_scale` ~ `fit_scale × MAX_ZOOM`으로 제한. 최소 배율 이하로 줄이면 자동으로 `fit_view`
* **이미지 미로드 방어:** `fit_view`, `zoom_at`, `on_canvas_resize`, `redraw_boxes`는 `self.img`가 없으면 즉시 반환. (`clamp_view`, `visible_rect`, `zoom_to_rect`에는 가드가 없으며 호출하는 쪽에서 보장)
* **PhotoImage 보존:** `self.tkimg`에 참조를 유지해 Tkinter에서 이미지가 사라지는 문제 방지
* **클래스 이름 방어:** `name_of`는 `CLASS_NAMES` 범위를 벗어난 번호면 숫자만 표시

---

## 5. 핵심 처리 로직 (Logic Flow)
1. 이미지 열기 → `fit_view()`: 캔버스/이미지 크기 비교로 `fit_scale`과 중앙 오프셋 계산
2. `render()`: 캔버스 초기화 → `visible_rect` 계산 → 크롭·리사이즈 → 이미지 배치 → `draw_boxes()`
3. `draw_boxes()`: 각 박스를 캔버스 좌표로 변환해 사각형·이름표·(선택 시) 핸들 생성, 이름표 영역을 `_label_hits`에 저장
4. 마우스 클릭 → `hit_test()`가 이름표 → 박스 내부 순으로 검사해 대상 반환

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. **전체보기 상태**에서 창 크기를 바꾸면 이미지가 중앙을 유지하며 다시 맞춰지는지 확인 (확대 상태에서는 중앙 정렬이 아니라 경계 제한만 적용됨)
  2. BBox가 겹친 위치를 클릭했을 때 면적이 가장 작은 박스가 선택되는지 확인
  3. 이름표(박스 바깥 위쪽)를 클릭해도 해당 박스가 선택되는지 확인
  4. 영역 확대 후 `원상태`·`축소` 버튼이 정상 동작하는지, 최대 배율을 넘지 않는지 확인
