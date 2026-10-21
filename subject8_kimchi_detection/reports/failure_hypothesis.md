# Failure Analysis Hypothesis

> 상태: 초안 v3 (2026-10-16) — 재라벨링 제외, 학습 조건 변경으로 전환
> - 7일차 변경 변수는 A(총괄) 승인 후 확정 (role_plan_6_9 6일차 순서 4)
> - `reports/failure_analysis.csv`는 수정하지 않고, Class 5 해석은 이 문서 3절에만 기록

---

## 1. 분석 대상

| 항목 | 값 |
|---|---|
| 모델 | `baseline_v1` — `runs/baseline_v1/weights/baseline_best.pt` (seed 0 · batch 3 · imgsz 1920 · 100 epoch) |
| Dataset Version | `kimchi_v1` |
| 데이터 범위 | Validation 100장 · 501 instances (`manifests/val.csv`) |
| 예측 이미지 | `runs/detect/runs/predict/baseline_val_images/` |
| 사용하지 않은 데이터 | Train · Frozen Test · Bridge Holdout (19.2) |

- 예측 이미지는 이전 CLI Weight로 생성했습니다. Script 재학습 Weight와 Validation 지표(P .926 · R .849 · mAP50 .889 · mAP50-95 .780)와 `results.csv` 100행이 완전히 같아 분석 결과는 그대로 유효합니다.

---

## 2. 가장 중요한 반복 실패

**병해·갈변(Class 5)을 놓침 (FN)**

| Class | 이름 | val 이미지 | instances | Precision | Recall | mAP50 |
|---|---|---|---|---|---|---|
| 5 | 병해·갈변 | 16 | 31 | 0.739 | **0.367** | **0.427** |
| 나머지 6개 Class | — | — | — | 0.889~1.000 | 0.897~0.971 | 0.949~0.989 |

- 다른 Class는 모두 Recall 0.89 이상인데 병해·갈변만 0.367입니다. 31개 중 약 20개를 놓쳤습니다.
- Precision .739는 상대적으로 유지됩니다. 모델이 병해·갈변을 **잘못 찾기보다는 거의 찾지 않는** 쪽으로 실패합니다.

---

## 3. 근거

| 파일 | 내용 |
|---|---|
| `reports/baseline_metrics.csv` 8행 | Class 5 P .739 · R .367 · mAP50 .427 · mAP50-95 .338 |
| `manifests/train.csv` | train 600장 중 Class 5 포함 98장 (pool 80 · excluded 14 · review 4) |
| `reports/failure_candidates.csv` | 5일차 후보 19장 중 16장이 Class 5 포함 (GT Class 5 박스 31개 = val 전체 Class 5) |
| `reports/failure_analysis.csv` | 대표 실패 29건 (아래 Class 5 관련 줄 참고) |
| `demo/failure_analysis/` | `failure_analysis.csv`와 1:1 대응 이미지 29장 |

**Class 5 FN 대표 사례**

| 이미지 | csv 줄 | 내용 |
|---|---|---|
| `demo/failure_analysis/250424_150751737200.jpg` | 21 | GT Class 5 2개 미검출 (csv 기록 "미인식 객체 2개 존재") |

**Class 5 FP 사례 (GT에 Class 5 없음)**

| 이미지 | csv 줄 | 내용 |
|---|---|---|
| `demo/failure_analysis/250410_171711703137.jpg` | 3 | Class 2를 Class 5로 예측 |
| `demo/failure_analysis/250424_112553658191.jpg` | 16 | Class 5 오검출 |
| `demo/failure_analysis/250424_141451512347.jpg` | 20 | Class 5 오검출 |

- 모델이 병해·갈변을 **놓치기도 하고(FN), 다른 위치에 붙이기도(FP)** 합니다. Class 5의 특징(색)을 안정적으로 학습하지 못했다는 4절 가설과 맞습니다.
- `failure_analysis.csv`는 수정하지 않았습니다. 위 Class 5 해석은 GT Class 5 포함 이미지 16장(`failure_candidates.csv`)과 csv를 대조해 이 문서에만 기록합니다.
- `250424_142806480763`(REVIEW·QA 대기, class_ambiguous)은 대표 사례에 포함하지 않았습니다.

---

## 4. 원인 가설 (19.3 네 범주)

| 범주 | 판단 | 근거 |
|---|---|---|
| **Model / Training 문제** | **주 가설 (이번 실험 대상)** | 병해·갈변은 다른 Class와 달리 **모양보다 색으로 구분**됩니다. Ultralytics 기본 색상 Augmentation(`hsv_h` 0.015 · `hsv_s` 0.7 · `hsv_v` 0.4)이 학습 중 색을 크게 흔들어, 갈변 색이 정상 김치 색과 구분되지 않게 학습되었을 가능성이 있습니다. 모양으로 구분되는 다른 Class는 영향이 작아 Class 5만 단독으로 낮은 현상과 맞습니다. |
| Label 문제 | 남은 가설 (이번에는 확인하지 않음) | 병해·갈변은 경계가 뚜렷하지 않아 BBox 범위와 판정 기준이 이미지마다 다를 가능성 — 교과7 검수에서 라벨 기준 문제로 판단. 재라벨링은 작업 부담이 커 이번 실험에서 제외합니다. |
| Data 문제 | 낮음 | Class 5 train 이미지 98장으로, 33장뿐인 Class 6(R .933)보다 많음 → 수량 부족으로 설명되지 않음 |
| Inference 문제 | 낮음 | Precision이 유지되고 Recall만 낮음 → Threshold 조정으로는 놓친 객체를 되찾기 어려움 |

- imgsz는 이미 1920이고 작은 박스 표본도 7개뿐이라, 입력 크기는 이번 변수 후보에서 제외합니다.

---

## 5. 7일차 변경 변수

**색상 Augmentation 끄기 (EXP001)**

| 항목 | Baseline | EXP001 |
|---|---|---|
| `hsv_h` | `[확인 필요: args.yaml]` (기본 0.015) | 0 |
| `hsv_s` | `[확인 필요: args.yaml]` (기본 0.7) | 0 |
| `hsv_v` | `[확인 필요: args.yaml]` (기본 0.4) | 0 |

- 세 값은 모두 "색상 변형"이라는 **하나의 변수**로 묶어 바꿉니다. 값을 조금씩 줄이는 대신 끄는 이유는 결과 해석을 분명하게 하기 위해서입니다 (켬 vs 끔).
- 라벨은 바꾸지 않으므로 Dataset Version은 `kimchi_v1` 그대로이고, 20.5 Baseline 재평가는 필요 없습니다.
- 확인할 지표: Class 5 Recall · mAP50 (주), 다른 Class 지표가 떨어지지 않는지 (보조)
- 결과가 좋아지지 않아도 `experiment_log.csv`에 남깁니다 (20.4). 그 경우 Label 가설 쪽 가능성이 더 커졌다고 기록합니다.

---

## 6. 유지 조건

| 조건 | 값 |
|---|---|
| Split 배정 | Train 600 · Validation 100 · Test 100 · Holdout 100 그대로 (Split Freeze, 11.5) |
| 학습 조건 | 같은 모델 · imgsz 1920 · 100 epoch · batch 3 · seed 0 · Baseline과 같은 시작 가중치 |
| 다른 Augmentation | mosaic · fliplr 등 hsv 외 값은 Baseline `args.yaml` 그대로 |
| 라벨 | 변경 없음 |
| Dataset Version | `kimchi_v1` 동일 |

---

## 7. 다른 후보 (이번에는 선택하지 않음)

| 후보 | 관찰 | 선택하지 않은 이유 |
|---|---|---|
| NMS · 중복 검출 | `failure_analysis.csv`에서 같은 객체 BBox 겹침 약 10건 | 전체 Precision .926으로 영향이 작음 · 재학습 실험이 아님 |
| Class 4 → 1 혼동 | 5건, 신뢰도 0.72~0.92 | Class 4 val Recall .971로 지표상 영향이 작음 · train의 Class 4 이미지 100장이 전부 미승인(excluded)이라 별도 검수 과제로 넘김 |
| Class 2 ↔ 0 혼동 | 6건, 대부분 BBox 겹침과 함께 발생 | 두 Class 모두 Recall 0.89 이상 |

---

## 8. 남은 확인 사항

**알려진 한계 (`failure_analysis.csv` 수정하지 않음)**
- `ground_truth`·`prediction` 열은 Class가 아니라 박스 개수입니다. Class 정보는 `evidence` 열에 있습니다.
- confidence 열에 `—`와 `ㅡ`가 섞여 있고, 19줄 `prediction`에 `7*`(7개·8개 혼재)이 있습니다.

- `demo/failure_analysis/` 이미지는 예측 박스만 그려져 있어, GT 비교는 csv `evidence`와 이 문서로 대신합니다.
- [ ] `runs/baseline_v1/args.yaml`에서 `hsv_h` · `hsv_s` · `hsv_v` 실제 값 확인 → 5절 채우기
- [ ] 7일차 변수 A 승인
- [ ] 7일차 계획(`baseline_best.pt`에서 이어서 학습)은 시작 가중치가 바뀌어 두 번째 변수가 됨 → Baseline과 같은 시작 조건으로 학습