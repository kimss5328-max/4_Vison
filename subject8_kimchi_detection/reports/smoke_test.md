# Smoke Test

- 기준: 교과8 수행가이드 16.4~16.8 (Smoke Test · 3일차 Daily Gate)
- 성격: 진행용 보조기록 (16.A) — Smoke Weight는 Baseline으로 사용하지 않음
- 설정: `configs/smoke_dataset.yaml` · 표본 목록 `manifests/smoke_split_manifest.csv`
- 실행 결과 위치: `runs/detect/…` (현재 폴더) · `backup/runs_archive_1013.tar.gz` (10-13 정리 때 압축 보관)
- 지표: 각 실행 `results.csv` 에서 mAP50-95가 가장 높은 epoch 행 (Validation 기준)

## 1. Smoke 표본

| 판 | 만든 시각 | 구성 | Frozen Test · Bridge Holdout 겹침 |
|---|---|---|---|
| 이전 표본 | 2026-10-12 | 50장 · train 35 / val 10 / test 5 | **6장 겹침** (Frozen Test 3 · Bridge Holdout 3 — 파일·픽셀 SHA-256 동일) |
| 현재 표본 (v4) | 2026-10-13 16:22 | 본 분할의 **train 600장에서만** 50장 추출 · 35 / 10 / 5 · seed 42 | 0장 |

- 원인: 이전 표본은 본 분할과 따로 뽑아서 Test · Holdout 이미지가 섞임
- 해결: `tools/build_split.py` v4 — Smoke 표본을 `split_manifest.csv` 의 train 이미지로만 제한 (`build_split_20261013_162244.md`)

## 2. 실행 기록

| # | 시작 | 실행 이름 | 표본 | 클래스 | imgsz | epoch | P | R | mAP50 | mAP50-95 | 목적 · 결과 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10-12 11:49 | `smoke_single` | 이전 | 단일 | 640 | 10 | 0.002 | 0.100 | 0.000 | 0.000 | 학습 → Weight 생성까지 동작 확인 |
| 2 | 10-12 12:25 | `smoke_single_960` | 이전 | 단일 | 960 | 30 | 0.859 | 0.460 | 0.536 | 0.364 | 해상도 탐색 |
| 3 | 10-12 12:26 | `smoke_single_1920` | 이전 | 단일 | 1920 | 30 | 0.488 | 0.500 | 0.517 | 0.403 | 해상도 탐색 |
| 4 | 10-12 12:40 | `smoke_single_4864` | 이전 | 단일 | 4864 | — | — | — | — | — | `results.csv` 없음 — 학습 미완료 (원본 해상도 시도) |
| 5 | 10-12 12:43 | `smoke_single_2560` | 이전 | 단일 | 2560 | 30 | 0.533 | 0.251 | 0.250 | 0.143 | 해상도 탐색 |
| 6 | 10-12 14:26 | `smoke_single_960_e90` | 이전 | 단일 | 960 | 90 | 0.834 | 0.680 | 0.804 | 0.553 | 해상도 비교 (90 epoch) |
| 7 | 10-12 14:27 | `smoke_single_1920_e90` | 이전 | 단일 | 1920 | 90 | 0.862 | 0.880 | 0.886 | **0.677** | 해상도 비교 (90 epoch) |
| 8 | 10-12 14:31 | `smoke_single_2432_e90` | 이전 | 단일 | 2432 | 90 | 0.861 | 0.780 | 0.863 | 0.574 | 해상도 비교 (90 epoch) |
| 9 | 10-12 14:41 | `smoke_single_1088_e90` | 이전 | 단일 | 1088 | 90 | 0.852 | 0.820 | 0.833 | 0.592 | 해상도 비교 (90 epoch) |
| 10 | 10-12 14:44 | `smoke_single_1440_e90` | 이전 | 단일 | 1440 | 90 | 0.821 | 0.780 | 0.809 | 0.615 | 해상도 비교 (90 epoch) |
| 11 | 10-12 14:56 | `smoke_single_1440_e150` | 이전 | 단일 | 1440 | 150 | 0.816 | 0.800 | 0.838 | 0.591 | epoch 늘림 확인 (90 → 150, 개선 없음) |
| 12 | 10-13 16:28 | `smoke_multi` | **v4** | 7클래스 | 640 | 3 | 0.302 | 0.040 | 0.019 | 0.016 | **3일차 Gate용 Smoke** — 학습 → Weight → Prediction |
| 13 | 10-14 09:49 | `smoke_multi` (재실행) | **v4** | 7클래스 | 640 | 3 | 0.302 | 0.040 | 0.019 | 0.016 | 같은 조건 재실행 — 결과 동일 |

- 위치: 1 · 13 `runs/detect/runs/` · 12 `runs/detect/smoke_multi` · 2~11 압축 보관
- Prediction: `runs/detect/smoke_multi_pred/` · `runs/detect/runs/smoke_multi_pred/` · Validation 재확인 `runs/detect/smoke_multi_val/`

## 3. 해상도 결정 (Baseline imgsz 1920의 근거)

| 근거 | 640 | 960 | 1088 | 1440 | 1920 | 2432 |
|---|---|---|---|---|---|---|
| Smoke 90 epoch (#6~#10) mAP50-95 | — | 0.553 | 0.592 | 0.615 | **0.677** | 0.574 |
| 전체 데이터 단일 클래스 100 epoch (val 100장) mAP50-95 | 0.684 | — | — | — | **0.832** | — |
| 7클래스 (val 100장) mAP50-95 | 0.601 (30 epoch) | — | — | — | **0.781** (100 epoch · Baseline) | — |

- 원본 4848×2704 를 640 으로 줄이면 약 1/7.6 — 작은 이물의 경계가 흐려짐. 1920 은 약 2/5
- 2432 이상은 오히려 낮아짐 (#5 · #8) · 원본 해상도(#4)는 학습 미완료
- 전체 데이터 비교 실행: `full_single_640` · `full_single_1920` (10-12, 압축 보관) · `full_single_{640,1920}_e30` · `full_multi_640_e30` (`runs/detect/runs/`)

**한계**: #2~#11 은 이전 표본(Frozen Test 3장 · Bridge Holdout 3장 포함)으로 실행함. 해상도 선택에 Test 이미지 일부가 관여했을 수 있음. 다만 전체 데이터 비교(train 600 / val 100, Test · Holdout 미사용)도 같은 결론(1920)이라 Baseline 조건 결정은 유지함.

## 4. 3일차 Daily Gate — Smoke 항목 (16.8)

| 항목 | 판정 | 근거 |
|---|---|---|
| Frozen Test와 Bridge Holdout을 Smoke Test에 사용하지 않았습니다 | 부분 | Gate용 Smoke(#12 · #13)는 v4 표본으로 0장. 해상도 탐색(#2~#11)은 이전 표본으로 6장 포함 — 3절 한계에 기록 |
| 1~3 Epoch 학습이 완료됩니다 | 완료 | #12 · #13 (3 epoch) |
| Smoke Weight가 생성됩니다 | 완료 | `runs/detect/smoke_multi/weights/best.pt` |
| 이미지 Prediction이 실행됩니다 | 완료 | `runs/detect/smoke_multi_pred/` |
| BBox · Class · Confidence가 표시됩니다 | 완료 | 예측 이미지 확인 (아래 5절) |
| Smoke Weight를 Baseline으로 사용하지 않습니다 | 완료 | Baseline은 `runs/baseline_v1` 에서 별도 학습 |
| 오류와 해결방법을 기록했습니다 | 완료 | 6절 |

## 5. Prediction 관찰 (#12 Smoke Weight)

- BBox · Class 이름 · Confidence 가 이미지에 표시됨
- 3 epoch 학습이라 박스가 화면 전체를 크게 잡는 경우가 많음
- 나뭇가지를 벌레로 잘못 잡은 박스가 Confidence 0.93 으로 나온 경우가 있음 → Smoke 단계에서는 정확도를 판단하지 않음 (16.7)

## 6. 오류와 해결

| 오류 | 원인 | 해결 |
|---|---|---|
| `yolo` · `python` 명령을 찾을 수 없음 | 가상환경 미활성화 | `source venv/bin/activate` |
| 결과가 `runs/detect/runs/<이름>` 에 겹쳐 저장됨 | `project=runs` (상대경로)를 Ultralytics가 `runs/detect/` 아래에 붙임 | Baseline Script는 `project` 를 절대경로로 지정 → `runs/<이름>` 에 저장 확인 |
| Smoke 표본 6장이 Frozen Test · Holdout 과 겹침 | 표본을 본 분할과 따로 뽑음 | `build_split.py` v4 — train 에서만 추출, 겹침 0장 확인 |
| 원본 해상도(4864) 학습 결과 없음 | 학습 미완료 (원인 기록 없음) | 이후 비교에서 제외 |
| 학습 로그가 남지 않음 | 화면 출력만 함 | Baseline부터 `python -u … 2>&1 \| tee runs/<이름>.log` (9.4) |
