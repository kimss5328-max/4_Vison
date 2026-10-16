"""
[진행 현황] failure_analysis.csv 초안 작성 완료, 대표 실패 5장 분석 완료.
            통계 확정 및 Validation 전체 분석은 다음 단계.

1. 왜 필요한가?
   - mAP 숫자만으로는 무엇을 고쳐야 하는지 알 수 없다.
   - 실제 실패 사례를 분석해 모델의 문제점과 개선 방향을 구체적으로 찾는다.

2. 입력은?
    -Ground Truth     : data/yolo/labels/val/*.txt (YOLO txt · 100장 · 501박스)
    -모델 Prediction   : models/baseline/baseline_best.pt 로 val 재예측(imgsz 1920 · conf 0.25 · iou 0.7 · Baseline 과 같은 조건)
    -Validation 결과   : reports/baseline_metrics.csv · Confusion Matrix (reports/figures/)
                    → 클래스별 지표로 집중 분석할 클래스 선정 (예: Class 5 Recall 0.367)
    -Dataset Manifest  : manifests/split_manifest.csv (val 100행)
                    → source_dataset · scene_type · group(검수 상태) 를 이미지 이름으로 연결

3. 무엇을 찾아야 하는가?
   - FP         : GT에 없는 객체 검출 / 동일 객체 중복 검출
   - FN         : GT에 있는데 검출 못함
   - Class Error: 위치는 맞지만 다른 클래스로 예측
   - BBox Error : 클래스는 맞지만 박스 위치/크기가 틀림

4. 처리 순서는?
   Validation 결과에서 분석할 이미지 선정
     -> GT와 Prediction 비교(매칭)
     -> FP / FN / Class Error / BBox Error 분류
     -> scene_type 확인
     -> 추정 원인과 판단 근거 기록
     -> 다음 실험 및 개선 조치 작성(사람이 검토 후 기입)

5. 출력은?
   - failure_analysis.csv
   - ~/4_Vison/subject8_kimchi_detection/demo/failure_analysis/ 29장
   - 실패 유형별 통계 대표 29강 기준
    Class Error	16
    FP	14
    FN	10
    BBox Error	2

6. 성공 기준은?
   - 병해·갈변(Class 5)의 FN이 반복된다 (Recall 0.367, 31개 중 약 20개 미검출)

7. 발생 가능한 문제는? (코드에서의 대응)
   - GT-Prediction 잘못 연결 -> IoU 기반 + 점수 높은 순 1:1 매칭
   - 동일 실패 중복 집계    -> GT/Prediction 각각 한 번만 소비(used set)
   - Confidence만으로 원인 단정 -> suspected_cause는 '가설'로만 기록, 근거(IoU 등) 함께 저장
   - 객체 개수만으로 유형 확정 -> 개수가 아니라 개별 객체 매칭 결과로 분류

8. 작은 시험은?  --limit 5  (실패가 많은 이미지 5장만 먼저 분석)

9. 성공하면?     --limit 0  (Validation 전체로 확장)

10. 무엇을 기록하는가?
   image, source_dataset, scene_type, failure_type, ground_truth,
   prediction, confidence, suspected_cause, evidence, next_action
"""