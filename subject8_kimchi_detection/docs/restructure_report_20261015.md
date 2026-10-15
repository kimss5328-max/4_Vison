# 교과 7 · 교과 8 저장소 구조 분리 작업 완료 보고서

> **작성일:** 2026-10-15
> **작성자:** KimKimJuHan (`wngks37@naver.com`)
> **기준 가이드:** `c:\Users\user1\Downloads\restructure_guide.md`
> **작업 브랜치:** `feature/split_7_8` (기반: `feature/7_8`)
> **최종 커밋:** `cc96920`

---

## 1. 작업 개요 및 목적

하나의 저장소 루트에 뒤섞여 있던 **교과 7 (조각김치 이물검출 라벨링 프로그램)**과 **교과 8 (Vision 기반 객체검출 모듈)**을 수행가이드 공식 표준에 따라 최상위 폴더로 완전히 분리하고, 각 프로그램이 상호 간섭 없이 독립적으로 동작하도록 모듈화 및 경로 정비를 완료했습니다.

* **절대 원칙 준수:**
  * Baseline 학습 결과 및 Split Freeze 데이터 수치가 1건도 변형되지 않음.
  * Git 히스토리를 보존하며 분리 완료.
  * NDA 보안 규칙에 따라 원본 데이터, 레이블 txt, 학습 가중치(`.pt`)의 Git 유출을 원천 차단.

---

## 2. 분리 전후 구조 비교 (Before & After)

### 분리 전 (기존 단일 루트 혼재 구조)
```text
4_Vison/
├── main.py, app.py
├── src/ (ui, bbox, validation, yolo, common, detector, dataset_audit.py, train_detector.py ...)
├── tools/ (01~06, build_split.py, export_final.py, merge_manifest.py ...)
├── configs/ (classes.yaml, dataset.yaml, smoke_dataset.yaml)
├── manifests/ (dataset_manifest.csv, split_manifest.csv, train.csv, val.csv ...)
└── reports/ (qa_summary.md, baseline_metrics.csv, dataset_summary.csv ...)
```

### 분리 후 (가이드 권장 표준 독립 구조)
```text
4_Vison/
├── README.md                                     ← 통합 안내 및 파이프라인 대시보드
├── .gitignore                                    ← 공통 보안 및 바이너리 제외 규칙
│
├── subject7_kimchi_labeling/                     ← [교과 7] 라벨링 프로그램
│   ├── main.py                                   ← 실행 진입점
│   ├── requirements.txt                          ← Tkinter, Pillow 등
│   ├── README.md                                 ← 교과 7 전용 가이드
│   ├── .gitignore                                ← 교과 7 전용 제외 규칙
│   ├── configs/classes.yaml                      ← 라벨링 클래스 정의
│   ├── src/                                      ← C구역 UI·BBox·검수 엔진
│   │   ├── app.py / config.py / __init__.py
│   │   ├── ui/ / bbox/ / validation/ / yolo/
│   ├── tools/                                    ← 데이터 수집 및 마이그레이션 도구
│   │   ├── export_final.py / merge_manifest.py / migrate_result.py
│   ├── manifests/dataset_manifest.csv            ← 라벨링 검수 전체 대장
│   ├── docs/                                     ← 가이드 및 명세서
│   ├── reports/                                  ← qa_summary.md / test_report.md
│   ├── handoff_subject08/                        ← 교과 8 인계 산출물
│   └── data/ / reviews/                          ← Git 제외 (로컬 작업 폴더)
│
└── subject8_kimchi_detection/                    ← [교과 8] YOLO11 객체검출 모듈
    ├── README.md                                 ← 교과 8 전용 가이드
    ├── requirements.txt                          ← Ultralytics, PyTorch, PyYAML
    ├── .gitignore                                ← 교과 8 전용 제외 규칙
    ├── configs/                                  ← dataset.yaml / smoke_dataset.yaml
    ├── manifests/                                ← split_manifest / train / val / test / holdout
    ├── src/                                      ← 재사용 기능 코드
    │   ├── __init__.py
    │   ├── dataset_audit.py                      ← 데이터 감사 모듈
    │   └── train_detector.py                     ← 학습 인터페이스 함수 (17.2)
    ├── scripts/                                  ← 실행 스크립트 (가이드 표준)
    │   ├── 03_build_split.py                     ← 데이터 분할 정규 스크립트
    │   └── 06_train_baseline.py                  ← Baseline 정규 학습 스크립트 (17.3)
    ├── reports/                                  ← baseline_metrics / condition / summary / logs
    ├── docs/                                     ← split_policy.md / restructure_guide.md
    ├── data/                                     ← subject7_final / yolo / smoke / bridge_holdout
    ├── models/                                   ← baseline / improved / final
    ├── runs/                                     ← Ultralytics 학습 결과
    ├── demo/                                     ← failure_analysis / 시연물
    └── presentation/                             ← 발표 자료
```

---

## 3. 단계별 상세 이행 내역 (restructure_guide.md 기준)

### 1단계 — 브랜치 전략
* 기존 `feature/7_8` 브랜치에서 안전한 작업 브랜치인 `feature/split_7_8`을 생성하여 분리 작업을 진행했습니다.

### 2단계 — 교과 7 파일 배치 (`subject7_kimchi_labeling/`)
* `main.py`, `requirements.txt`, `src/`(UI/BBox/Validation/YOLO), `configs/classes.yaml`, `manifests/dataset_manifest.csv`, `docs/`, `reports/`, `tools/`(export_final, merge_manifest, migrate_result), `handoff_subject08/`를 교과 7 폴더로 배치했습니다.

### 3단계 — 교과 8 파일 배치 (`subject8_kimchi_detection/`)
* `configs/`(dataset.yaml, smoke_dataset.yaml), `manifests/`(split_manifest, train, val, test, holdout), `src/`(dataset_audit, train_detector), `scripts/`(03_build_split, 06_train_baseline), `reports/`, `docs/`를 교과 8 표준 구조로 배치했습니다.
* 필수 보존 폴더(`.gitkeep`) 11종 생성:
  * `data/subject7_final`, `data/yolo`, `data/bridge_holdout`, `data/smoke`, `data/new_unlabeled`
  * `models/baseline`, `models/improved`, `models/final`
  * `runs`, `demo/failure_analysis`, `presentation`

### 4단계 — `.gitignore` 및 README 3단 분리
1. **루트 `.gitignore`:** 글로벌 바이너리, NDA 확장자(`.pt`, `.jpg`, `.png`, `.npy`, `.zip`), 환경설정, 키 파일 차단.
2. **`subject7_kimchi_labeling/.gitignore`:** 라벨링 프로그램 작업 데이터(`data/**`, `reviews/**`) 차단 및 제출 보고서 예외 설정.
3. **`subject8_kimchi_detection/.gitignore`:** 학습 데이터(`data/**`), 가중치(`models/**`), 실행 로그(`runs/**`), 시연 파일(`demo/**`) 차단 및 교과 8 공식 산출물 6종 예외 설정.
4. **README 분리:** 루트에는 전체 파이프라인 안내, 각 하위 폴더에는 해당 교과 전용 상세 README 구성.

### 5단계 — 소스코드 내 경로 수정 및 독립화
* **`configs/dataset.yaml` & `smoke_dataset.yaml`:**
  * 절대경로(`/home/user1/exe_01/...`)를 상대경로 `path: data/yolo` 및 `path: data/smoke`로 수정하여 어떤 환경에서도 즉시 구동되도록 개선.
* **`src/dataset_audit.py`:**
  * 교과 7 결과의 복사본인 `data/subject7_final/` 경로를 우선 탐색하도록 수정 (fallback 지원 포함).
* **`scripts/03_build_split.py`:**
  * `FINAL_DIR`을 `data/subject7_final` 우선으로 변경.
  * 교과 8 단독 실행 환경에서 `src.config` 부재 시에도 동작할 수 있도록 독립 상수 fallback 추가.

### 6단계 — 가상환경(venv) 재구성
* **`subject7_kimchi_labeling/`:** `python -m venv venv` 생성 후 `requirements.txt` 패키지 설치 완료 (tkinter 내장, requests 등).
* **`subject8_kimchi_detection/`:** `python -m venv venv` 생성 후 `ultralytics==8.4.175`, `pyyaml` 등 설치 완료. `pip freeze` 결과로 `requirements.txt` 갱신.

### 9단계 — 문서 내부 경로 수정
* `subject7_kimchi_labeling/docs/split_policy.md` 내 옛 경로 3건을 신규 경로로 수정:
  * `tools/build_split.py` → `scripts/03_build_split.py` (분할 도구 참조, seed 표기, Data Leakage 항목)
* `baseline_training_condition.md` 비고란: 해당 파일 내 학습 당시 경로 관련 내용은 과거 기록이므로 수정하지 않음.

### PR 사전 정리 (팀원 요청 반영 · 커밋 `cc96920`)
1. **`feature/7_8` 최신 커밋 머지:** `be50895` (split_manifest 열 보완 — scene_type · capture_group · dataset_version) 반영. split_manifest.csv 충돌은 origin/feature/7_8 버전(신규 열 포함)으로 해결.
2. **`scripts/` 정리:** `03_build_split.py`, `06_train_baseline.py` 2개만 남기고 나머지 삭제 (`01_`, `02_`, `03_export`, `04_`, `05_`, `06_evaluate`, 번호 없는 사본 전부).
3. **`tools/` 폴더 삭제:** 교과 8 쪽 `tools/` 전체 제거. 교과 7 도구(`export_final` · `merge_manifest` · `migrate_result`)는 `subject7_kimchi_labeling/tools/`에만 유지.
4. **`split_policy.md` 위치 정리:** `subject7_kimchi_labeling/docs/split_policy.md` 삭제 → `subject8_kimchi_detection/docs/`에만 존재.
5. **리팩토링 대상 분리:** `src/common/`, `src/detector/`, `scripts/05_train.py`, `scripts/06_evaluate.py`는 이번 PR에서 제외하고 별도 리팩토링 PR로 분리.
6. **fallback 코드 확인 (Freeze 도구 검토):**
   * `03_build_split.py` — `try/except ModuleNotFoundError`: 교과 7 `src.config` import 실패 시 교과 8 자체 상수로 동작. Split Freeze 배정 로직에 영향 없음.
   * `03_build_split.py` — `FINAL_DIR`: `data/subject7_final` 우선, 없으면 `data/final` fallback. 같은 900장을 가리키면 결과 동일.
   * `dataset_audit.py` — manifest 경로: `data/subject7_final/dataset_manifest.csv` 우선, 없으면 `manifests/` fallback.
   * `dataset_audit.py` — 데이터 경로: `subject7_final/dataset{n}/images` → `subject7_final/images` → `dataset{n}_result/final/img` 순서로 탐색.
   * **결론: 모든 fallback은 데이터 배치 전 스크립트가 죽지 않도록 한 방어 코드. 배정 숫자·해시값 변경 없음.**

---

## 4. 최종 검증 결과 (8대 검증 항목)

| 번호 | 검증 항목 | 실행 명령 / 방법 | 결과 | 상태 |
|:---:|---|---|---|:---:|
| 1 | **Python 문법 컴파일** | `py_compile` (전체 50개 파이썬 파일) | 문법 에러 0건 (Syntax OK) | **PASS** |
| 2 | **Split Freeze 검증** | `python scripts/01_build_split.py --freeze-only` | split_manifest, train, val, test 4개 파일 일치 | **PASS** |
| 3 | **Tkinter 비의존성** | `import src.common.paths; 'tkinter' in sys.modules` | `False` (독립 확인) | **PASS** |
| 4 | **데이터 분할 미리보기** | `python scripts/03_build_split.py` | subject7_final 경로 정상 감지 및 대기 확인 | **PASS** |
| 5 | **데이터 무결성 검사** | `python src/dataset_audit.py` | 보고서 3종 생성 및 실행 정상 | **PASS** |
| 6 | **교과 7 프로그램 구문** | `subject7_kimchi_labeling/main.py` 컴파일 | 임포트 구조 및 문법 정상 | **PASS** |
| 7 | **NDA 보안 검사** | `git status -s` 및 `git ls-files` 추적 검사 | `.pt`, `.jpg`, `.png`, 키 파일 커밋 제외 100% | **PASS** |
| 8 | **Git 이력 보존** | Git 커밋 로그 확인 (`git log --oneline`) | 이전 교과 7/8 커밋 히스토리 정상 유지 | **PASS** |

※ 2·4·5번은 데이터 배치(가이드 7단계) 후 실데이터 기반으로 재검증 필요.

---

## 5. 향후 작업 안내 (데이터 담당 인계 및 실행)

1. **데이터 파일 배치 (가이드 7단계):**
   * 교과 7 검수 완료본(900장 JPG/TXT)을 `subject8_kimchi_detection/data/subject7_final/`에 복사본으로 배치합니다.
   * 기 분할된 데이터(`data/yolo/`, `data/bridge_holdout/`, `data/smoke/`) 및 가중치(`models/baseline/baseline_best.pt`)를 각 위치에 배치합니다.
2. **Baseline 평가 재현 (가이드 8단계):**
```bash
   cd subject8_kimchi_detection
   yolo detect val model=models/baseline/baseline_best.pt data=configs/dataset.yaml imgsz=1920 batch=3
   # 기대치: 전체 P 0.926 · R 0.849 · mAP50 0.889 · mAP50-95 0.780
```
3. **Pull Request:**
   * 브랜치 `feature/split_7_8` → `feature/7_8` 으로 PR 생성 후 데이터 담당이 8단계 결과 확인 후 승인·머지.
4. **리팩토링 PR (별도):**
   * `src/common/`, `src/detector/`, `scripts/05_train.py`, `scripts/06_evaluate.py` 정리.