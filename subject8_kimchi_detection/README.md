# Vision 기반 조각김치 이물검출 모듈 (YOLO11)
> 최종 갱신: 2026-10-20

## 1. 프로젝트 목적
교과 7에서 검수 및 확정한 조각김치 이미지 900장과 YOLO TXT 900개를 활용하여, YOLO 기반 조각김치 이물검출 모델을 학습하고 평가하는 프로젝트입니다.

## 2. 교과 7 → 교과 8 연결
- **이전 단계(교과 7) 요약:** Tkinter 기반 라벨링 프로그램으로 900장 전수 검수 및 품질 검사 완료
- **QA 결과 (교과 7 종료 시점):** PASS 729 · FAIL 0 · REVIEW 171 · 오류 0 (REVIEW 는 Class 4 고무장갑 관련)
- **데이터 구축 · 수정:** Tkinter 기반 라벨링 프로그램 제작 → 1차 · 2차 검수 → Human QA 900장 전수 확인 · 수정 40건 (Class 5 · BBox 30 · 좌표 5) → 재검사 오류 0 → FINAL 900장 정리

| 교과 7 결과물 (FINAL)     | Dataset 1 | Dataset 2                  | 합계                         |
| -------------------- | --------- | -------------------------- | -------------------------- |
| 이미지 / YOLO 라벨        | 500 / 500 | 400 / 400                  | 900 / 900                  |
| 원본 구조                | train 500 | train 220 · validation 180 | train 720 · validation 180 |
| BBox (Class 0~6, 7개) | 2,677     | 1,756                      | 4,433                      |
- **변경 사항:** 팀 회의 결정으로 Class 4 고무장갑을 다시 사용 → 해당 이미지 재라벨링 완료
- **인수인계 데이터 (FINAL Dataset):** `data/final/` 에 정리된 이미지·라벨을 학습용 폴더에 분할

## 3. Dataset 설명
- **Dataset Version:** `kimchi_v1` (train `57f0bf5121e4` / val `ab6cc7f98da7`)
- **입력 데이터:** 조각김치 이미지 900장 (JPG, 4848×2704) + YOLO Detection TXT 900개
- **장면 유형(Scene Type):** `kimchi_with_target` 587장 · `object_only` 138장 · `other_review` 175장 (합계 900장)
- **Split Freeze:** `manifests/split_manifest.csv` @ `1b074fa`

## 4. Class
본 프로젝트에서 탐지할 7개 클래스 목록입니다. (7개 모두 사용)

| ID  | 이름         | 사용 여부            |
| --- | ---------- | ---------------- |
| 0   | 나뭇잎·종이류    | 사용               |
| 1   | 플라스틱·돌·금속류 | 사용               |
| 2   | 나뭇가지류      | 사용               |
| 3   | 벌레류        | 사용               |
| 4   | 고무장갑       | 사용 (Class 4 재사용) |
| 5   | 병해·갈변      | 사용               |
| 6   | 파·고추       | 사용               |

*(클래스별 상세 판단 기준은 `docs/class_guide.md` 참고)*

> 7~12번의 결과는 모두 **클래스별(0~6, 7클래스) 학습** 기준입니다. 모든 이물을 `item` 하나로 합친 단일 클래스(single_cls) 실험과 해상도 비교 실험은 부록 E에 참고로 정리했습니다.

## 5. 실행환경
### 5-1. 환경
| 항목          | 값                       |
| ----------- | ----------------------- |
| OS          | Windows + WSL2 (Ubuntu) |
| Python      | 3.10.12                 |
| Ultralytics | 8.4.175 (YOLO11)        |
| PyTorch     | 2.14.1+cu130            |
| GPU         | NVIDIA RTX 3060 12GB    |

- 학습 · 평가 · 추론은 모두 위와 같은 사양 · 같은 패키지 버전에서 실행했습니다 (`requirements.txt`).

### 5-2. 패키지 설치
```bash
cd subject8_kimchi_detection
pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements.txt
python -c "import ultralytics, torch, numpy; print(ultralytics.__version__, torch.__version__, numpy.__version__, torch.cuda.is_available())"
# 8.4.175 2.14.1+cu130 2.2.6 True
```
- PyTorch 는 GPU(CUDA 13.0) 빌드를 쓰기 위해 먼저 따로 설치합니다. `requirements.txt` 만으로 설치하면 다른 빌드가 설치될 수 있습니다.

| 패키지 (`requirements.txt`) | 버전 |
|---|---|
| ultralytics | 8.4.175 |
| ultralytics-thop | 2.2.2 |
| torch | 2.14.1 |
| torchvision | 0.29.1 |
| opencv-python | 5.0.0.93 |
| numpy | 2.2.6 |
| PyYAML | 6.0.3 |

*(교과 7 라벨링 툴 실행 환경은 `subject7_kimchi_labeling/requirements.txt` 참고)*

### 5-3. 디렉토리 구조
```text
subject8_kimchi_detection/
├── README.md                          # 본 문서
├── requirements.txt                   # 필수 패키지 목록
│
├── configs/
│   ├── dataset.yaml                   # YOLO 학습 데이터 설정 (train/val/test · Bridge Holdout 미포함)
│   └── smoke_dataset.yaml             # Smoke Test 설정 (표본 50장)
│
├── manifests/
│   ├── split_manifest.csv             # 4개 역할 전체 분할 대장 (Split Freeze)
│   ├── train.csv                      # 학습 데이터 (600장)
│   ├── val.csv                        # 검증 데이터 (100장)
│   ├── test.csv                       # Frozen Test (100장)
│   ├── bridge_holdout.csv             # 교과 14 보존용 (100장)
│   ├── smoke_split_manifest.csv       # Smoke Test 표본 분할 대장
│   └── dataset_manifest.csv           # 교과 7 입력 메타데이터
│
├── src/                               # 재사용 핵심 모듈
│   ├── __init__.py
│   ├── dataset_audit.py               # 데이터 정합성 감사 모듈
│   ├── train_detector.py              # YOLO11 학습 인터페이스 함수 (17.2)
│   └── failure_analyzer.py            # Failure Analysis 모듈 자리 (분석 기록은 reports/failure_analysis.csv 수작업)
│
├── scripts/                           # 순서별 실행 스크립트
│   ├── 03_build_split.py              # 데이터 분할 · Split Freeze
│   ├── 06_train_baseline.py           # Baseline 정규 학습 스크립트 (17.3)
│   ├── 11_evaluate_final_test.py      # Frozen Test 1회 평가 (21.2)
│   └── 12_auto_label_candidates.py    # Auto Label 후보 생성 (21.4)
│
├── models/                            # (GitHub 미포함)
│   ├── baseline/                      # baseline_best.pt
│   ├── improved/                      # exp001_best.pt
│   └── final/                         # final_best.pt
│
├── runs/                              # (GitHub 미포함) 학습 · 평가 산출물
│   ├── baseline_v1/                   # Baseline 학습 (results.csv · weights)
│   └── final_test/                    # Frozen Test 평가 (Confusion Matrix · PR Curve)
│
├── reports/                           # 산출물 보고서
│   ├── dataset_summary.csv            # 데이터 감사 요약
│   ├── smoke_test.md                  # Smoke Test 결과 및 해상도 선정 기록
│   ├── baseline_training_condition.md # Baseline 학습 조건 및 환경 기록
│   ├── baseline_metrics.csv           # Baseline 성능 지표 (all 및 클래스별)
│   ├── failure_candidates.csv         # 실패분석 대상 후보 (19장)
│   ├── failure_analysis.csv           # 대표 실패 29건
│   ├── failure_hypothesis.md          # 원인 가설
│   ├── improvement_experiment.md      # EXP001 실험 계획
│   ├── experiment_log.csv             # 실험 기록
│   ├── baseline_vs_improved.md        # Baseline vs EXP001 비교
│   ├── final_model_selection.md       # Final Model 선택 근거
│   ├── final_metrics.csv              # Frozen Test 지표
│   ├── auto_label_review.csv          # Auto Label 검수 집계
│   ├── acceptance_test.md             # Acceptance Test
│   ├── subject08_handoff.md           # 교과 7 → 8 인수 기록
│   ├── figures/                       # 학습곡선 · Confusion Matrix · PR Curve (그래프만)
│   ├── assets/                        # 문서용 그래프
│   └── logs/build_split/              # 분할 실행 기록
│
├── demo/                              # (GitHub 미포함 — 원본 이미지 포함)
│   ├── prediction_images/             # Detection 결과 이미지 (8장)
│   ├── auto_label/                    # candidate_labels/ · reviewed_labels/ (각 8개)
│   └── failure_analysis/              # 대표 실패 이미지 (29장)
│
├── docs/
│   ├── split_policy.md                # 층화 분할 정책 및 Freeze 사유
│   ├── class_guide.md · bbox_guide.md # Class · BBox 판단 기준 (교과 7)
│   ├── 교과8-Handoff.md                # 교과 7 인계 문서 사본
│   └── 교과14-Handoff.md               # 교과 14 인계 문서
│
├── presentation/                      # 발표 자료
│
└── data/                              # 학습용 데이터셋 (NDA, GitHub 미포함)
    ├── subject7_final/                # 교과 7 수령 FINAL 데이터
    ├── yolo/                          # YOLO images/labels (train, val, test)
    ├── bridge_holdout/                # 교과 14 보존 데이터
    ├── smoke/                         # Smoke Test 표본 (50장)
    └── new_unlabeled/                 # 라벨 없는 새 이미지 (Auto Label 대상 8장)
```

### 5-4. 순서별 실행 명령어
프로젝트 폴더(`subject8_kimchi_detection/`)에서 실행합니다.

1. **데이터 정합성 및 무결성 검사**
   ```bash
   python src/dataset_audit.py
   # 산출물: reports/dataset_summary.csv
   ```

2. **Split Freeze 확인** (미리보기 — `split_manifest.csv` 배정을 그대로 사용, 파일을 만들지 않음)
   ```bash
   python scripts/03_build_split.py --include all --counts 600 100 100 100
   ```

3. **Smoke Test 표본 만들기** (기록용 — 이미 만들어 두었으므로 **다시 실행하지 않음**. 다시 실행하면 Smoke 표본이 새로 만들어짐)
   ```bash
   python scripts/03_build_split.py --limit 50 --apply
   # data/smoke + configs/smoke_dataset.yaml
   ```

4. **Baseline 모델 학습** (조건은 스크립트에 고정: yolo11n · imgsz 1920 · 100 epoch · batch 3 · seed 0)
   ```bash
   # 시험 실행 (1 epoch)
   python -u scripts/06_train_baseline.py --epochs 1 --name baseline_dryrun

   # 정규 Baseline 학습
   python -u scripts/06_train_baseline.py 2>&1 | tee runs/baseline_v1.log
   ```

5. **Validation 평가** (Ultralytics CLI)
   ```bash
   yolo detect val model=models/baseline/baseline_best.pt data=configs/dataset.yaml imgsz=1920 batch=3 plots=True project=$PWD/runs name=baseline_val
   ```
   - `plots=True` 가 없으면 Confusion Matrix 가 집계되지 않음
   - `project=` 를 절대경로로 주지 않으면 Ultralytics 전역 설정 위치로 저장될 수 있음

6. **Frozen Test** (Final Model 선택 후 **1회만** — 이미 실행 완료, 다시 실행하지 않음)
   ```bash
   python scripts/11_evaluate_final_test.py
   # runs/final_test/ → reports/final_metrics.csv · reports/figures/final_test_*.png
   ```

7. **Detection · Auto Label 후보 생성**
   ```bash
   python scripts/12_auto_label_candidates.py
   # data/new_unlabeled → runs/auto_label_candidates/ (박스 그린 이미지 · labels/*.txt)
   # → demo/prediction_images/ · demo/auto_label/candidate_labels/ 로 복사

   yolo predict model=models/final/final_best.pt source=<이미지 폴더> imgsz=1920 conf=0.25 save=True
   ```
   - 추론 조건은 교과 8 Detection · Auto Label 과 같음 (imgsz 1920 · conf 0.25)
   - 사람 검수는 교과 7 라벨링 프로그램(`subject7_kimchi_labeling/main.py`)에서 후보 TXT 사본 폴더를 열어 진행

## 6. Dataset Split
- **전체 데이터:** 900장
- **분할 개수:** Train 600 / Validation 100 / Frozen Test 100 / Bridge Holdout 100
- **산출물 기준**: `reports/logs/build_split/build_split_20261013_111107.md` 파일 참고
- Final 기준 : `export_final_20261013_111104.md` 파일 참고

| 세트             | 장수  | 비율    | 역할                                      |
| -------------- | --- | ----- | --------------------------------------- |
| Train          | 600 | 약 67% | 모델 가중치 학습                               |
| Validation     | 100 | 약 11% | 학습 중 성능 모니터링, Best Epoch 선정, 설정 비교      |
| Frozen Test    | 100 | 약 11% | 최종 모델의 일반화 성능 평가 (Final 선택 후 1회만)       |
| Bridge Holdout | 100 | 약 11% | 별도 보관하는 독립 평가용 데이터 (교과 14용, 교과 8에서 미사용) |

- **분할 방식:** 대표 클래스 기준 층화 분할 (이미지 안에서 가장 드문 클래스를 대표 클래스로 두고 클래스 비율 유지) → 모든 Class 가 Train 에 63~67%, Seed 42 고정
- **Data Leakage 점검:** 900장 파일 · 픽셀 SHA-256 중복 0건 · Smoke 표본은 본 분할 Train 에서만 추출(Test · Holdout 과 겹침 0장) · raw ↔ final 비교는 생략 (사유: `docs/split_policy.md`) · `capture_group`(촬영 묶음) 누수는 미확인

**Class · 박스 (이미지) 분포**

| Class       | Train       | Val      | Test     | Holdout  | 합계          |
| ----------- | ----------- | -------- | -------- | -------- | ----------- |
| 0 나뭇잎·종이    | 492 (192)   | 84 (32)  | 76 (36)  | 93 (43)  | 745 (303)   |
| 1 플라스틱·돌·금속 | 1,045 (355) | 179 (57) | 171 (65) | 186 (65) | 1,581 (542) |
| 2 나뭇가지      | 586 (232)   | 97 (41)  | 101 (48) | 96 (43)  | 880 (364)   |
| 3 벌레        | 260 (131)   | 46 (22)  | 38 (24)  | 34 (19)  | 378 (196)   |
| 4 고무장갑      | 188 (100)   | 34 (16)  | 27 (17)  | 34 (19)  | 283 (152)   |
| 5 병해·갈변     | 225 (98)    | 31 (16)  | 31 (16)  | 29 (16)  | 316 (146)   |
| 6 파·고추      | 165 (33)    | 30 (6)   | 30 (6)   | 25 (5)   | 250 (50)    |
| **박스 합계**   | 2,961       | 501      | 474      | 497      | 4,433       |
| **이미지 수**   | 600         | 100      | 100      | 100      | 900         |

**scene_type 분포 (이미지)**

| scene_type | Train | Val | Test | Holdout | 합계 |
|---|---|---|---|---|---|
| kimchi_with_target | 397 (68%) | 68 (12%) | 57 (10%) | 65 (11%) | 587 |
| object_only | 89 (64%) | 12 (9%) | 23 (17%) | 14 (10%) | 138 |
| other_review | 114 (65%) | 20 (11%) | 20 (11%) | 21 (12%) | 175 |
- **Split Freeze:** 분할은 `manifests/split_manifest.csv` 로 고정 (commit `1b074fa`). **`03_build_split.py --force` 재실행 금지** (`--force` 는 기존 배정을 버리고 새로 나눔)
- **Bridge Holdout:** `data/bridge_holdout/` 에 별도 보관하며 `configs/dataset.yaml` 에 포함하지 않음
- **상세 기준:** `docs/split_policy.md` 참고

**최초 분할 명령어 (기록용 — 다시 실행하지 않음):**
```bash
python3 scripts/03_build_split.py --include all --counts 600 100 100 100 --apply
```

| 산출물            | 위치                                                                                       |
| -------------- | ---------------------------------------------------------------------------------------- |
| 학습용 데이터        | `data/yolo/{images,labels}/{train,val,test}`                                             |
| Bridge Holdout | `data/bridge_holdout/{images,labels}`                                                    |
| 학습 설정          | `configs/dataset.yaml`                                                                   |
| 분할 기록          | `manifests/split_manifest.csv`, `train.csv`, `val.csv`, `test.csv`, `bridge_holdout.csv` |

## 7. Smoke Test
- **목적:** 작은 데이터로 학습 → Weight 생성 → Prediction 까지 Pipeline 이 정상 동작하는지 확인 (성능 확인 단계 아님)

| 실행                                          | 조건                                 | 표본 · 데이터            | Precision | Recall    | mAP50 | mAP50-95  |
| ------------------------------------------- | ---------------------------------- | ------------------- | --------- | --------- | ----- | --------- |
| `smoke_multi`                               | 640 · 3 epoch                      | v4 표본 50장           | -         | -         | -     | 0.016     |
| `full_multi_640_e30`                        | 640 · 30 epoch                     | train 600 / val 100 | 0.840     | 0.786     | 0.828 | 0.601     |
| `full_multi_1920_e100`<br>(==baseline_v1==) | 1920 · 100 epoch ·  batch auto(-1) | train 600 / val 100 | 0.926     | ==0.849== | 0.889 | ==0.780== |

- **해상도 비교 (Smoke Dataset 50장 · 90 epoch · Val 10장):** 960 · 1088 · 1440 · 1920 · 2432 를 같은 조건으로 비교 → 1920 이 박스 위치 정확도(단일 클래스 Smoke · mAP50-95 0.677)와 놓침 수에서 가장 좋음 →  Baseline 해상도로 채택 (상세: `reports/smoke_test.md`)
- **한계:** 위 해상도 비교는 Smoke 표본 v4 이전(구 표본에 Test 3장 · Holdout 3장 포함)으로 실행했습니다. 1920 결정은 전체 데이터(val 만 사용) 비교(단일 클래스 640 0.684 → 1920 0.832)로도 확인했습니다.
- 위 표의 640 · 30 epoch 와 1920 · 100 epoch 는 epoch 수가 달라 해상도만의 비교가 아닙니다 (참고용).

## 8. Baseline (`baseline_v1`)
- **조건 확정 근거:** Smoke Test 해상도 비교에서 1920 이 가장 좋음 · 원본 4848×2704 를 640 으로 줄이면(약 1/7.6) 작은 이물 경계가 흐려짐 · 참고 실행 7클래스 640 · 30 epoch 는 mAP50-95: 0.601

| 항목                          | 값                                                                    |
| --------------------------- | -------------------------------------------------------------------- |
| Model                       | YOLO11n (`yolo11n.pt` 사전학습에서 시작)                                     |
| Dataset                     | `kimchi_v1` · Train 600 / Val 100 (Frozen Test · Bridge Holdout 미사용) |
| Image Size                  | 1920                                                                 |
| Epoch                       | 100 (patience 30, 조기 종료 없음 · best epoch 90)                          |
| Batch                       | `-1` (AutoBatch 자동 결정 → 3)                                           |
| Seed                        | 학습 0 · 분할 42                                                         |
| Optimizer(가중치 방향) · LR(학습률) | auto → AdamW · lr 0.000909 · warmup 3 epoch                          |
| cache                       | ram                                                                  |
| 학습 시간                       | 약 53분 (2026-10-13 CLI 학습 기준)                                     |

- **재학습:** 2026-10-14 `scripts/06_train_baseline.py` 로 같은 조건 재학습 → `results.csv` 100행 · val 지표 모두 이전 CLI 학습과 동일. 현재 Weight (`baseline_best.pt`, sha256 `c90f9767442e`) 는 이 재학습 결과
- **상세 조건:** `reports/baseline_training_condition.md`

**결과 (Validation 100장 · 박스 501개)**

| 클래스          | 이미지 | 박스  | Precision | Recall        | mAP50         | mAP50-95      |
| ------------ | --- | --- | --------- | ------------- | ------------- | ------------- |
| **전체**       | 100 | 501 | **0.926** | **0.849**     | **0.889**     | **0.780**     |
| 0 나뭇잎·종이류    | 32  | 84  | 0.916     | 0.909         | 0.962         | 0.879         |
| 1 플라스틱·돌·금속류 | 57  | 179 | 0.975     | 0.911         | 0.953         | 0.829         |
| 2 나뭇가지류      | 41  | 97  | 0.889     | 0.897         | 0.949         | 0.850         |
| 3 벌레류        | 22  | 46  | 1.000     | 0.956         | 0.972         | 0.819         |
| 4 고무장갑       | 16  | 34  | 0.966     | 0.971         | 0.989         | 0.918         |
| 5 병해·갈변      | 16  | 31  | 0.739     | ==**0.367**== | ==**0.427**== | ==**0.338**== |
| 6 파·고추       | 6   | 30  | 1.000     | 0.933         | 0.972         | 0.830         |

- 위 표는 학습 종료 후 `best.pt` 로 검증한 값입니다 (`reports/baseline_metrics.csv`). `results.csv` 의 best epoch 90 행은 학습 중 검증값이라 P 0.932 · R 0.845 로 조금 다릅니다.
- **상세 지표:** `reports/baseline_metrics.csv`

## 9. Failure Analysis (Validation 기준)
- **분석 대상:** `baseline_v1` · Validation 100장 · 501 instances (Train · Frozen Test · Bridge Holdout 미사용)
- **가장 중요한 반복 실패:** 병해·갈변(Class 5)을 놓침 (FN) — 다른 Class 는 Recall 0.89 이상인데 병해·갈변만 0.367

| Class        | 이름    | val 이미지 | instances | Precision   | Recall        | mAP50       |
| ------------ | ----- | ------- | --------- | ----------- | ------------- | ----------- |
| 5            | 병해·갈변 | 16      | 31        | 0.739       | ==**0.367**== | **0.427**   |
| 나머지 6개 Class | —     | —       | —         | 0.889~1.000 | 0.897~0.971   | 0.949~0.989 |
- **원인 가설:**

| 범주                   | 판단                      | 근거                                                                                                  |
| -------------------- | ----------------------- | --------------------------------------------------------------------------------------------------- |
| **Model / Training** | **주 가설 (EXP001 실험 대상)** | 병해·갈변은 모양보다 색으로 구분됨. 기본 색상 Augmentation(`hsv_h` · `hsv_s` · `hsv_v`)이 갈변 색을 흔들어 정상 김치와 구분하지 못했을 가능성 |
| Label                | 남은 가설                   | 병해·갈변은 경계가 뚜렷하지 않아 BBox 범위 · 판정 기준이 이미지마다 다를 가능성. 재라벨링은 작업 부담이 커 이번에는 제외                            |
| Inference            | 낮음                      | Precision 이 유지되고 Recall 만 낮음 → Threshold 조정으로는 되찾기 어려움                                              |

**병해·갈변 정답 31개의 예측 결과 (Baseline 혼동행렬 기준)**

| 병해·갈변으로 맞힘 | 배경으로 놓침    | 나뭇가지로 예측 | 나뭇잎으로 예측 | 플라스틱으로 예측 |
| ---------- | ---------- | -------- | -------- | --------- |
| 17         | ==**10**== | 2        | 1        | 1         |

- Recall 기준: 0.367 → 31개 중 약 20개 놓침 (Recall 로 계산) 
- 혼동행렬 기준: 17개 맞힘 · 14개 놓침/혼동 — 집계 기준(신뢰도)이 달라 수치가 다름
- 그 밖의 실패: 병해·갈변 오검출(FP) · 나뭇가지 ↔ 나뭇잎 혼동 · 같은 객체에 중복 박스

- **기록:** `reports/failure_analysis.csv` (대표 실패 29건) · `demo/failure_analysis/` · `reports/failure_hypothesis.md`

## 10. Improvement (7일차 · EXP001)
- **변경 변수 (1개):** 색상 Augmentation 끄기 (`hsv_h` 0.015 · `hsv_s` 0.7 · `hsv_v` 0.4 → 0)
- **선택 이유:** 병해·갈변만 Recall 이 단독으로 낮음 (다른 Class 0.89 이상) · Precision 이 유지되고 Recall 만 낮아 Threshold 조정으로는 되찾기 어려움 · 켬 / 끔 한 변수라 결과 해석이 분명함
- **유지 조건:** 모델 · imgsz 1920 · 100 epoch · batch 3 · seed 0 · 시작 가중치 · 다른 Augmentation · 라벨 · `kimchi_v1`

**지표 비교 (Validation)**

| 지표           | Baseline | EXP001 | 차이     |
| ------------ | -------- | ------ | ------ |
| Precision    | 0.926    | 0.937  | +0.011 |
| Recall       | 0.849    | 0.824  | −0.025 |
| mAP50        | 0.889    | 0.884  | −0.005 |
| mAP50-95     | 0.780    | 0.775  | −0.005 |
| 병해·갈변 Recall | 0.367    | 0.355  | −0.012 |
| 병해·갈변 mAP50  | 0.427    | 0.435  | +0.008 |

**실패 패턴 비교**

| 패턴                                    | Baseline | EXP001  | 판단              |
| ------------------------------------- | -------- | ------- | --------------- |
| 병해·갈변 정답 검출 (※ 9절 혼동행렬 17 과 집계 기준 다름) | 18 / 31  | 21 / 31 | 소폭 증가           |
| 병해·갈변 FN                              | 10 / 31  | 9 / 31  | 거의 같음           |
| 병해·갈변 FP (background → 병해·갈변)         | 762      | 501     | ==EXP001 −34%== |
| 나뭇가지 → 나뭇잎                            | 10       | 17      | ==🔴EXP001 악화== |
| 고무장갑 → 플라스틱                           | 11       | 15      | ==🔴EXP001 악화== |
| 나뭇가지류 Recall                          | 0.897    | 0.825   | ==🔴EXP001 악화== |

- Baseline 칸은 단독 val(18 / 762 / 10) 기준, 9절 혼동행렬 그림은 학습 종료 시 검증(17 / 764 / 10) 기준입니다.
- **결론:** 색상 Augmentation 을 끄는 것만으로는 병해·갈변 미검출이 해결되지 않음 → Label 가설의 가능성이 커짐
- 개선 실험이 Baseline 을 넘지 못한 것도 결과로 기록 (`reports/experiment_log.csv`)
- **상세:** `reports/improvement_experiment.md` · `reports/baseline_vs_improved.md`

## 11. Final Model
- **선택 원칙:** Frozen Test 를 보기 전에 Validation 근거로 선택
- **Final Model: Baseline (`baseline_v1`)**

| 판단 기준               | 결과                                                       |
| ------------------- | -------------------------------------------------------- |
| 주 목표 (병해·갈변 미검출 개선) | EXP001 도 해결 못 함 (Recall 0.367 → 0.355)                   |
| 전체 성능               | EXP001 이 Recall · mAP50 · mAP50-95 모두 낮음                 |
| 다른 클래스 영향           | EXP001 에서 나뭇가지 Recall −0.072, 가지 → 잎 · 고무장갑 → 플라스틱 혼동 증가 |
| EXP001 의 장점         | 병해·갈변 FP 34% 감소 · Precision +0.011                       |

- 이물검출은 **놓치는 것(FN)이 잘못 찾는 것(FP)보다 위험** — 이물이 섞인 제품이 그대로 통과하기 때문 → Recall 이 높은 Baseline 선택
- **가중치:** `models/final/final_best.pt` (`models/baseline/baseline_best.pt` 복사본, sha256 앞 12자리 `c90f9767442e`) — GitHub 미포함
- **추론 시간:** 이미지 1장 14.0 ms
- **상세:** `reports/final_model_selection.md`

## 12. Frozen Test
- **원칙:** Final Model 선택 후 1회만 실행, 결과를 보고 다시 튜닝하지 않음

| 클래스          | 이미지 | 박스  | Precision | Recall        | mAP50         | mAP50-95  |
| ------------ | --- | --- | --------- | ------------- | ------------- | --------- |
| **전체**       | 100 | 474 | **0.957** | **0.887**     | **0.919**     | **0.808** |
| 0 나뭇잎·종이류    | 36  | 76  | 0.946     | 0.882         | 0.927         | 0.840     |
| 1 플라스틱·돌·금속류 | 65  | 171 | 0.938     | 0.892         | 0.957         | 0.852     |
| 2 나뭇가지류      | 48  | 101 | 0.911     | 0.910         | 0.964         | 0.900     |
| 3 벌레류        | 24  | 38  | 0.998     | 0.974         | 0.994         | 0.835     |
| 4 고무장갑       | 17  | 27  | 0.925     | 0.912         | 0.899         | 0.808     |
| 5 병해·갈변      | 16  | 31  | 1.000     | ==**0.636**== | ==**0.698**== | ==0.539== |
| 6 파·고추       | 6   | 30  | 0.981     | 1.000         | 0.995         | 0.884     |

- Validation(0.780) 대비 **Frozen Test mAP50-95 : 0.808** 로 일반화 성능 유지
- 병해·갈변은 Test 에서도 Recall 0.636 으로 가장 낮음
- **상세 지표:** `reports/final_metrics.csv` · 그래프 `reports/figures/final_test_confusion_matrix.png` · `final_test_pr_curve.png`

## 13. Detection / Auto Label
- **대상 이미지:** 학습에 쓰지 않은 Frozen Test 8장 (seed 42 무작위 추출 · Frozen Test 평가가 끝난 뒤 사용)
- **Detection:** Final Model (`final_best.pt`) · imgsz 1920 · conf 0.25 → `demo/prediction_images/*.jpg` 8장 (BBox · Class · Confidence 표시)
- **실행:** `scripts/12_auto_label_candidates.py` (5-4 7단계)
- **Auto Label 흐름:** 후보 라벨 생성 → `demo/auto_label/candidate_labels/*.txt` 8개 → 교과 7 라벨링 도구(`subject7_kimchi_labeling/data/auto_label_review/` 사본)에서 사람 검수 → `demo/auto_label/reviewed_labels/*.txt` 8개 · `reports/auto_label_review.csv`

**Auto Label 검수 결과**

| 검수 이미지 | 후보 BBox | 그대로 승인 | Class 수정 | BBox 수정 | 삭제  | 누락 추가 | REVIEW |
| ------ | ------- | ------ | -------- | ------- | --- | ----- | ------ |
| 8      | 36      | **34** | 1        | 0       | 1   | 0     | 0      |

- 후보 36개 중 34개(약 94%)는 그대로 승인, 2개만 사람이 고침
- 검수 중 1장 저장 누락 → 다시 열어 저장 후 재확인 (14절 FAIL-01)
- 삭제 수는 교과 7 이력 csv 가 아니라 후보 TXT 와 검수 TXT 의 줄 수 비교로 집계 (이력 csv 에 삭제 박스가 남지 않은 사례가 있어서)
- **원칙:** Auto Label 결과는 사람 검수 전에는 정답으로 확정하지 않음

## 14. Acceptance Test
- **상세:** `reports/acceptance_test.md` (교과 8 수행가이드 22.7 기준 · FAIL 은 수정 후 Retest 까지 기록)

### 최종 판정

| 구분         | 항목 수   | PASS                        | 확인 필요 |
| ---------- | ------ | --------------------------- | ----- |
| Dataset    | 7      | 7                           | 0     |
| Model      | 5      | 5                           | 0     |
| Evaluation | 8      | 8                           | 0     |
| Inference  | 4      | 4                           | 0     |
| Auto Label | 5      | 5 (A5 는 FAIL → Retest PASS) | 0     |
| 재실행        | 2      | 2                           | 0     |
| **합계**     | **31** | **31**                      | **0** |

**FAIL 기록 (모두 수정 · Retest PASS)**

| #       | 문제                              | 원인                 | 조치                                               |
| ------- | ------------------------------- | ------------------ | ------------------------------------------------ |
| FAIL-01 | Auto Label 검수 1장이 후보와 같은 상태로 남음 | 검수 후 저장하지 않음       | 다시 열어 박스 1개 삭제 후 저장 · `auto_label_review.csv` 수정 |
| FAIL-02 | Frozen Test Script 실행 시 출력 없음   | 처음 저장한 파일이 0바이트    | 다시 저장 후 크기 확인 · 1회 실행                            |
| FAIL-03 | Confusion Matrix 값이 모두 0        | `plots=False` 로 실행 | `plots=True` 로 수정                                |

- Critical Error 0건 · 미해결 FAIL 0건
- **최종 판정: ACCEPTED**

## 15. 알려진 한계
- 병해·갈변 검출이 가장 약함 — Validation Recall 0.367, Frozen Test Recall 0.636. 색상 Augmentation 은 원인이 아닌 것으로 확인 → Label(갈변 범위 · 판정 기준) 가설이 남음
- 개선 실험 EXP001 은 Baseline 을 넘지 못함 (`reports/baseline_vs_improved.md`)
- 정상 김치(검출 대상 없음) 이미지가 데이터에 없어 정상 김치에서의 오검출(FP)은 확인하지 못함
- `capture_group`(촬영 묶음) 기준 누수 점검은 미완료 — 약 30초 간격 연속 촬영 이미지가 서로 다른 역할에 섞인 사례 있음
- 모든 실험은 학습 1회 결과 — ±0.01~0.03 차이는 "변화 없음"으로 판단
- Auto Label 검수는 8장(후보 36개) 표본이라 승인률 94% 를 일반화하기 어려움

## 16. 교과 14 Handoff
- 상세는 `docs/교과14-Handoff.md` 참고
- **전달 항목:** Dataset Version (`kimchi_v1`) · Train / Validation / Frozen Test 수량 · Bridge Holdout 100장 (위치 · 교과 8 미사용 확인) · Final Model 가중치 (`final_best.pt`) · Final Model 선택 근거 · Frozen Test 결과 · 대표 FP / FN · Detection · Auto Label 결과 위치 · `reports/acceptance_test.md` (ACCEPTED)
- **다음 교과 연계:** 교과 14 제조 제품검사 프로젝트에서 **Bridge Holdout 100장으로 교과 8 Final Model 을 다시 확인**하는 것부터 이어감 (수행가이드 22.7.1)

## 17. 데이터 보안 주의사항
- 이번 프로젝트 데이터는 **NDA 가 적용되는 교육용 기업 데이터**입니다 (수행가이드 22.2).
- 다음 파일은 GitHub 에 올리지 않습니다 (`.gitignore` 로 제외)

| 제외 대상 | 위치 |
|---|---|
| 원본 이미지 · YOLO 라벨 TXT | `data/` |
| 모델 가중치 (`*.pt`) | `models/` · `runs/` |
| 학습 · 평가 산출물 (예측 박스를 그린 원본 이미지 포함) | `runs/` |
| Detection · Auto Label · 실패 분석 이미지와 라벨 | `demo/` |
| 시연 영상 | `demo/*.mp4` |

- `reports/figures/` 에는 **그래프만** 둡니다 (학습곡선 · Confusion Matrix · PR Curve). `val_batch*.jpg` 처럼 원본 이미지가 들어간 파일은 넣지 않습니다.
- 커밋 전에는 반드시 `git status` 로 추가되는 파일을 확인하고, `git add .` · `git add -A` 대신 파일을 지정해서 추가합니다.
- 데이터 · 가중치는 팀 내부 드라이브로만 전달하며, 공유 범위는 팀원 계정으로 제한합니다 ("링크가 있는 모든 사용자" 공유 금지).
- SSH 키 · 인증 파일은 저장소에 올리지 않습니다.
