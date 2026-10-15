#  folder_mixin.py 명세서

---

## 1. 파일 역할 (Role)
* **담당 기능:** 프로젝트 폴더 선택·구조 인식(`images`/`labels`), 이미지·라벨 목록 구성, 폴더/단계별 목록 필터링, 이미지 목록 색상 표시, 진행률 계산, 마지막 폴더·이미지 기억
* **연동 모듈:**
  * `tkinter.filedialog`, `messagebox`
  * `src.config`: `IMG_EXTS`, `AUTO_LIST_COLOR`, `DONE_LIST_COLOR`, `STAGE_FILTERS`, `PICK_START_DIR`, `SETTINGS_PATH`
  * 다른 Mixin: `show_image`, `cur_path`, `clear_view`(navigation), `discard_pending`(edit), `status`(layout)
  * 외부(저장 Mixin): `is_output_dir`, `prepare_out_dir`, `saved_stages`, `latest_stage`, `ensure_out_dir`
  * 참고: `threading`, `run_validation`(auto_validator)은 import만 되어 있고 이 파일에서는 사용하지 않음

---

## 2. 입출력 데이터 (Input & Output)
* **Input:** 사용자가 고른 폴더, 설정 파일(`SETTINGS_PATH`, 마지막 폴더 기억용 JSON. 프로그램 폴더 밖 홈 디렉터리에 저장), 단계 필터 선택
* **Output:**
  * 프로젝트 구조: `self.projects`(dict 목록: `proj`, `img_root`, `name`, `out_dir`, `by_rel`, `by_name`), `self.proj_of`(이미지→프로젝트), `self.folders`
  * 목록: `self.folder_images`(폴더 전체), `self.images`(단계 필터 적용 작업 목록)
  * 상태 집합: `self.done`(저장 이력 있는 이미지), `self.passed`(진행률용)
  * UI: `folderSelect`, `stageSelect`, `imageList`, `progressBar`, `progressText`

---

## 3. 주요 기능 및 구성 (Core Features)
* **경로 도우미:** `P(p)`(소속 프로젝트), `rel_of(p)`, `disp(p)`(프로젝트가 2개 이상이면 프로젝트명 포함)
* **프로젝트 루트 탐색(`_find_roots`):** ① 선택 폴더 자체에 `images`+`labels`가 있으면 그 폴더, ② 선택 폴더가 `images`이면 상위 폴더와 함께, ③ 바로 아래 하위 폴더 중 `images`+`labels`를 가진 것들(`*_labeled` 폴더 제외), ④ 없으면 선택 폴더 자체를 이미지 폴더로 사용
* **폴더 열기(`open_folder`):** 수동 선택 시 폴더 선택 창을 반복(`askdirectory` + "다른 폴더도 추가하시겠습니까?")해 여러 프로젝트 선택 가능. 시작 시 자동 열기(`auto_picked`)는 창 없이 진행
  * 프로젝트마다 `labels` 폴더를 순회해 `.txt/.csv`를 `by_rel`(상대경로)·`by_name`(파일명) 색인으로 저장 (프로그램 결과 폴더는 `is_output_dir`로 제외)
  * `img_root`를 순회해 `IMG_EXTS` 이미지를 폴더 키 `프로젝트명|상대폴더`로 묶고 `proj_of` 구성 (결과 폴더 제외)
  * 상태 초기화(`annotations`, `notes`, `review_status`, `done`, `passed`, `auto_pred`) → 프로젝트별 `prepare_out_dir` → `saved_stages(p)`가 있는 이미지를 `done`에 등록, `passed = set(done)`
* **폴더 선택:** `folderSelect`는 "(전체 이미지)" + 각 폴더. `load_folder`는 "(전체 이미지)"일 때만 단계 선택 행(`stageRow`)을 보이고, 개별 폴더면 숨기며 필터를 "전체"로 되돌림
* **단계 필터:** `_match_filter`는 `latest_stage(p) == view_filter`로 판단(가장 최근 저장 단계 = 현재 단계). `on_stage_filter_select`는 "전체"가 아닌 단계를 고르려면 저장 위치가 정해져 있어야 하며(`ensure_out_dir`), 없으면 먼저 선택하게 함. `update_stage_counts`는 콤보박스 항목에 `단계 (개수)`로 표시
* **작업 목록 구성(`apply_filter`):** 현재 이미지의 메모·미지정 박스 정리 → `self.images` 재구성 → 목록/진행률/단계 개수 갱신 → 비어 있으면 `clear_view` + 안내 → 아니면 `keep` 이미지 → 없으면 **저장 안 한 첫 이미지** → 없으면 0번을 표시
* **목록 색상(`refresh_image_list`):** 저장 이력(`done`) = `DONE_LIST_COLOR`, 일괄 추론 결과가 있고 미확인(`auto_pred`) = `AUTO_LIST_COLOR`, 그 외 검정
* **진행률(`update_progress`):** 보기 필터와 무관하게 **폴더 전체**(`folder_images`) 중 `passed`에 속한 비율. `passed`는 저장 이력이 있는 이미지 + "다음"으로 넘어간 이미지이며, "이전"으로 돌아가면 해당 이미지가 빠짐 (navigation_mixin이 갱신)
* **마지막 폴더 기억:** `save_last_folder`(폴더 목록 + 보던 이미지 저장), `load_last_folder`(존재하는 폴더만 복원), `remember_folder`(열기·이미지 전환 때마다 호출)

---

## 4. 예외 처리 및 UI 안정성 (Validation & Safety)
* **이미지 없음:** 수동 선택일 때만 경고창을 띄우고 열기를 중단(기존 상태 유지). 자동 열기에서는 조용히 반환
* **설정 파일 입출력:** 저장 시 `OSError`는 무시. 복원 시 `OSError`/`ValueError`/`TypeError`는 `(None, None)`을 반환해 앱이 정상 시작
* **사라진 폴더/이미지:** 복원 시 존재하지 않는 폴더는 제외, 마지막 이미지는 파일이 있을 때만 기억
* **작업 보존:** 폴더 전환·필터 변경 전에 현재 이미지의 메모와 미지정 박스를 정리
* **디렉터리 접근 오류:** 하위 폴더 탐색 중 `OSError`는 건너뜀

---

## 5. 핵심 처리 로직 (Logic Flow)
1. `open_folder()` → 폴더 선택(또는 자동 복원) → 프로젝트·이미지·라벨 색인 구성
2. 상태 초기화 + 출력 구조 준비 + 저장 이력 반영
3. `load_folder("__all__")` → `apply_filter()` → 목록·진행률 갱신 → 첫 표시 이미지 `show_image`
4. 이후 이미지 전환 때마다 `remember_folder()`로 위치 저장

---

## 6. 테스트 및 확인 방법 (Test)
* **Smoke Test:**
  1. `images`+`labels`가 있는 폴더를 열면 이미지 목록이 로드되고 저장된 이미지는 초록색으로 표시되는지 확인
  2. 단계 콤보박스(`1차 (12)` 형태)를 바꾸면 개수와 이미지 목록이 해당 단계 기준으로 필터링되는지 확인
  3. 앱을 종료 후 재실행하면 직전 폴더와 보던 이미지가 자동으로 열리는지 확인
  4. 이미지가 없는 폴더를 선택하면 경고가 뜨고 기존 작업이 유지되는지 확인
  5. 여러 폴더를 연속 선택해 열었을 때 목록에 프로젝트명이 붙는지 확인
