# Improvement Experiment — EXP001 (색상 Augmentation 끄기)

- 기준: 교과8 수행가이드 20.3 (학습 전에 무엇을 왜 바꾸는지 기록)
- 출발 문서: `reports/failure_hypothesis.md` (v3) 5·6절
- 작성 시점: 변경 변수와 유지 조건은 학습 전에 `failure_hypothesis.md` v3에서 확정했고, 이 문서는 그 내용을 20.3 형식으로 정리한 것입니다 (2026-10-16)

---

## 1. 입력 — 3일차 Dataset Version

| 항목 | 값 |
|---|---|
| Dataset Version | `kimchi_v1` |
| Label 해시 | train `57f0bf5121e4` · val `ab6cc7f98da7` |
| Split Freeze | 2026-10-13 11:11:07 · commit `1b074fa` |
| 역할 | Train 600 · Validation 100 · Frozen Test 100 · Bridge Holdout 100 |
| 비교에 쓰는 Split | Validation 100장 · 501 instances (Frozen Test · Holdout 사용 안 함) |

---

## 2. 입력 — 6일차 `failure_hypothesis.md`

| 항목 | 내용 |
|---|---|
| 주 실패 | 병해·갈변(Class 5) 단독 저조 — val 16장 · 31개, P 0.739 · **R 0.367** · mAP50 0.427 |
| 주 가설 | Model / Training — 기본 색상 Augmentation이 갈변 색을 흔들어, 색으로 구분되는 Class 5 학습을 방해 |
| 제외한 가설 | Label(재라벨링 작업 부담으로 이번 실험 제외, 남은 가설로 유지) · Data(Class 5 train 98장 > Class 6 33장) · Inference(Threshold로 놓친 객체 회복 어려움) |

---

## 3. 변경 변수 1개

| 항목 | Baseline (`baseline_v1`) | EXP001 |
|---|---|---|
| `hsv_h` | 0.015 | **0** |
| `hsv_s` | 0.7 | **0** |
| `hsv_v` | 0.4 | **0** |

- 세 값은 "색상 변형"이라는 **하나의 변수**로 묶어 바꿉니다 (20.2).
- 조금씩 줄이지 않고 끄는 이유: 켬 vs 끔으로 결과 해석을 분명하게 하기 위해서입니다.
- 라벨을 바꾸지 않으므로 Dataset Version은 `kimchi_v1` 그대로이며, 20.5 Baseline 재평가는 필요 없습니다.

---

## 4. 유지할 조건

| 조건 | 값 |
|---|---|
| 시작 Weight | `yolo11n.pt` (sha256 `0ebbc80d4a76`) — Baseline과 동일 |
| 학습 조건 | imgsz 1920 · 100 epoch · batch 3 · patience 30 · cache ram · seed 0 · deterministic |
| 다른 Augmentation | mosaic · fliplr 등 hsv 외 값은 Baseline `args.yaml` 그대로 |
| Split · 라벨 | Split Freeze 유지 · 라벨 변경 없음 |
| 환경 | Ultralytics 8.4.175 · torch 2.14.1+cu130 · Python 3.10.12 |

---

## 5. 확인할 Validation 지표와 실패 패턴

**지표**

| 구분 | 지표 | Baseline 기준값 |
|---|---|---|
| 주 | Class 5 Recall · mAP50 | 0.367 · 0.427 |
| 보조 | 전체 P · R · mAP50 · mAP50-95 | 0.926 · 0.849 · 0.889 · 0.780 |
| 보조 | 다른 Class가 떨어지지 않는지 | `reports/baseline_metrics.csv` |

**실패 패턴 (Confusion Matrix, 행 = 예측 · 열 = 정답)**

| 패턴 | Baseline |
|---|---|
| 병해·갈변 정답 검출 | 18 / 31 |
| 병해·갈변 FN (정답 → background) | 10 / 31 |
| 병해·갈변 FP (background → 병해·갈변) | 762 |
| 나뭇가지 → 나뭇잎 | 10 |
| 나뭇잎 → 나뭇가지 | 9 |
| 고무장갑 → 플라스틱 | 11 |

**판정 기준**
- 학습 1회 결과이므로 ±0.03 이내 차이는 "변화 없음"으로 봅니다.
- 좋아지지 않아도 `experiment_log.csv`에 남깁니다 (20.4). 그 경우 Label 가설의 가능성이 커진 것으로 기록합니다.

---

## 6. 실행과 Weight 보관

| 항목 | 값 |
|---|---|
| 실행 이름 | `exp001` |
| 학습 PC | 2 PC (`DESKTOP-007V3ON`) — 1 PC와 같은 버전으로 설치 확인 |
| Weight | `runs/exp001/weights/best.pt` → `models/improved/exp001_best.pt` |

---

## 7. 결과 기록 위치

| 파일 | 내용 |
|---|---|
| `reports/experiment_log.csv` | 실제 조건 · Validation 결과 · 결정 |
| `reports/figures/exp001_results.png` | 학습곡선 |
| `reports/figures/exp001_confusion_matrix.png` | Confusion Matrix |
| `reports/baseline_vs_improved.md` | Baseline과 같은 Validation 비교 |

- 결과 요약: Class 5 Recall 0.367 → 0.355로 개선되지 않아 **가설은 지지되지 않았고, Final 후보에서 제외**했습니다. 상세 내용은 `baseline_vs_improved.md`에 있습니다.
