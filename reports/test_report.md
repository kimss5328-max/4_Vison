---
title: Test Report
project: 조각김치 이물검출 라벨링 프로젝트 (교과 7)
type: Report
status: 양식 작성 (테스트 후 값 입력)
created: 2026-10-08
updated: 2026-10-08
---

# Labeling Tool Test Report

팀에서 만든 라벨링 프로그램이 실제 900장 작업에 사용해도 문제가 없는지 단계별로 시험한 결과를 기록하는 문서다.

> `==입력 필요==` 표시는 테스트를 마친 뒤 실제 값으로 채운다. 다 채운 뒤에는 이 안내와 `==입력 필요==`가 남아 있지 않은지 확인한다.

이 문서는 다음 질문에 답한다.

- 이미지가 정상적으로 열리는가?
- 기존 YOLO TXT가 정상적으로 불러와지는가?
- BBox를 추가·수정·삭제할 수 있는가?
- 저장한 뒤 다시 열어도 같은 위치에 복원되는가?
- Zoom/Pan을 사용해도 좌표가 틀어지지 않는가?
- Validation이 정상적으로 동작하는가?

## 테스트 진행 순서

기능 검증은 작은 범위에서 시작해 전체로 넓혀 간다.

```text
기능 확인 → 1장 End-to-End → Golden Test → Pilot Test → 전체 Validation → Final Acceptance Test
```

| 단계                       | 대상            | 목적                               | 결과   |
| ------------------------ | ------------- | -------------------------------- | ---- |
| 1. Golden Test           | 실제 데이터 약 20장  | 핵심 기능이 연결되어 있는지 확인               | DONE |
| 2. Pilot Test            | 실제 데이터 20~50장 | 작업 흐름 전체가 안정적인지 확인               | DONE |
| 3. Final Acceptance Test | 900장 전체       | 프로그램과 FINAL 데이터를 최종 인정할 수 있는지 확인 | DONE |

---

## 1. Golden Test

### 테스트 목적

900장 전체 작업을 시작하기 전에 핵심 기능이 정상적으로 동작하는지 소수의 실제 데이터로 먼저 확인한다. 여기서 오류가 나면 900장 작업을 시작하지 않고 프로그램을 먼저 수정한다.

```text
이미지 Load → YOLO TXT Load → BBox 표시 → BBox 수정 → 저장 → Reload → Validation
```

### 테스트 데이터

- 실제 조각김치 이미지: 30장
- 실제 YOLO TXT: 30개
- 테스트 일자 / 담당자: 2026-10-02 / 김도은

### 테스트 결과

| 테스트 항목           | 결과   | 비고  |     |
| ---------------- | ---- | --- | --- |
| 이미지 열기           | PASS |     |     |
| 기존 YOLO TXT Load | PASS |     |     |
| 기존 BBox 표시       | PASS |     |     |
| BBox 추가          | PASS |     |     |
| BBox 수정          | PASS |     |     |
| BBox 삭제          | PASS |     |     |
| Class 변경         | PASS |     |     |
| Zoom             | PASS |     |     |
| Pan              | PASS |     |     |
| YOLO TXT 저장      | PASS |     |     |
| 저장 후 Reload      | PASS |     |     |
| Validation       | PASS |     |     |

최종 결과: PASS

---

## 2. Pilot Test

### 테스트 목적

Golden Test가 통과했더라도 바로 900장을 작업하지 않는다. 더 많은 실제 데이터로 작업 흐름 전체를 한 번 더 시험해서 프로그램이 안정적으로 동작하는지 확인한다.

처음부터 전부 PASS가 나오는 것이 중요한 게 아니다. 오류를 발견하고 수정한 과정까지 이 문서에 남기는 것이 중요하다.

### 테스트 데이터

- 실제 조각김치 이미지: 50장 (20~50장)
- 실제 YOLO TXT: 50개
- 테스트 일자 / 담당자: 2026-10-06 / 김도은

### 최초 결과

| 판정   | 장수  |
| ---- | --- |
| PASS | 50  |
| FAIL | 0   |

### 발견된 문제

FAIL이 나온 건마다 아래 양식으로 기록한다. 문제가 없으면 "FAIL 없음"이라고 적는다.

#### FAIL-01

| 항목  | 내용                                                       |
| --- | -------------------------------------------------------- |
| 문제  | Zoom/Pan 오류, Class 4 예외처리 없음                             |
| 원인  | Zoom/Pan 확대 시 user 편의성을 고려하지 않음. Class 4 예외처리로 안감.       |
| 조치  | Zoom/Pan Wheel 기능 추가, 버튼 기능 수정 / Class 4 검증상태&검증사유로 예외처리 |
| 재시험 | PASS                                                     |


### Pilot 최종 결과

| 판정   | 장수  |
| ---- | --- |
| PASS | 50  |
| FAIL | 0   |

---

## 3. Final Acceptance Test

### 테스트 목적

900장 전체 검수 작업이 끝난 뒤, 프로그램과 FINAL 데이터를 최종 산출물로 인정해도 되는지 확인한다.

```text
900장 작업 완료 → Critical Error 확인 → 미처리 REVIEW 확인 → Validation 확인 → 저장 / Reload 확인 → ACCEPTED
```

### Critical Error란

프로젝트 진행에 치명적인 문제를 말한다. 아래와 같은 문제가 0건이어야 한다.

- 저장이 되지 않음
- TXT가 손상됨
- 저장 후 BBox 위치가 달라짐
- 이미지와 TXT Pair가 깨짐
- 프로그램이 반복적으로 종료됨

### 확인 항목

| 확인 항목             | 결과   |
| ----------------- | ---- |
| 900장 이미지 탐색 가능    | PASS |
| 이미지와 TXT Pair 정상  | PASS |
| 저장 후 Reload 정상    | PASS |
| 미처리 REVIEW 없음     | PASS |
| Critical Error 없음 | PASS |
| Validation 오류 없음  | PASS |

### 최종 결과

| 항목                | 결과   |
| ----------------- | ---- |
| 전체 대상             | 800장 |
| Critical Error    | 0건   |
| Unresolved Review | 171건 |
| Validation Error  | 0건   |

최종 판정: ACCEPTED

---

## 참고 문서

- [Project Baseline](../docs/project_baseline.md)
- [BBox 기준서](../docs/bbox_guide.md)
- [QA Summary](qa_summary(도은님%20제출완료).md)
- [교과 8 Handoff](../docs/subject08_handoff.md)

---

## 변경 이력

| 날짜 | 작성자 | 변경 내용 |
|---|---|---|
| 2026-10-08 | 권지현 | Test Report 양식 작성 |
