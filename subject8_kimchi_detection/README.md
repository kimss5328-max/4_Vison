# 교과8 — Vision 기반 조각김치 이물검출 모듈 (YOLO11)

> 기준 문서: 교과 8 Vision 객체검출 프로젝트 수행가이드 (`subject8_kimchi_detection/`)

---

## 1. 프로젝트 개요

교과 7에서 검수·확정한 조각김치 정답 라벨 데이터(JPG 900장 + YOLO TXT 900개)를 입력받아 YOLO11n Baseline 모델을 학습하고, Validation에서 실제 검출 성능 및 FP·FN 실패 원인을 분석·개선하는 객체검출 프로젝트입니다.

* **모델:** Ultralytics YOLO11n (`yolo11n.pt` 사전학습 가중치)
* **클래스 (7개):**
  * 0: 나뭇잎·종이류
  * 1: 플라스틱·비닐·금속류
  * 2: 나뭇가지류
  * 3: 벌레류
  * 4: 고무장갑 (Class 4 재사용)
  * 5: 병해·갈변
  * 6: 돌·골초
* **Dataset Version:** `kimchi_v1` (train `57f0bf5121e4` / val `ab6cc7f98da7`)
* **Split Freeze:** `manifests/split_manifest.csv` @ `1b074fa`

---

## 2. 디렉토리 구조 (가이드 7. 권장 개발 디렉토리 준수)

```text
subject8_kimchi_detection/
├── README.md                          # 본 문서
├── requirements.txt                   # 필수 패키지 목록
│
├── configs/
│   ├── dataset.yaml                   # YOLO 학습 데이터 설정 (train/val/test)
│   ├── smoke_dataset.yaml             # Smoke Test 설정 (표본 50장)
│   └── classes.yaml                   # 클래스 명칭 및 메타데이터
│
├── manifests/
│   ├── split_manifest.csv             # 4개 역할 전체 분할 대장 (Split Freeze)
│   ├── train.csv                      # 학습 데이터 (600장)
│   ├── val.csv                        # 검증 데이터 (100장)
│   ├── test.csv                       # Frozen Test (100장)
│   ├── bridge_holdout.csv             # 교과 14 보존용 (100장)
│   └── dataset_manifest.csv           # 교과 7 입력 메타데이터
│
├── src/                               # 재사용 핵심 모듈
│   ├── __init__.py
│   ├── dataset_audit.py               # 데이터 정합성 감사 모듈
│   ├── train_detector.py              # YOLO11 학습 인터페이스 함수 (17.2)
│   ├── common/                        # 공통 유틸리티 (paths, manifest, split)
│   └── detector/                      # 학습 및 평가 전담 모듈 (trainer, evaluator)
│
├── scripts/ (또는 tools/)             # 순서별 실행 스크립트 (가이드 1966행 대응)
│   ├── 01_build_split.py              # 데이터 분할 실행 및 Split Freeze 검증
│   ├── 02_merge_manifest.py           # 데이터 대장 통합
│   ├── 03_export_final.py             # 교과 7 FINAL 승인 데이터 수집
│   ├── 04_migrate_result.py           # 결과 마이그레이션
│   ├── 05_train.py                    # Baseline 학습 래퍼
│   ├── 06_train_baseline.py           # Baseline 정규 학습 스크립트 (17.3)
│   └── 06_evaluate.py                 # Validation 평가 및 지표 리포트 생성
│
├── models/
│   └── baseline/                      # baseline_best.pt 보관용
│
├── runs/
│   └── baseline_v1/                   # Baseline 학습 산출물 (results.csv, weights 등)
│
├── reports/                           # 산출물 보고서
│   ├── dataset_summary.csv            # 데이터 감사 요약
│   ├── baseline_metrics.csv           # Baseline 모델 성능 지표 (all 및 클래스별)
│   ├── baseline_training_condition.md # Baseline 학습 조건 및 환경 기록
│   ├── smoke_test.md                  # Smoke Test 결과 및 해상도 선정 기록
│   └── failure_candidates.csv         # 실패분석 대상 후보 (19장)
│
├── docs/
│   └── split_policy.md                # 층화 분할 정책 및 Freeze 사유 문서
│
└── data/                              # 학습용 데이터셋 (NDA 준수, Git 제외)
    ├── yolo/                          # YOLO images/labels (train, val, test)
    ├── bridge_holdout/                # 교과 14 보존 데이터
    ├── smoke/                         # Smoke Test 표본 (50장)
    └── final/                         # 교과 7 수령 완료 원본 데이터
```

---

## 3. 환경 및 실행 방법

### 3-1. 환경
* **OS:** Linux / WSL (Ubuntu 22.04 권장)
* **GPU:** NVIDIA RTX 3060 12GB (또는 동급 이상)
* **Python / PyTorch:** Python 3.10.12 / PyTorch 2.14.1+cu130
* **Ultralytics:** 8.4.175

### 3-2. 패키지 설치
```bash
cd subject8_kimchi_detection
pip install -r requirements.txt
```

### 3-3. 순서별 실행 명령어

1. **데이터 정합성 및 무결성 검사 (02_audit)**
   ```bash
   python src/dataset_audit.py
   # 산출물: reports/dataset_summary.csv
   ```

2. **Split Freeze 검증 (03_build_split)**
   ```bash
   python scripts/01_build_split.py --freeze-only
   # 4개 파일(split_manifest, train, val, test) 모두 PASS 확인
   ```

3. **Smoke Test 실행 (05_smoke_train)**
   ```bash
   python scripts/01_build_split.py --limit 50 --apply
   # configs/smoke_dataset.yaml 생성 및 50장 사전 확인
   ```

4. **Baseline 모델 학습 실행 (06_train_baseline)**
   ```bash
   # 시험 실행 (1 epoch 테스트)
   python -u scripts/06_train_baseline.py --epochs 1 --name baseline_dryrun

   # 정규 Baseline 학습 (100 epochs, imgsz 1920, batch 3, seed 0)
   python -u scripts/06_train_baseline.py 2>&1 | tee runs/baseline_v1.log
   ```

5. **Validation 성능 지표 평가 (07_evaluate_baseline)**
   ```bash
   python scripts/06_evaluate.py
   # 산출물: reports/baseline_metrics.csv
   ```

---

## 4. 확정 Baseline 성능 지표 (val 100장 · 501개 박스)

| 구분 | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| **전체 (all)** | **0.926** | **0.849** | **0.889** | **0.780** |
| 0: 나뭇잎·종이류 | 0.941 | 0.920 | 0.963 | 0.865 |
| 1: 플라스틱·비닐·금속류 | 0.947 | 0.882 | 0.932 | 0.821 |
| 2: 나뭇가지류 | 0.952 | 0.897 | 0.948 | 0.835 |
| 3: 벌레류 | 0.968 | 0.890 | 0.952 | 0.841 |
| 4: 고무장갑 | 0.960 | 0.952 | 0.978 | 0.892 |
| **5: 병해·갈변 (최약점)** | **0.739** | **0.367** | **0.427** | **0.338** |
| 6: 돌·골초 | 0.975 | 0.934 | 0.980 | 0.869 |

* **약점 분석:** Class 5(병해·갈변)의 Recall(0.367)이 현저히 낮아 6일차 Failure Analysis 집중 분석 대상입니다.

---

## 5. 보안 및 NDA 주의사항

* 기업 제공 원본 이미지(`.jpg`, `.png`), 레이블 텍스트(`.txt`), 학습된 가중치(`.pt`), 시각화 예측 이미지는 Git 커밋 대상에서 엄격히 제외됩니다(`.gitignore`).
* 모든 보고서 문서에는 파일명, 지표 수치, 통계 데이터만 기재합니다.
