# 🛠️ navigation_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 현재 이미지 열기, 이전/다음 이동, 다음 이미지 프리패치, 이미지별 메모·검수 상태 관리, 검수 단계 선택 가능 여부 판단, Manifest 상태에 따른 UI 자동 맞춤
* **연동 모듈:**
  * `threading`, `PIL.Image`, `tkinter.messagebox`
  * `src.config`: `UNUSED_CLASS`, `STAGES`, `WORKER_STAGES`, `REVIEWER_STAGES`
  * 다른 Mixin: `render`/`fit_view`/`set_zoom_mode`(view), `discard_pending`/`refresh_info`(edit), `update_progress`(folder), `disp`/`P`/`remember_folder`(folder)
  * 외부(저장·자동 라벨링 Mixin): `load_saved`, `is_in_progress`, `update_out_dir_label`, `manifest_path`, `apply_auto`, `predict_image`, `labeler`, `auto_pred`

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** 이미지 인덱스, 이슈 노트 텍스트, 작업자/검수자 정보 입력 상태, Manifest CSV의 `status`
* **Output:**
  * 현재 이미지(`self.img`, RGB), 인덱스(`self.idx`), BBox 목록(`cur_boxes()`)
  * 메모(`self.notes`), 검수 상태(`self.review_status`, `self.last_stage`)
  * 상태바 메시지, 검수 버튼 활성/비활성, 이미지 목록 선택, 진행률(`self.passed`) 갱신

---

## 3. 주요 기능 및 구성 (Core Features)
* **현재 항목 도우미:** `cur_path()`(현재 이미지 경로), `cur_boxes()`(현재 이미지 BBox 목록. 없으면 생성) — 다른 Mixin이 공용으로 사용
* **메모/검수 상태:** `save_current_note()`(이슈 노트 → 메모리 `self.notes`), `on_review_select(state)`(선택 단계를 이미지에 기록하고 `last_stage`로 기억 → 다음 이미지에 같은 단계를 미리 선택)
* **선택 가능 단계 판단(`stage_allowed`):** `review`는 **작업자 정보 또는 검수자 정보 중 하나만 완성돼도** 선택 가능, `WORKER_STAGES`(1차·2차)는 작업자 정보 완성, `REVIEWER_STAGES`(review·final 등)는 검수자 정보 완성 시 선택 가능. `update_review_buttons()`가 `STAGES` 전체에 반영
* **이미지 열기(`show_image`):** 미지정 박스·메모 정리 → 캐시(`_cache`) 또는 디스크에서 로드(RGB) → 저장된 라벨/메모 로드(`load_saved`) → 자동 BBox 적용 → 메모·검수 상태 복원 → 목록 선택·뷰 맞춤·정보 갱신 → 상태바 메시지 → `remember_folder()` → 다음 이미지 프리패치
  * **자동 BBox 적용 조건:** 라벨이 없고, 저장된 적이 없고(`done`에 없음), 모델이 로드되어 있을 때. 일괄 추론 결과(`auto_pred`)가 우선이며, 없을 때만 "열 때 자동 추론"(`autoOnOpen`)이 켜져 있고 일괄 추론이 실행 중이 아니면 직접 추론
* **프리패치(`prefetch`):** 다음 이미지를 데몬 스레드로 미리 읽어 `_cache`에 저장. **캐시는 항상 최대 1장**(저장 전에 `clear()`)
* **이동:** `prev_image`(이전, 이동 후 해당 이미지를 `passed`에서 제거), `next_image`(현재 이미지를 `passed`에 추가하고 진행률 갱신 후 이동). 첫/마지막 이미지에서는 안내창
* **Manifest 연동 UI 맞춤(`show_image` 끝):** 해당 프로젝트 Manifest CSV에서 현재 파일의 `status`를 찾아
  * `DONE` → 검수 상태를 "2차"로 설정
  * `EDITED`/`FINAL`/`REVIEW` → 검수 상태는 그대로 두고 검수자 정보 입력칸을 활성화
  * 그 외(Manifest 없음/미기록) → 검수 상태를 **"1차"로 설정**하고 검수자 정보 입력칸을 **비활성화 + 입력값 초기화**
* **화면 비우기(`clear_view`):** 표시할 이미지가 없을 때 캔버스·메모·검수 상태·정보 패널 초기화

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **로드 실패:** 이미지를 열 수 없으면 오류창을 띄우고 현재 상태를 유지(앱 종료 없음)
* **자동 추론 실패:** 예외를 잡아 상태바에 표시하고 계속 진행
* **프리패치 실패:** 스레드 안에서 예외를 조용히 무시(UI 접근 없음). 실제 열 때 오류 처리
* **경계 처리:** 첫 이미지에서 이전, 마지막 이미지에서 다음은 안내창만 표시하고 인덱스 유지. 이미지가 없으면 이동 함수는 즉시 반환
* **미사용 클래스 경고:** `UNUSED_CLASS` 박스가 있으면 상태바에 "⚠ 4번(사용 안 함) 박스 있음 …" 표시 (조건은 상수, 문구의 숫자 4는 하드코딩)
* **메모 보관:** 이동 전에 메모를 메모리에 저장하고 미지정 박스를 정리 (디스크 저장은 저장 Mixin 담당)

---

## 5. 핵심 처리 로직 (Logic Flow)
1. `show_image(i)`: 이전 이미지 정리 → 로드 → 라벨/메모/자동 BBox 처리 → UI 복원 → 상태바
2. 이어서 `remember_folder()` → `prefetch(i+1)` → Manifest 상태에 맞춰 검수 UI 조정
3. `next_image()`/`prev_image()`가 `passed`와 진행률을 갱신하고 `show_image` 호출

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `다음`/`이전`으로 이미지가 연속 전환되고, 첫/마지막에서 안내창이 뜨는지 확인
  2. 작업자·검수자 정보를 비워 두면 모든 검수 상태가 비활성, 작업자 정보만 채우면 1차·2차·review가 활성, 검수자 정보만 채우면 review·final이 활성인지 확인
  3. 이슈 노트에 입력한 뒤 다른 이미지로 갔다가 돌아오면 노트가 유지되는지 확인
  4. 4번 클래스 박스가 있는 이미지를 열면 상태바 경고가 뜨는지 확인
  5. 손상된 이미지를 열면 오류창이 뜨고 앱이 계속 동작하는지 확인

---

## 7. 알려진 동작 / 확인 필요 사항
* `show_image` 앞부분에서 `review_status.get(p, last_stage)`로 검수 상태를 복원하지만, 끝의 Manifest 블록이 status가 비어 있으면 "1차"로 **다시 덮어씀** → `last_stage` 기능이 사실상 적용되지 않을 수 있음 (의도 확인 필요)
* Manifest 블록이 이미지를 넘길 때마다 CSV 전체를 읽고, `remember_folder()`도 매번 설정 파일을 씀 → 목록이 커지면 이동 속도에 영향 가능
* `status` 값 `FINAL`이 가이드의 Manifest 상태(DONE/EDITED/REVIEW)에 없으므로 실제 사용 여부 확인 필요
