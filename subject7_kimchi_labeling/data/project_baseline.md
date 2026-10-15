---
title: Project Baseline
project: 조각김치 이물검출 라벨링 프로젝트 (교과 7)
type: Baseline
status: 검토중
created: 2026-10-02
updated: 2026-10-08
---

# Project Baseline — 조각김치 이물검출 라벨링 프로젝트 (교과 7)

## 개요
900장 조각김치 이미지에서 이물질을 7개 클래스(0~6)로 YOLO 포맷 라벨링(보정 포함)하는 프로젝트의 공통 기준 문서. 팀 전원이 이 기준에 합의한 뒤 작업을 시작한다.

## 1. 프로젝트 기본 정보

| 항목                  | 내용                                                                   | 비고                                      |
| ------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| 프로젝트명               | 조각김치 이물검출 라벨링 프로젝트 (교과 7)                                            |                                         |
| 목표                  | 900장 조각김치 이미지에서 이물질을 7개 클래스(0~6)로 YOLO 포맷 라벨링·보정작업                   | 900장의 이미지는 사람이 확인해야 하며, 필요한 경우에만 라벨을 보정 |
| 범위 (In-Scope)       | 이미지 라벨링, 바운딩박스 작성, 상호검수, 라벨링 툴(Tkinter) 사용                           |                                         |
| 범위 (Out-of-Scope)   | 모델 학습·추론은 교과 8 이후 범위                                                 |                                         |
| 화면 구성               | 아래 "4. 화면 구성" 참고                                                     |                                         |
| MVP 기능              | 아래 "5. 기능 범위" 참고 (Must Have 18개)                                     |                                         |
| Git URL             | https://github.com/kimss5328-max/4_Vison.git                         |                                         |
| Git 기준              | feat: 기능 진행 및 오류 검증 로직 구현                                            |                                         |
| 완료 조건 (DoD)         | 900장 전수 라벨링 완료 + 상호검수 통과 + Dataset Manifest 100% 업데이트                |                                         |
| 팀 구성 (5명)           | 김성섭 / 김동윤 / 김도은 / 김주한 / 권지현                                          |                                         |
| 역할 분담 개요            | GUI 김동윤 / UX 김주한 / QA, PM 김성섭 / YOLO학습 김도은 / DOC 권지현                 |                                         |
| 라벨 작업 기준            | 아래 "6. 라벨 작업 기준" 참고                                                  |                                         |
| 일정 개요 (5일)          | 1일차 기준 수립 / 2~3일차 라벨링 / 3일차 Pilot Test / 4~5일차 QA·교차검수 / 5일차 Handoff |                                         |
| 클래스 수               | 7개 (클래스 0~6)                                                         | 상세 정의는 [[2. Class-기준서 1]] 참고            |
| Dataset Manifest 항목 | 아래 "7. Dataset Manifest 항목" 참고                                       |                                         |

## 2. 데이터 운영 원칙

| 항목                  | 내용                                      |
| ------------------- | --------------------------------------- |
| 데이터 수량              | JPG 900장 + YOLO TXT 900개                |
| 데이터 출처 관리           | Dataset 1 / Dataset 2의 출처 정보 유지         |
| Train/Validation 구분 | 기존 train / validation 구분 유지             |
| 이미지 삭제 금지           | 정상 김치·대상 객체 단독 이미지도 임의 삭제하지 않음          |
| 라벨 포맷               | YOLO Detection TXT 사용                   |
| 클래스 ID              | Class ID 0~6 유지                         |
| RAW 데이터             | RAW 수정 금지                               |
| 작업 데이터(WORK)        | WORK > 1차/2차                            |
| FINAL 기준            | 1/2차 검수 완료, REVIEW에서 최종 검수 완료           |
| BBox 관리 기준          | 원본 이미지 기준으로 BBox 관리                     |
| 검증 절차               | 자동 Validation + Human QA + Cross Review |
| 데이터 인계              | 최종 데이터는 교과 8로 인계                        |

### 3. 화면 구성 (확정된 와이어프레임)

- **상단**: 진행률 = (완성된 파일양) / (전체 파일양)
- **좌측**: 사이드바 on/off, 폴더분류란, 폴더내 이미지 목록
- **중앙**: 이미지 작업 영역
- **중앙 하단**: 원상태 / 확대 / 축소 / 삭제
- **우측 상단**: 클래스 분류, 클래스 크기 정보
- **우측 중단**: 자동 라벨링(YOLO), 작업이력, 검수 상태, 작업자 정보, Scene Type / REVIEW 사유, 이슈 노트
- 우측 하단 : 이전 / 다음 / 저장 / 저장 후 다음

![화면구성 이미지](../assets/program_screen.png)

## 4. 기능 범위 (Must Have)

| 구분        | 기능                              | 진행상태/비고 |
| --------- | ------------------------------- | ------- |
| Must Have | 이미지 표시                          | ㅇ       |
| Must Have | 이전/다음                           | ㅇ       |
| Must Have | 기존 TXT Load                     | ㅇ       |
| Must Have | 기존 BBox 표시                      | ㅇ       |
| Must Have | 새 BBox 작성                       | ㅇ       |
| Must Have | Class 지정·변경                     | ㅇ       |
| Must Have | BBox 삭제                         | ㅇ       |
| Must Have | 다중 BBox                         | ㅇ       |
| Must Have | Zoom/Pan                        | ㅇ       |
| Must Have | YOLO Save/Reload                | ㅇ       |
| Must Have | 저장 유실 방지                        | ㅇ       |
| Must Have | 작업상태                            | ㅇ       |
| Must Have | Validation                      | ㅇ       |
| Must Have | 진행률 표시                          | ㅇ       |
| Must Have | 이미지 목록                          | ㅇ       |
| Must Have | 클래스별 분류 현황 (분류내역/클래스분류/라벨분류 통합) | ㅇ       |
| Must Have | 이슈 노트 (클래스 추가 요청)               | ㅇ       |
| Must Have | CSV 저장 정보                       | ㅇ       |

## 5. 라벨 작업 기준
#### 검수 체계

| 단계                      | 담당자           | 비고                    |
| ----------------------- | ------------- | --------------------- |
| 1차 라벨 검수                | 김성섭, 김도은, 권지현 | 라벨링 결과를 처음 확인         |
| 교차검수(2차 라벨 검수)          | 김도은, 김동윤      | 교차검수자가 2차 검수와 QA를 진행. |
| REVIEW 최종 판단 (Reviewer) | 김성섭           | 판단이 어려운 건을 최종 결정      |

#### 데이터 저장 위치

| 구분           | 폴더 경로                                              | 비고           |
| ------------ | -------------------------------------------------- | ------------ |
| 작업 중 데이터     | `data/dataset1_result/`<br>`data/dataset2_result/` | 라벨링 작업 중인 파일 |
| 최종 QA 완료 데이터 | `data/final/`                                      | QA를 통과한 최종본  |

## 6. Dataset Manifest

#### Dataset Manifest 예시

```text
file_name,source_dataset,original_split,scene_type,worker,status,qa_status,review_reason

250410_144532010108.jpg,raw,,kimchi_with_target,4,DONE,WAIT,
250410_145141723860.jpg,raw,,kimchi_with_target,4,DONE,WAIT,
250410_145433197807.jpg,raw,,kimchi_with_target,4,DONE,WAIT,
250410_171526553647.jpg,raw,,other_review,4,REVIEW,WAIT,other
250410_172417911438.jpg,raw,,kimchi_with_target,4,REVIEW,WAIT,other
250410_172828996170.jpg,raw,,other_review,4,DONE,WAIT,other
250410_173557486868.jpg,raw,,kimchi_with_target,4,DONE,WAIT,other
250410_174950640074.jpg,raw,,kimchi_with_target,4,DONE,WAIT,
250410_175133040999.jpg,raw,,kimchi_with_target,4,DONE,WAIT,
250410_175310273550.jpg,raw,,kimchi_with_target,4,EDITED,WAIT,
250410_175613332662.jpg,raw,,kimchi_with_target,4,EDITED,WAIT,
```

#### Dataset Manifest 항목

| 항목               | 의미                                  | 예시                                                                   |
| ---------------- | ----------------------------------- | -------------------------------------------------------------------- |
| `file_name`      | 이미지 파일명                             | `250410_144403911987.jpg`                                            |
| `source_dataset` | 이미지가 온 출처                           | `raw`                                                                |
| `original_split` | 기존 train / validation 구분 (없으면 비워 둠) | `train`, `validation`                                                |
| `scene_type`     | 이미지 전체 장면 유형                        | `kimchi_with_target`, `normal_kimchi`, `object_only`, `other_review` |
| `worker`         | 작업자                                 | `1` : 파이널 검수자 `2` : QA 작업자 `3` : 김도은 작업자 `4` : 권지현 작업자 `5` : 김성섭     |
| `status`         | 작업 상태                               | `DONE`,  `EDIT`, `REVIEW`                                            |
| `qa_status`      | QA 진행 상태                            | `WAIT`                                                               |
| `review_reason`  | REVIEW 사유 (REVIEW가 아니면 비워 둠)        | `class_ambiguous`, `bbox_boundary_ambiguous`                         |

## 7. 완료 기준

| #   | 완료 기준            | 목표          | 확인 방법                                    | 완료      |
| --- | ---------------- | ----------- | ---------------------------------------- | ------- |
| 1   | 미처리 REVIEW       | **0건**      | Issue 기록 탭에서 상태가 미해결인 건 수 확인             | 0건      |
| 2   | Validation 오류    | **0건**      | Validation 실행 결과의 오류 건수 확인               | 0건      |
| 3   | 이미지와 TXT Pair 확인 | 완료          | 이미지 900장 ↔ TXT 900개 파일명이 1:1로 일치하는지 확인   | 완료      |
| 4   | 전체 검수            | **900장 완료** | Dataset Manifest의 검수 상태가 900장 모두 완료인지 확인 | 900장 완료 |
| 5   | FINAL 데이터 정리     | 완료          | `final` 폴더에 최종 이미지와 TXT가 정리돼 있는지 확인      | 완료      |

## 참고 문서

- [Class 가이드](class_guide.md)
- [BBox 가이드](bbox_guide.md)

## 변경 이력
| 날짜         | 작성자 | 변경 내용                                     |
| ---------- | --- | ----------------------------------------- |
| 2026-10-02 | 권지현 | 최초 작성 (Google Sheet → md 변환)              |
| 2026-10-07 | 권지현 | 화면 구성 수정 / Git, 완료 기준 추가 / 라벨 작업 기준       |
| 2026-10-08 | 권지현 | 화면 구성 / 라벨 작업 기준 / Dataset Manifest 항목 수정 |
