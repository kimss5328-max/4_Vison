# 🛠️ panels.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 재사용 가능한 독립 서브 패널 위젯 정의 — `InfoPanel`(정보 입력), `ReviewPanel`(검수 상태 선택), `SceneTypePanel`(장면 유형 + REVIEW 이유)
* **연동 모듈:**
  * `src.config`: `FONT`, `FONT_B`, `SCENE_TYPES`, `REVIEW_REASONS`
  * `layout_mixin`: 패널 인스턴스 생성·배치
  * `navigation_mixin`: `update_review_buttons`가 `ReviewPanel.set_enabled`를 호출, 이미지 전환 시 `set_state` 호출

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** 부모 위젯, 제목, 필드 이름 목록(`InfoPanel`), 상태 목록(`ReviewPanel`), `on_change` 콜백
* **Output (메서드):**

| 패널 | 읽기 | 쓰기 |
|---|---|---|
| `InfoPanel` | `get_data()`(dict), `is_complete()` | `set_data(dict)` |
| `ReviewPanel` | `get_state()` | `set_state(str)`, `set_enabled(state, bool)` |
| `SceneTypePanel` | `get_scene()`, `get_reason()` | `set_scene(str)`, `set_reason(str)` |

---

## 3. UI 구성 요소 (Panel Components)
* **InfoPanel (`tk.LabelFrame`):** 필드마다 `Label` + `Entry`를 세로로 배치. 각 Entry는 `StringVar`에 연결되고, `trace_add("write")`로 글자를 칠 때마다 `on_change()` 호출 (현재 사용: 이름, ID)
* **ReviewPanel (`tk.LabelFrame`):** 상태별 `Radiobutton`을 2열 바둑판으로 배치. `tristatevalue="__none__"`로 초기(빈 값)에 어떤 버튼도 선택되지 않은 상태를 표현. 클릭하면 `on_change(state)` 호출
* **SceneTypePanel (`tk.LabelFrame`):** `SCENE_TYPES` 라디오 버튼 + "REVIEW 이유" 라벨 + `ttk.Combobox`(`REVIEW_REASONS`). 콤보박스가 `state="normal"`이라 **목록에 없는 문구를 직접 입력할 수도 있음**. `on_change` 콜백은 없음(저장 시 `get_*`로 읽기만 함)

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **필수 입력 검증:** `InfoPanel.is_complete()`는 **모든 칸**이 공백 제외 후 비어 있지 않을 때만 True
* **값 정제:** `get_data()`와 `get_reason()`은 앞뒤 공백을 제거해 반환
* **잘못된 장면 값 방어:** `SceneTypePanel.set_scene()`은 `SCENE_TYPES`에 없는 값이면 `""`로 초기화
* **주의:** `ReviewPanel.set_enabled()`는 목록에 없는 상태 이름을 넘기면 `KeyError`가 발생함(호출 측이 `STAGES` 기준으로만 호출). 어떤 단계를 활성화할지의 판단은 이 파일이 아니라 navigation_mixin의 `stage_allowed`가 담당

---

## 5. 핵심 처리 로직 (Logic Flow)
1. layout_mixin이 패널을 생성하고 콜백(`update_review_buttons`, `on_review_select`)을 연결
2. 사용자가 입력/클릭하면 `InfoPanel`·`ReviewPanel`이 내부 `_changed()`를 통해 콜백을 호출
3. 저장·이동 시 상위 Mixin이 `get_*`/`set_*`로 값을 수집하거나 복원

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `InfoPanel`에 이름만 입력 → `is_complete()` False, 이름·ID 모두 입력 → True, 공백만 입력 → False
  2. `ReviewPanel.set_enabled("final", False)` 호출 시 해당 라디오 버튼이 비활성화되는지 확인
  3. `SceneTypePanel.set_scene("목록에 없는 값")` 호출 시 선택이 해제(`""`)되는지 확인
  4. 콤보박스에서 이유를 고른 뒤 `get_reason()`이 해당 문자열을 반환하는지 확인
