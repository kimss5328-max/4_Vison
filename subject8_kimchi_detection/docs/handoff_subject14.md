---
title: 교과 14 Handoff
project: 조각김치 이물검출 AI · 데이터 구축부터 모델까지 (교과 8)
type: Handoff
status: ACCEPTED (재실행 확인 R1 · R2 후 확정)
created: 2026-10-16
updated: 2026-10-19
---

# 교과 14 Handoff

> 교과 8에서 학습 · 평가한 조각김치 이물검출 Final Model과 Bridge Holdout을 교과 14로 넘기기 위한 인계 문서다.
> 교과 8 전체 설명은 `README.md`, 인수 시험 결과는 `reports/acceptance_test.md` 를 본다. 경로는 모두 `subject8_kimchi_detection/` 기준이다.

## 1. 개요

| 항목 | 내용 |
|---|---|
| 프로젝트 | 조각김치 이물검출 AI (교과 7 데이터 구축 → 교과 8 모델 학습) |
| 인계 목적 | 교과 14 에서 Final Model 을 서비스(API) 백엔드 파이프라인 · 제품검사 흐름에 연결 |
| 모델 | YOLO11n · 7클래스 Detection |
| Dataset Version | `kimchi_v1` |
| 교과 8 판정 | Acceptance Test ACCEPTED (재실행 확인 R1 · R2 남음) |

---

## 2. 인계 내용

| 항목                  | 위치                                                                                                          | 상태               |
| ------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------- |
| Final Model 가중치     | `models/final/final_best.pt` (sha256 앞 12자리 `c90f9767442e`)                                                 | 완료               |
| Final Model 선택 근거   | `reports/final_model_selection.md`                                                                          | 완료               |
| Frozen Test 결과      | `reports/final_metrics.csv` · `reports/figures/final_test_confusion_matrix.png` · `final_test_pr_curve.png` | 완료               |
| Baseline 학습 조건      | `reports/baseline_training_condition.md`                                                                    | 완료               |
| 개선 실험 기록            | `reports/improvement_experiment.md` · `reports/experiment_log.csv` · `reports/baseline_vs_improved.md`      | 완료               |
| 실패 분석               | `reports/failure_hypothesis.md` · `reports/failure_analysis.csv` · `demo/failure_analysis/`                 | 완료               |
| Bridge Holdout 100장 | `data/bridge_holdout/{images,labels}` · `manifests/bridge_holdout.csv`                                      | 완료 (미사용 상태 유지)   |
| Prediction 이미지      | `demo/prediction_images/` 8장                                                                                | 완료               |
| Auto Label 검수 결과    | `demo/auto_label/candidate_labels/` · `demo/auto_label/reviewed_labels/` · `reports/auto_label_review.csv`  | 완료 (8장 · 후보 36개) |
| Acceptance Test     | `reports/acceptance_test.md`                                                                                | ACCEPTED         |

- 가중치 · 이미지 · 라벨 txt · `runs/` · `demo/` 는 GitHub 에 포함하지 않는다 (NDA). 별도 경로로 전달한다.

---

## 3. Dataset

| 항목              | 내용                                                                                  |
| --------------- | ----------------------------------------------------------------------------------- |
| 교과 7 FINAL      | 이미지 900장 (JPG, 4848×2704) + YOLO TXT 900개 · BBox 4,433개                             |
| Dataset Version | `kimchi_v1` · labels sha256 train `57f0bf5121e4` / val `ab6cc7f98da7`               |
| Split           | Train 600 · Validation 100 · Frozen Test 100 · Bridge Holdout 100 (층화 분할 · seed 42) |
| Split Freeze    | `manifests/split_manifest.csv` · commit `1b074fa` (2026-10-13)                      |

**Bridge Holdout**

| 항목 | 내용 |
|---|---|
| 위치 | `data/bridge_holdout/{images,labels}` · `manifests/bridge_holdout.csv` |
| 수량 | 이미지 100장 · 박스 497개 |
| Class 별 박스 (이미지) | 0 나뭇잎·종이 93 (43) · 1 플라스틱·돌·금속 186 (65) · 2 나뭇가지 96 (43) · 3 벌레 34 (19) · 4 고무장갑 34 (19) · 5 병해·갈변 29 (16) · 6 파·고추 25 (5) |

**Bridge Holdout 미사용 확인**
- Train · Validation · Final Model 선택 · Frozen Test 모두 미사용
- `configs/dataset.yaml` 에 Holdout 경로 없음 · Acceptance D7 PASS

---

## 4. Final Model

| 항목 | 값 |
|---|---|
| 선택 모델 | Baseline (`baseline_v1`) |
| 학습 조건 | YOLO11n (`yolo11n.pt` 사전학습) · imgsz 1920 · 100 epoch (best 90) · batch `-1` (자동 결정 → 3) · seed 0 |
| 학습 데이터 | Train 600 / Validation 100 |
| 추론 해상도 | 1920 |
| 추론 시간 | 이미지 1장 14.0 ms (RTX 3060 기준) |
| 실행 환경 | Ultralytics 8.4.175 · PyTorch 2.14.1+cu130 · Python 3.10.12 · RTX 3060 12GB |

**선택 이유**
- 개선 실험 EXP001(색상 Augmentation 끄기)이 Recall · mAP50 · mAP50-95 모두 Baseline 보다 낮음
- 이물검출은 놓치는 것(FN)이 잘못 찾는 것(FP)보다 위험 → Recall 이 높은 Baseline 선택
- Frozen Test 를 보기 전에 Validation 근거로 선택함

### 4-1. Class

| ID | 이름 |
|---|---|
| 0 | 나뭇잎·종이류 |
| 1 | 플라스틱·돌·금속류 |
| 2 | 나뭇가지류 |
| 3 | 벌레류 |
| 4 | 고무장갑 |
| 5 | 병해·갈변 |
| 6 | 파·고추 |

- 서비스에서 Class 이름을 표시할 때 위 ID 순서를 그대로 사용한다 (`configs/dataset.yaml` 과 동일).

---

## 5. 실행 방법

```bash
cd subject8_kimchi_detection
pip install -r requirements.txt   # ultralytics 8.4.175 · torch 2.14.1 · torchvision 0.29.1 · opencv-python 등

# Final Model 추론 (교과 8 Detection · Auto Label 과 같은 조건)
yolo predict model=models/final/final_best.pt source=<이미지 폴더> imgsz=1920 conf=0.25 save=True
```

- 상세 실행 순서: `README.md` 5절

---

## 6. 성능 (Frozen Test 100장 · 1회 실행)

| 클래스 | 이미지 | 박스 | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| **전체** | 100 | 474 | **0.957** | **0.887** | **0.919** | **0.808** |
| 0 나뭇잎·종이류 | 36 | 76 | 0.946 | 0.882 | 0.927 | 0.840 |
| 1 플라스틱·돌·금속류 | 65 | 171 | 0.938 | 0.892 | 0.957 | 0.852 |
| 2 나뭇가지류 | 48 | 101 | 0.911 | 0.910 | 0.964 | 0.900 |
| 3 벌레류 | 24 | 38 | 0.998 | 0.974 | 0.994 | 0.835 |
| 4 고무장갑 | 17 | 27 | 0.925 | 0.912 | 0.899 | 0.808 |
| 5 병해·갈변 | 16 | 31 | 1.000 | **0.636** | **0.698** | 0.539 |
| 6 파·고추 | 6 | 30 | 0.981 | 1.000 | 0.995 | 0.884 |

| 구분 | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|
| Validation (Baseline) | 0.926 | 0.849 | 0.889 | 0.780 |
| Frozen Test (Final) | 0.957 | 0.887 | 0.919 | 0.808 |

---

## 7. 잘하는 상황 · 약한 상황

**잘하는 상황**
- 병해·갈변을 뺀 6개 Class 는 Frozen Test Recall 0.88 이상 (파·고추 1.000 · 벌레류 0.974)
- 모든 Class 의 Precision 이 0.91 이상 → 잘못 찾는 경우는 적음
- Validation mAP50-95 0.780 → Frozen Test 0.808 로 처음 보는 데이터에서도 성능 유지

**약한 상황**
- 병해·갈변: Frozen Test Recall 0.636 — 놓치기도(FN) 하고 다른 위치에 붙이기도(FP) 함
- 나뭇가지 ↔ 나뭇잎 혼동 (Validation 10건)
- 고무장갑 → 플라스틱 혼동 (Validation 11건)
- 같은 객체에 중복 박스 (약 10건)

---

## 8. 대표 실패

| 구분 | 이미지 | 내용 |
|---|---|---|
| FN | `demo/failure_analysis/250424_150751737200.jpg` | 병해·갈변 2개 미검출 |
| FP | `demo/failure_analysis/250410_171711703137.jpg` | 나뭇가지를 병해·갈변으로 예측 |
| FP | `demo/failure_analysis/250424_112553658191.jpg` | 병해·갈변 오검출 |
| FP | `demo/failure_analysis/250424_141451512347.jpg` | 병해·갈변 오검출 |

- 상세: `reports/failure_analysis.csv` (대표 실패 29건) · `reports/failure_hypothesis.md`

---

## 9. Detection · Auto Label 결과

- **대상:** 학습에 쓰지 않은 Frozen Test 8장 (seed 42 · Frozen Test 평가가 끝난 뒤 사용)
- **조건:** Final Model · imgsz 1920 · conf 0.25
- **검수:** 교과 7 라벨링 도구 사본(`subject7_kimchi_labeling/data/auto_label_review/`)에서 사람이 확인

| 검수 이미지 | 후보 BBox | 그대로 승인 | Class 수정 | BBox 수정 | 삭제 | 누락 추가 | REVIEW |
|---|---|---|---|---|---|---|---|
| 8 | 36 | 34 | 1 | 0 | 1 | 0 | 0 |

---

## 10. 교과 14 에서 주의할 점

| # | 내용 |
|---|---|
| 1 | **병해·갈변 검출이 가장 약함** — Frozen Test Recall 0.636. 서비스 결과에서 병해·갈변 미검출 가능성을 안내하거나 사람 확인 단계를 두는 것을 권장 |
| 2 | **Bridge Holdout 100장은 교과 8에서 학습 · 분석 · 평가에 쓰지 않았다.** 교과 14 의 독립 평가용으로 그대로 사용 |
| 3 | 입력 해상도는 1920 기준으로 학습했다. 다른 해상도로 추론하면 성능이 달라질 수 있음 |
| 4 | Confidence Threshold: 교과 8 Detection · Auto Label 은 **conf 0.25** 로 실행. 서비스용 값은 교과 14 에서 확정 |
| 5 | Auto Label 결과는 사람 검수 전에는 정답으로 쓰지 않는다 |

---

## 11. 교과 14 에서 이어갈 내용

1. Bridge Holdout 100장으로 Final Model 연결 성능 확인 → Frozen Test (mAP50-95 0.808) 와 비교
2. 실제 제조환경 카메라 입력 연결
3. 현장 조명 · 배경 변화에서 성능 확인 — 특히 색으로 구분하는 병해·갈변
4. On-Device 환경 확장 (예: Jetson Orin Nano Super)
5. 추론속도 · Latency · FPS 확인 — 교과 8 기준 14.0 ms (RTX 3060)
6. 서비스(API) · 실제 제품검사 판정 흐름과 연결 — 병해·갈변은 사람 확인 단계 권장

---

## 12. 참고 문서

| 문서 | 내용 |
|---|---|
| `README.md` | 교과 8 전체 흐름 · 실행 방법 · 결과 요약 |
| `docs/split_policy.md` | Split 기준 · Bridge Holdout 보존 원칙 |
| `docs/class_guide.md` · `docs/bbox_guide.md` | Class · BBox 판단 기준 (교과 7) |
| `reports/final_model_selection.md` | Final Model 선택 근거 |
| `reports/final_metrics.csv` | Frozen Test 지표 |
| `reports/acceptance_test.md` | Acceptance Test 결과 · FAIL 기록 |
| `reports/auto_label_review.csv` | Auto Label 검수 기록 |
