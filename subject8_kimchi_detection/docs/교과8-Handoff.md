---
title: 교과8 Handoff
project: 조각김치 이물검출 라벨링 프로젝트 (교과 7)
type: Handoff
owner: 권지현
status: 미작성 (5일차 확정)
created: 2026-10-02
updated: 2026-10-02
source: Google Sheet - 교과8 Handoff
---

# 교과8 Handoff — 다음 프로젝트 데이터 인계

## 개요
교과 7에서 검수 완료한 조각김치 이물검출 YOLO Dataset을
교과 8 Object Detection 학습에서 사용할 수 있도록 전달합니다.

---

## 2. FINAL Dataset

- 전체 이미지: 900장
- FINAL Image: 900장
- FINAL Label: 900개
- Label Format: YOLO Detection TXT
- 이미지와 TXT 파일명 Pair 확인 완료

FINAL 데이터 위치:

data/final/
├── img/
└── txt/

예:

250410_144403911987.jpg
250410_144403911987.txt

---
## 3. YOLO Label Format

TXT 한 줄은 객체 하나를 의미합니다.

class_id x_center y_center width height

예:

6 0.8006198347 0.6231481481 0.0340909090 0.0537037037

좌표값은 이미지 크기 대비 0~1 범위의 정규화 좌표입니다.
## 4. Class 정보

- Class 0: 나뭇잎·종이류
- Class 1: 플라스틱류·돌·금속류
- Class 2: 나뭇가지류
- Class 3: 벌레류
- Class 4: 고무장갑 — 현재 사용하지 않음/ # 기존 라벨에 4가 있으면 1(플라스틱류·돌·금속류)로 변경 안내
- Class 5: 병해·갈변
- Class 6: 파·고추

상세 Class 기준:

docs/class_guide.md

프로그램 Class 설정:

configs/classes.yaml
---

## 5. BBox 기준

객체 외곽선과 BBox 사이에 2~4px의 최소 여백을 둔다.

상세 기준:

docs/bbox_guide.md

---

## 6. QA 결과

교과 7 최종 QA 결과:

- Validation PASS: 729장
- FAIL: 0장
- REVIEW: 171장
- Critical Error: 0건

상세 QA 결과:

reports/qa_summary.md

프로그램 테스트 결과:

reports/test_report.md

---

## 7. Dataset 작업 이력

900장의 작업 상태와 검수 이력은 다음 파일에서 확인합니다.

manifests/dataset_manifest.csv

확인 가능한 정보:

- 원본 데이터 출처
- 기존 Split
- 작업자
- 작업 상태
- QA 상태
- REVIEW 사유

---

## 8. 교과 8 전달 자료

교과 8에서는 다음 자료를 사용합니다.

4_Vision/
├── ... (기존 파일 및 폴더들)
│
└── handoff_subject08/                    
    ├── final_dataset/                   
    │   ├── img/                      
    │   └── txt/                      
    │
    ├── dataset_manifest.csv              
    ├── class_guide.md                    
    ├── bbox_guide.md                   
    └── subject08_handoff.md

※ 실제 900장 데이터는 GitHub에 올리지 않고 내부 저장소 또는 지정된 교육환경에서 전달합니다.

---

## 9. 교과 8에서 확인할 내용

교과 8 시작 시 다음을 먼저 확인합니다.

1. 이미지와 TXT Pair가 정상인지 확인
2. Class 0~6 설정 확인
3. Class 4 사용 여부 확인
4. YOLO TXT 형식 확인
5. 기존 Dataset Split 정보 확인
6. 학습용 Dataset 설정 파일 구성
7. YOLO Object Detection 학습 진행

---

## 10. 교과 8 연결 흐름

교과 7 FINAL Dataset
        ↓
이미지 / YOLO TXT 확인
        ↓
Dataset Manifest 확인
        ↓
Class / BBox 기준 확인
        ↓
기존 Split 정보 확인
        ↓
교과 8 학습용 Dataset 구성
        ↓
YOLO Object Detection 학습
        ↓
Validation
        ↓
성능평가

## 참고 문서
- [[QA-Summary]]
- [[Test-Report]]
- [[Class-기준서]]
- [[BBox-기준서]]

## 변경 이력
| 날짜 | 작성자 | 변경 내용 |
|---|---|---|
| 2026-10-02 | 권지현 | 최초 작성 (Google Sheet → md 변환) |
| 2026-10-12 | 김도은 | Handoff 요약 테이블 추가 및 폴더 경로(img, txt) 수정, BBox/Class 기준 보완 |