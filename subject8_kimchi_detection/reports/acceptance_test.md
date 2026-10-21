# Acceptance Test — 교과8 조각김치 이물검출

- 기준: 교과8 수행가이드 22.7 (PASS/FAIL만 적지 않고, FAIL은 수정 후 Retest까지 기록)
- 대상: Dataset `kimchi_v1` · Final Model `models/final/final_best.pt` (sha256 `c90f9767442e`)
- 실행 환경: RTX 3060 12GB · Ultralytics 8.4.175 · torch 2.14.1+cu130 · Python 3.10.12
- 판정 표기: PASS · FAIL → Retest PASS · **확인 필요** (9일차 실행 후 기입)

---

## 1. Dataset

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| D1 | 교과7 FINAL 데이터 출처 확인 | PASS | 교과7 FINAL JPG 900 + YOLO TXT 900 · `manifests/split_manifest.csv` |
| D2 | Dataset Version 확인 | PASS | `kimchi_v1` · train labels `57f0bf5121e4` · val labels `ab6cc7f98da7` |
| D3 | `source_dataset / original_split / scene_type` 추적 | PASS | `split_manifest.csv` 900행 (16.1 최소 열 보완 완료) |
| D4 | Train / Validation / Frozen Test / Bridge Holdout Manifest 존재 | PASS | `manifests/train.csv` · `val.csv` · `test.csv` · `bridge_holdout.csv` (600 · 100 · 100 · 100) |
| D5 | Split 정책 설명 가능 | PASS | `docs/split_policy.md` · Split Freeze 2026-10-13 commit `1b074fa` |
| D6 | Frozen Test를 Final 선택 전에 사용하지 않음 | PASS | `final_model_selection.md`(Validation 근거) 작성 후 `11_evaluate_final_test.py` 1회 실행 |
| D7 | Bridge Holdout을 학습·튜닝·선택·Test에 사용하지 않음 | PASS | `configs/dataset.yaml`에 Holdout 없음 · Auto Label 이미지도 Test에서만 추출 |

---

## 2. Model

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| M1 | Baseline과 Final 구분 | PASS | `models/baseline/` · `models/improved/` · `models/final/` |
| M2 | Baseline 학습조건 기록 | PASS | `reports/baseline_training_condition.md` (yolo11n · imgsz 1920 · 100 epoch · batch 3 · seed 0) |
| M3 | `baseline_best.pt` 존재 | PASS | sha256 `c90f9767442e` |
| M4 | `final_best.pt` 존재 | PASS | `baseline_best.pt` 복사본 · sha256 `c90f9767442e` 일치 |
| M5 | Final 선택 이유 기록 | PASS | `reports/final_model_selection.md` — EXP001 Recall −0.025, 이물검출에서 FN이 더 위험 |

---

## 3. Evaluation

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| E1 | Baseline Validation 결과 | PASS | `reports/baseline_metrics.csv` |
| E2 | Precision | PASS | Val 0.926 · Test 0.957 |
| E3 | Recall | PASS | Val 0.849 · Test 0.887 |
| E4 | mAP50 | PASS | Val 0.889 · Test 0.919 |
| E5 | mAP50-95 | PASS | Val 0.780 · Test 0.808 |
| E6 | Failure Analysis | PASS | `reports/failure_analysis.csv` (29건) · `failure_hypothesis.md` · `demo/failure_analysis/` |
| E7 | Baseline vs Improved 비교 | PASS | `reports/baseline_vs_improved.md` · `experiment_log.csv` · `improvement_experiment.md` |
| E8 | Frozen Test 결과 | PASS | `reports/final_metrics.csv` (100장 · 474 instances) · `reports/figures/final_test_confusion_matrix.png` |

---

## 4. Inference

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| I1 | 이미지 Detection 실행 | PASS | `scripts/12_auto_label_candidates.py` · 8장 |
| I2 | BBox 표시 | PASS | `demo/prediction_images/*.jpg` 8장 |
| I3 | Class 표시 | PASS | 같은 이미지 |
| I4 | Confidence 표시 | PASS | 같은 이미지 (conf 0.25 이상) |

---

## 5. Auto Label

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| A1 | 새 이미지에서 후보 라벨 생성 | PASS | 학습에 쓰지 않은 Frozen Test 8장(seed 42, Test 평가 후) → 후보 36개 |
| A2 | YOLO TXT 후보 저장 | PASS | `demo/auto_label/candidate_labels/*.txt` 8개 |
| A3 | 교과7 라벨링 도구에서 다시 열기 | PASS | `subject7_kimchi_labeling/data/auto_label_review/` 에서 8장 Load |
| A4 | 사람이 수정·삭제·추가 | PASS | Class 수정 1 · 삭제 1 · 추가 0 |
| A5 | 승인 라벨 저장 | FAIL → Retest PASS | 아래 FAIL-01 · `demo/auto_label/reviewed_labels/*.txt` 8개 |

**Auto Label 집계** (`reports/auto_label_review.csv`)

| 새 이미지 | 후보 BBox | 그대로 승인 | Class 수정 | BBox 수정 | 삭제 | 누락 추가 | REVIEW |
|---|---|---|---|---|---|---|---|
| 8 | 36 | 34 | 1 | 0 | 1 | 0 | 0 |

---

## 6. 재실행 확인 (22.6)

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| R1 | 다른 팀원이 README만 보고 Final Model Load · Prediction 실행 | PASS | 다른 팀원 환경에서 README 5-2 · 5-4 순서로 실행 확인 |
| R2 | 다른 팀원이 Auto Label 후보 생성 → 교과7 도구 Human Review | PASS | 다른 팀원 환경에서 후보 생성 · 교과7 도구 검수 · 저장 확인 |

---

## 7. FAIL 기록

**FAIL-01 — Auto Label 검수 1장 저장 누락**
- 문제: 검수 결과 8장 중 1장(`250513_021522087814`)이 후보와 같은 상태로 남음
- 원인: 검수 후 저장 버튼을 누르지 않음 (프로그램 오류 아님). 이력 csv는 박스 삭제를 남기지 않아 집계에서도 빠짐
- 수정: 다시 열어 Class 1 박스 1개 삭제 후 저장 · `auto_label_review.csv` 해당 행 수정
- Retest: 후보 4줄 → 검수 3줄 확인 · PASS

**FAIL-02 — Frozen Test Script 0바이트**
- 문제: `11_evaluate_final_test.py` 실행 시 출력 없음
- 원인: 처음 저장한 파일이 0바이트
- 수정: 다시 저장 후 `wc -c`로 크기 확인 · 빈 `runs/final_test` 폴더 삭제 (Test는 실행되지 않은 상태)
- Retest: 1회 실행 · PASS

**FAIL-03 — Confusion Matrix 전부 0**
- 문제: 단독 val의 CM 값이 모두 0
- 원인: `plots=False` 로 실행
- 수정: `plots=True` (Validation에서 확인 후 Frozen Test에 적용)
- Retest: PASS

---

## 8. 최종 판정

| 구분 | 항목 수 | PASS | 확인 필요 |
|---|---|---|---|
| Dataset | 7 | 7 | 0 |
| Model | 5 | 5 | 0 |
| Evaluation | 8 | 8 | 0 |
| Inference | 4 | 4 | 0 |
| Auto Label | 5 | 5 | 0 |
| 재실행 | 2 | 2 | 0 |

- Critical Error: 0건 · 미해결 FAIL: 0건
- **최종 판정: ACCEPTED**

**알려진 한계 (판정에는 영향 없음)**
- 병해·갈변(Class 5) Test Recall 0.636 — 다른 클래스(0.88 이상)보다 낮음. 교과14 인계 항목
- 개선 실험 EXP001은 Baseline을 넘지 못함 (`baseline_vs_improved.md`)
