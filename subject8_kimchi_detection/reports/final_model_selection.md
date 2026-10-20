# Final Model Selection

- 기준: 교과8 수행가이드 21 (Final Model은 Frozen Test를 보기 전에 Validation 근거로 선택)
- 비교 대상: Baseline (`baseline_v1`) · Improved (`exp001`)
- 근거 문서: `reports/baseline_vs_improved.md` · `reports/failure_hypothesis.md` · `reports/experiment_log.csv`

---

## 1. 선택 흐름

```text
Baseline  +  Improved (EXP001)
        ↓
같은 Validation에서 비교 (100장 · 501 instances)
        ↓
지표 + 실패 사례
        ↓
Final Model 선택
```

---

## 2. 후보

| 후보 | Weight | 변경 변수 | 학습 조건 |
|---|---|---|---|
| Baseline | `models/baseline/baseline_best.pt` (sha256 `c90f9767442e`) | — | yolo11n · imgsz 1920 · 100 epoch · batch 3 · seed 0 · kimchi_v1 |
| EXP001 | `models/improved/exp001_best.pt` | 색상 Augmentation 끄기 (`hsv_h/s/v` → 0) | 나머지 Baseline과 같음 |

---

## 3. 지표 비교 (Validation)

| 지표 | Baseline | EXP001 | 차이 |
|---|---|---|---|
| Precision | 0.926 | 0.937 | +0.011 |
| Recall | 0.849 | 0.824 | **−0.025** |
| mAP50 | 0.889 | 0.884 | −0.005 |
| mAP50-95 | 0.780 | 0.775 | −0.005 |
| 병해·갈변 Recall | 0.367 | 0.355 | −0.012 |
| 병해·갈변 mAP50 | 0.427 | 0.435 | +0.008 |
| 추론 시간 (이미지 1장) | 14.0 ms | 같은 모델 크기·해상도 (차이 없음으로 추정) | — |

- 수치: 학습 종료 시 검증값 (best.pt). 상세는 `baseline_vs_improved.md` 2·3절

---

## 4. 실패 사례 비교 (6일차 패턴)

| 패턴 | Baseline | EXP001 | 판단 |
|---|---|---|---|
| 병해·갈변 정답 검출 | 18 / 31 | 21 / 31 | 소폭 증가 |
| 병해·갈변 FN | 10 / 31 | 9 / 31 | 거의 같음 |
| 병해·갈변 FP (background → 병해·갈변) | 762 | 501 | EXP001 −34% |
| 나뭇가지 → 나뭇잎 | 10 | 17 | EXP001 악화 |
| 고무장갑 → 플라스틱 | 11 | 15 | EXP001 악화 |
| 나뭇가지류 Recall | 0.897 | 0.825 | EXP001 악화 |

- 병해·갈변 수치(18 / 762 / 10)는 단독 val(`baseline_best.pt`, imgsz 1920 · batch 3) 기준입니다. Baseline CM 그림(`figures/baseline_confusion_matrix.png`)은 학습 종료 시 검증 값이라 17 / 764 / 10입니다.

---

## 5. 선택 결과

**Final Model: Baseline (`baseline_v1`)**

| 판단 기준 | 결과 |
|---|---|
| 주 목표 (병해·갈변 미검출 개선) | EXP001도 해결 못 함 (Recall 0.367 → 0.355) |
| 전체 성능 | EXP001이 Recall · mAP50 · mAP50-95 모두 낮음 |
| 다른 클래스 영향 | EXP001에서 나뭇가지 Recall −0.072, 가지 → 잎 · 고무장갑 → 플라스틱 혼동 증가 |
| EXP001의 장점 | 병해·갈변 FP 34% 감소 · Precision +0.011 — 하지만 놓치는 객체가 늘어나는 것이 이물검출에서 더 큰 손해 |

- 이물검출은 **놓치는 것(FN)이 잘못 찾는 것(FP)보다 위험**합니다. 이물이 섞인 제품이 그대로 통과하기 때문입니다. 그래서 Recall이 높은 Baseline을 선택합니다.
- 개선 실험이 Baseline을 넘지 못한 것도 결과로 기록합니다 (20.4).

**선택한 Weight**

```text
models/final/final_best.pt   ← models/baseline/baseline_best.pt 복사본 (sha256 c90f9767442e)
```

```bash
cp models/baseline/baseline_best.pt models/final/final_best.pt
sha256sum models/final/final_best.pt | cut -c1-12   # c90f9767442e 확인
```
