# Baseline Training Condition

- 기준: 교과8 수행가이드 17.1 (반드시 기록할 항목) · 17.3 (실행 Script) · 17.5 (Weight 보관)
- 실행 이름: `baseline_v1`
- 학습 Script: `tools/06_train_baseline.py` → `src/train_detector.py` 의 `train_detector()` 호출 (17.2 · 17.3)
- 결과 위치: `runs/baseline_v1/`
- 보관 Weight: `runs/baseline_v1/weights/baseline_best.pt` (원본 `runs/baseline_v1/weights/best.pt` · sha256 앞 12자리 `c90f9767442e`)
  - 가이드 경로 `models/baseline/baseline_best.pt`(17.5) 대신 사용 — 프로젝트 최상위에 새 폴더(`models/`)를 만들지 않는 팀 규칙에 따름
- 보관 results: `runs/baseline_v1/results.csv` (100행 = epoch 1~100)
- 보관 학습 설정: `runs/baseline_v1/args.yaml`
- 학습 로그: `runs/baseline_v1.log` (9.4)

## 1. 학습 조건 (17.1)

| 항목 | 값 | 근거 위치 |
|---|---|---|
| Model | YOLO11n (`yolo11n.pt` 사전학습에서 시작) | `args.yaml` → `model` |
| Dataset Version | kimchi_v1 (labels sha256 앞 12자리 — train: `57f0bf5121e4` / val: `ab6cc7f98da7`) | `data/yolo/labels/{train,val}/*.txt` 해시 (학습 직전 재확인) |
| Train / Val Manifest Version | `manifests/split_manifest.csv` @ commit `1b074fa` (2026-10-13 08:40) · train.csv sha256 `8b9e6b7c4644` · val.csv sha256 `eabbaa9b8f3a` | `git log` · `sha256sum` |
| Epoch | 100 (patience 30, 조기 종료 없이 100 epoch 완료) | `args.yaml` → `epochs` · `patience` / `results.csv` 100행 |
| Batch | 3 (Script에 고정 — 이전 CLI 학습에서 AutoBatch(-1)가 결정한 값) | `args.yaml` → `batch` |
| Image Size | 1920 | `args.yaml` → `imgsz` |
| Seed | 학습 seed 0 (Ultralytics 기본값) · 분할 seed 42 | `args.yaml` → `seed` / `tools/build_split.py --seed` |
| Optimizer | auto → AdamW (momentum 0.9) | `runs/baseline_v1.log` → `optimizer: AdamW(lr=0.000909, momentum=0.9)` |
| Learning Rate | auto → 0.000909 (= 0.002 × 5 ÷ (4 + 7)) · warmup 3 epoch · lrf 0.01 | 학습 로그 / `results.csv` → `lr/pg0` (1 epoch 0.000301 · 최고 0.000890 · 마지막 0.000018) |
| GPU | NVIDIA RTX 3060 12GB | 환경 확인 (14.3) |
| Ultralytics Version | 8.4.175 (PyTorch 2.14.1+cu130 · Python 3.10.12) | 환경 확인 (14.3) |
| 학습 시작·종료 시간 | 시작 2026-10-14 15:57:50 / 종료 2026-10-14 16:50:05 (약 52분) | `stat` (`args.yaml` 생성 · `weights/last.pt` 수정 시각) |

## 2. 그 밖의 조건

| 항목 | 값 |
|---|---|
| 클래스 | 7클래스 (`single_cls=False`) · Class ID 0~6 · Class 4 고무장갑 포함 |
| 데이터 설정 | `configs/dataset.yaml` — train 600 / val 100 (test 100 미사용 · Bridge Holdout 미포함) |
| cache | ram |
| deterministic | true (Ultralytics 기본값) |
| 학습 명령 | `python -u tools/06_train_baseline.py 2>&1 \| tee runs/baseline_v1.log` (프로젝트 루트에서 실행, 9.0) |

## 3. Baseline 조건 확정 근거

- Smoke 해상도 비교(`reports/smoke_test.md` 실행 #6~#10, 90 epoch): 960 · 1088 · 1440 · 1920 · 2432 중 1920 의 mAP50-95 가 가장 높음 (0.677)
- 전체 데이터 단일 클래스 100 epoch 비교(val 100장): 640 → 0.684 · 1920 → 0.832
- 원본 4848×2704 를 640 으로 줄이면(약 1/7.6) 작은 이물의 경계가 흐려짐 → 1920(약 2/5) 채택
- 참고 실행: 7클래스 640 · 30 epoch (`runs/detect/runs/full_multi_640_e30/`) — P 0.840 · R 0.786 · mAP50 0.828 · mAP50-95 0.601
- 한계: Smoke 해상도 비교는 이전 Smoke 표본(Frozen Test 3장 · Bridge Holdout 3장 포함)으로 실행함. 전체 데이터 비교(Test · Holdout 미사용)도 같은 결론이라 1920 결정은 유지 (`reports/smoke_test.md` 3절)

## 4. Validation 결과 (best epoch 90 · val 100장 · 박스 501개)

| 클래스 | 이미지 | 박스 | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| 전체 | 100 | 501 | 0.926 | 0.849 | 0.889 | 0.780 |
| 0 나뭇잎·종이류 | 32 | 84 | 0.916 | 0.909 | 0.962 | 0.879 |
| 1 플라스틱·돌·금속류 | 57 | 179 | 0.975 | 0.911 | 0.953 | 0.829 |
| 2 나뭇가지류 | 41 | 97 | 0.889 | 0.897 | 0.949 | 0.850 |
| 3 벌레류 | 22 | 46 | 1.000 | 0.956 | 0.972 | 0.819 |
| 4 고무장갑 | 16 | 34 | 0.966 | 0.971 | 0.989 | 0.918 |
| 5 병해·갈변 | 16 | 31 | 0.739 | 0.367 | 0.427 | 0.338 |
| 6 파·고추 | 6 | 30 | 1.000 | 0.933 | 0.972 | 0.830 |

- 상세 지표 파일: `reports/baseline_metrics.csv` (18.4, 5일차 작성)

## 5. 비고

- `optimizer=auto` 이므로 `args.yaml` 의 `lr0=0.01` 은 사용되지 않음
- 재현 확인: 처음 Baseline은 CLI 명령(`yolo detect train ... batch=-1 seed=0`, 실행 이름 `full_multi_1920_e100`, 2026-10-13)으로 학습함. 17.2·17.3 Script를 만든 뒤 같은 조건(seed 0 · batch 3)으로 다시 학습한 결과
  - `results.csv` 100행 — 시간 열을 뺀 모든 값 동일
  - Weight 텐서 499개 — 값 모두 동일
  - Validation 지표 — 위 표와 동일
  - Weight 파일 해시만 다름 (`18c5b4cc12d3` → `c90f9767442e`) — 파일 안에 저장 날짜가 들어 있기 때문
  - 따라서 4·5일차 산출물(`baseline_metrics.csv`, `failure_candidates.csv`, 그래프)의 수치는 그대로 유효함. 이전 실행 폴더 `runs/detect/runs/full_multi_1920_e100/` 는 참고용으로 보관
- 학습 데이터 900장 중 171장은 교과7 결과 폴더 final 단계에 없는 이미지 — Class 4 포함 152장 · REVIEW/QA 대기 19장(`other` 13 · `class_ambiguous` 6). 팀 회의 결정(900장 전체 사용)에 따름 · 근거 `src/dataset_audit.py` 결과 · 사유는 `docs/split_policy.md` 에 기록
- Frozen Test · Bridge Holdout 은 학습·평가에 사용하지 않음 (11.4, 17.6)
- 7일차 개선 실험(20.2)은 `tools/06_train_baseline.py` 의 `BASELINE` 조건에서 한 항목만 바꿔 실행
