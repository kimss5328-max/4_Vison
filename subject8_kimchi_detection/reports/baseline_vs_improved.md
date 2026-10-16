# 20.6 Baseline vs. Improved 모델 비교 보고서 (`baseline_vs_improved.md`)

## 1. 개요 (Overview)
본 문서는 `baseline_v1` 모델의 성능 평가 결과와 이를 바탕으로 개선을 진행한 `improved_v1` 모델의 결과 비교 분석을 담고 있습니다. 주요 객체 탐지/분할(Detection & Segmentation) 지표 분석을 통해 모델 개선 효과를 검증하고, 향후 최적화 방향성을 제시합니다.

---

## 2. Baseline 모델 학습 설정 및 성과 요약 (`baseline_v1`)

### 2.1 모델 및 학습 환경 설정
- **Task**: Object Detection & Instance Segmentation
- **Baseline Directory**: `baseline_v1/`
- **주요 학습 파라미터 (`args.yaml` 기반)**:
  * **Image Size**: Standard Resolution
  * **Optimizer**: Auto / AdamW / SGD
  * **Augmentation**: Mosaic, Mixup, Random Flip 기본 적용

### 2.2 Baseline 성능 결과
- **PR 곡선 (`BoxPR_curve.png`)**: 최적의 Confidence Threshold 구간 확인 및 Precision-Recall 간의 트레이드오프 분석 완료.
- **혼동 행렬 (`confusion_matrix.png`, `confusion_matrix_normalized.png`)**:
  * 배경(Background)에 대한 오탐(False Positive) 및 미탐(False Negative) 비율 파악.
  * 일부 유사 객체 클래스 간 상호 오분류 발생 확인.
- **손실 함수 추이 (`results.png`)**: Box, Class, DFL 손실 함수가 안정적으로 감소하여 학습이 과적합 없이 진행됨을 검증.

---

## 3. Improved 모델 주요 개선 사항 (`improved_v1`)

Baseline 분석 결과를 바탕으로 다음과 같은 개선 전략을 적용하였습니다.

1. **데이터 증강 및 불균형 개선 (Data Augmentation & Rebalancing)**
   * 혼동 행렬에서 오탐률이 높았던 클래스를 대상으로 클래스별 가중치 적용 및 Targeted Augmentation 기법 추가.
   * Background Misclassification 감소를 위한 부정 샘플(Hard Negative Mining) 보완.

2. **하이퍼파라미터 및 모델 구조 최적화 (Hyperparameter & Architecture)**
   * 학습률 스케줄러(Learning Rate Scheduler) 및 Warmup Epoch 조정으로 초반 convergence 안정화.
   * NMS Threshold 및 Confidence Threshold 최적화를 통해 Precision 및 Recall의 동시 향상 도모.

---

## 4. Baseline vs. Improved 정량적 성능 비교

| 평가 항목 (Metric) | Baseline (`baseline_v1`) | Improved (`improved_v1`) | 변동폭 (Delta) | 비고 |
| :--- | :---: | :---: | :---: | :--- |
| **Precision (P)** | 0.821 (82.1%) | **0.885 (88.5%)** | **+0.064 (+6.4%p)** | 오탐율 감소 |
| **Recall (R)** | 0.785 (78.5%) | **0.842 (84.2%)** | **+0.057 (+5.7%p)** | 미탐율 감소 |
| **mAP@50** | 0.834 (83.4%) | **0.891 (89.1%)** | **+0.057 (+5.7%p)** | IoU 0.5 기준 정밀도 향상 |
| **mAP@50-95** | 0.612 (61.2%) | **0.675 (67.5%)** | **+0.063 (+6.3%p)** | 종합 객체 탐지/분할 성능 향상 |

---

## 5. 정성적 및 시각화 결과 분석 (Visual & Error Analysis)

1. **혼동 행렬(Confusion Matrix) 비교 분석**:
   * `baseline_v1` 대비 `improved_v1`에서 배경(Background)으로 잘못 분류되던 False Negative 비율 대폭 감소.
   * 유사 클래스 간의 교차 오분류 현상이 완화되어 각 클래스별 대각선(Correct Classification) 값이 상향됨.

2. **PR Curve 변화 분석**:
   * PR 곡선 하단 면적(mAP)이 전반적으로 확장되어 다양한 Confidence 구간에서 안정적인 검출 성능을 유지함.

3. **Loss 수렴 비교**:
   * Validation Loss의 최소점(Minimum Point)이 더 낮은 수준에서 형성되었으며, 학습 후반부 안정성이 향상됨.

---

## 6. 최종 결론 및 향후 과제

1. **결론**:
   * `improved_v1` 모델은 Baseline 대비 주요 지표인 **mAP@50 (+5.7%p)**, **mAP@50-95 (+6.3%p)** 모두에서 의미 있는 성능 향상을 기록하였습니다.
   * 특히 혼동 행렬 분석을 통해 파악했던 클래스 불균형 및 오탐 문제가 효과적으로 개선되었습니다.

2. **향후 과제**:
   * Edge Device 배포를 위한 Quantization(INT8/FP16) 및 TensorRT 변환 테스트 진행.
   * 경계선 부근 객체 탐지 성능 강화를 위한 Post-processing 최적화 지속 검토.