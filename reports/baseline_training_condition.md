# Baseline Training Condition

- 기준: 교과8 수행가이드 17.1 (반드시 기록할 항목) · 17.5 (Weight 보관)
- 실행 이름: `full_multi_1920_e100` (가이드 이름 `baseline_v1` 에 해당)
- 결과 위치: `runs/detect/runs/full_multi_1920_e100/`
- 보관 Weight: `runs/baseline_v1/weights/baseline_best.pt` (원본: `runs/detect/runs/full_multi_1920_e100/weights/best.pt`)
  - 가이드 경로 `models/baseline/baseline_best.pt`(17.5) 대신 사용 — 프로젝트 최상위에 새 폴더(`models/`)를 만들지 않는 팀 규칙에 따름
- 보관 results: `runs/baseline_v1/results.csv` (원본: `runs/detect/runs/full_multi_1920_e100/results.csv`, 100행 = epoch 1~100)
- 보관 학습 설정: `runs/baseline_v1/args.yaml`

## 1. 학습 조건 (17.1)

| 항목 | 값 | 근거 위치 |
|---|---|---|
| Model | YOLO11n (`yolo11n.pt` 사전학습에서 시작) | `args.yaml` → `model` |
| Dataset Version | kimchi_v1 (labels sha256 앞 12자리 — train: `57f0bf5121e4` / val: `ab6cc7f98da7`) | `data/yolo/labels/{train,val}/*.txt` 해시 |
| Train / Val Manifest Version | `manifests/split_manifest.csv` @ commit `1b074fa` (2026-10-13 08:40) · train.csv sha256 `8b9e6b7c4644` · val.csv sha256 `eabbaa9b8f3a` | `git log` · `sha256sum` |
| Epoch | 100 (patience 30, 조기 종료 없이 100 epoch 완료) | `args.yaml` → `epochs` · `patience` / `results.csv` 100행 |
| Batch | -1 (AutoBatch 자동 결정 · 실제 값은 학습 로그 미보존) | `args.yaml` → `batch` |
| Image Size | 1920 | `args.yaml` → `imgsz` |
| Seed | 학습 seed 0 (Ultralytics 기본값 · 교과8 모든 학습 동일) · 분할 seed 42 | `args.yaml` → `seed` / `tools/build_split.py --seed` |
| Optimizer | auto (→ AdamW) | `args.yaml` → `optimizer` · 자동 선택 규칙 |
| Learning Rate | auto (→ 0.000909 = 0.002 × 5 ÷ (4 + 7)) · warmup 3 epoch · lrf 0.01 | `results.csv` → `lr/pg0` (1 epoch 0.000301 · 최고 0.000890 · 마지막 0.000018) |
| GPU | NVIDIA RTX 3060 12GB | 환경 확인 (14.3) |
| Ultralytics Version | 8.4.175 (PyTorch 2.14.1+cu130 · Python 3.10.12) | 환경 확인 (14.3) |
| 학습 시작·종료 시간 | 시작 2026-10-13 11:14:14 / 종료 2026-10-13 12:07:32 (약 53분 · 학습 3,150초 + 검증·그래프 저장) | `stat` (`args.yaml` 생성 · `weights/last.pt` 수정 시각) / `results.csv` 마지막 `time` |

## 2. 그 밖의 조건

| 항목 | 값 |
|---|---|
| 클래스 | 7클래스 (`single_cls=False`) · Class ID 0~6 · Class 4 고무장갑 포함 |
| 데이터 설정 | `configs/dataset.yaml` — train 600 / val 100 (test 100 미사용 · Bridge Holdout 미포함) |
| cache | ram |
| 학습 명령 | `yolo detect train model=yolo11n.pt data=configs/dataset.yaml imgsz=1920 epochs=100 patience=30 batch=-1 cache=ram seed=0 project=runs name=full_multi_1920_e100` |

## 3. Baseline 조건 확정 근거

- Smoke Test(`reports/smoke_test.md` 실행 1~11)에서 해상도 960 · 1088 · 1440 · 1920 · 2432 를 같은 조건으로 비교 → 1920 이 박스 위치 정확도(mAP50-95)와 놓침 수에서 가장 좋음
- 원본 4848×2704 를 640 으로 줄이면(약 1/7.6) 작은 이물의 경계가 흐려짐 → 1920(약 2/5) 채택
- 참고 실행: 7클래스 640 · 30 epoch (`runs/detect/runs/full_multi_640_e30/`) — P 0.840 · R 0.786 · mAP50 0.828 · mAP50-95 0.601

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
- AdamW 는 학습 로그 미보존으로 `results.csv` 학습률 값과 자동 선택 규칙으로 판정
- 학습 데이터 900장 중 169장은 검수자 최종 승인(final 단계) 전 이미지 — 팀 회의 결정(900장 전체 사용)에 따름, 사유는 `docs/split_policy.md` 에 기록
- Frozen Test · Bridge Holdout 은 학습·평가에 사용하지 않음 (11.4, 17.6)
- 다음 학습부터 로그 보존: 명령 끝에 `2>&1 | tee runs/<이름>.log` (9.4)
