---
title: 교과 8 Handoff
project: 조각김치 이물검출 라벨링 프로젝트 (교과 7)
type: Handoff
status: 검토중
created: 2026-10-07
updated: 2026-10-08
---

# 교과 8 Handoff

> 교과 7에서 만든 검수 완료 YOLO 데이터셋을 교과 8(객체검출 모델 학습)로 넘기기 위한 인계 문서다.
> **QA Summary와 Test Report가 끝난 뒤 5일차에 작성한다.** #작성필요 표시는 그때 채운다.

## 1. 개요

| 항목     | 내용                                                                                 |
| ------ | ---------------------------------------------------------------------------------- |
| 프로젝트   | 조각김치 이물검출 라벨링 프로젝트 (교과 7)                                                          |
| 인계 목적  | 교과 8 객체검출 모델 학습에 바로 사용할 수 있는 검수 완료 YOLO 데이터셋 전달                                    |
| 데이터 형식 | 이미지(JPG) + YOLO Detection TXT (`class_id x_center y_center width height`, 0~1 정규화) |

---

## 2. 인계 내용

| 항목           | 내용                                                                         | 상태  |
| ------------ | -------------------------------------------------------------------------- | --- |
| 인계 데이터셋 경로   | `data/final/` (`images/`, `labels/`)                                       | 완료  |
| 총 이미지 수      | 900장                                                                       | 완료  |
| 총 라벨(BBox) 수 | 900개                                                                       | 완료  |
| 클래스 정의 문서    | [Class 가이드](class_guide.md)                                                | 완료  |
| BBox 작성 기준   | [BBox 가이드](bbox_guide.md)                                                  | 완료  |
| 작업 이력        | [Dataset Manifest](manifests/dataset_manifest.csv)                         | 완료  |
| 최종 QA 결과     | [QA Summary](reports/qa_summary.md), [Test Report](reports/test_report.md) | 완료  |

### 2-1 YOlO Label Format

이미지와 TXT는 파일명이 같은 한 쌍이다.

```text
250410_144403911987.jpg
250410_144403911987.txt
```

TXT 한 줄은 객체 하나를 뜻한다.

```text
class_id x_center y_center width height
```

예:

```text
6 0.8006198347 0.6231481481 0.0340909090 0.0537037037
```

좌표는 픽셀 값이 아니라 이미지 크기 대비 0~1 범위의 비율값이다.

### 2-2. Class 설정

| ID  | 이름          | 사용                                                |
| --- | ----------- | ------------------------------------------------- |
| 0   | 나뭇잎·종이류     | 사용                                                |
| 1   | 플라스틱류·돌·금속류 | 사용                                                |
| 2   | 나뭇가지류       | 사용                                                |
| 3   | 벌레류         | 사용                                                |
| 4   | 고무장갑        | **사용하지 않음** (기존 TXT에서 발견되면 임의로 삭제하지 않고 REVIEW 처리) |
| 5   | 병해·갈변       | 사용                                                |
| 6   | 파·고추        | 사용                                                |

클래스별 판단 기준은 [Class 가이드](class_guide.md)를 확인한다.

### 2-3. BBox 작업 기준

모든 클래스에 공통으로 적용되는 바운딩박스(BBox) 작성 규칙이다.

본 프로젝트의 BBox는 **객체의 실제 외곽선에 밀착하되, 외곽이 잘리지 않도록 2~4px의 최소 여백을 두는 Tight Box를 기본 원칙으로 한다.**

### 핵심 원칙

- 객체 외곽선과 BBox 사이에 **2~4px의 최소 여백을 둔다.**
- 기본 여백은 **2~4px**을 원칙으로 한다.
- 객체의 실제 외곽이 BBox 밖으로 잘리지 않도록 하되, 여백은 4px를 넘기지 않는다.
- 객체와 관계없는 배경이 BBox에 과도하게 포함되지 않도록 한다.
- 하나의 BBox에는 원칙적으로 하나의 객체만 포함한다.
- 판단이 어려운 경우 임의로 처리하지 않고 **REVIEW**로 분류한다.
 
BBox별 판단 기준은 [BBox 가이드](bbox_guide.md)를 확인한다.
### 2-4. QA 결과

최종 라벨 데이터의 품질검사 결과를 확인합니다.

[![최종 이미지](https://github.com/kimss5328-max/4_Vison/raw/main/docs/assets/last.png)](https://github.com/kimss5328-max/4_Vison/blob/main/docs/assets/last.png)

|판정|장수|
|---|---|
|PASS|729|
|FAIL|0|
|REVIEW|171|

최종 판정: 729(QA 완료 )

### 완료 기준 확인

미처리 REVIEW는 Class 4 고무장갑입니다. 

|완료 기준|목표|결과|
|---|---|---|
|미처리 REVIEW|0건|171|
|Validation 오류|0건|0|
|이미지와 TXT Pair|900 : 900|900:900|
|전체 검수|900장 완료|900|
|FINAL 데이터 정리|완료|900|

QA 결과는 [QA Summary](reports/qa_summary.md)를 확인한다.
프로그램 테스트 결과는 [Test Report](reports/test_report.md)를 확인한다.
### 2-5. Dataset 작업 이력

### Dataset Manifest

`manifests/` 폴더의 CSV에 저장할 때마다 한 줄씩 작업 이력이 추가된다. 900장의 작업상태를 확인할 수 있습니다.

| 항목                             | 의미                                  | 예시                                                                   |
| ------------------------------ | ----------------------------------- | -------------------------------------------------------------------- |
| `file_name`                    | 이미지 파일명                             | `250410_144403911987.jpg`                                            |
| `source_dataset`               | 이미지가 온 출처                           | `raw`                                                                |
| `original_split`               | 기존 train / validation 구분 (없으면 비워 둠) | `train`, `validation`                                                |
| `scene_type`                   | 이미지 전체 장면 유형                        | `kimchi_with_target`, `normal_kimchi`, `object_only`, `other_review` |
| `worker`                       | 작업자                                 | `4`                                                                  |
| `status`                       | 작업 상태                               | `DONE`,  `EDIT`, `REVIEW`                                            |
| `qa_status`                    | QA 진행 상태                            | `WAIT`                                                               |
| `review_reason`                | REVIEW 사유 (REVIEW가 아니면 비워 둠)        | `class_ambiguous`, `bbox_boundary_ambiguous`                         |

같은 이미지를 여러 번 저장하면 행이 여러 개 생긴다. 이미지별 현재 상태는 가장 최근 행으로 판단한다.

Dataset Manifest 작업 이력은 [Dataset Manifest](manifests/dataset_manifest.csv) 을 확인한다.

---
## 3. 교과 8 전달 자료

교과 8에서는 다음 자료를 사용합니다.

```
handoff_subject08/
├── final_dataset/
│   ├── images/
│   └── labels/
│
├── dataset_manifest.csv
├── class_guide.md
├── bbox_guide.md
└── subject08_handoff.md
```

※ 실제 900장 데이터는 GitHub에 올리지 않고 내부 저장소 또는 지정된 교육환경에서 전달합니다.

---

## 4. 교과 8에서 확인할 내용

교과 8 시작 시 다음을 먼저 확인합니다.

1. 이미지와 TXT Pair가 정상인지 확인
2. Class 0~6 설정 확인
3. Class 4 사용 여부 확인
4. YOLO TXT 형식 확인
5. 기존 Dataset Split 정보 확인
6. 학습용 Dataset 설정 파일 구성
7. YOLO Object Detection 학습 진행

---
### 5. 교과 8 연결 흐름

```text
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
```