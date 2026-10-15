# Split Policy

- 기준: 교과8 수행가이드 11 (Dataset Split) · 15.A (Split 정책) · 16.8 (산출물 1 완료 확인)
- Dataset Version: **kimchi_v1** (labels sha256 앞 12자리 — train `57f0bf5121e4` / val `ab6cc7f98da7`)
- 분할 도구: `tools/build_split.py` · 실행 기록 `reports/logs/build_split/build_split_20261013_111107.md`
- 수량 검사: `src/dataset_audit.py` → `reports/dataset_summary.csv` (Split Role 600 / 100 / 100 / 100 = 900 · PASS)

## 1. 입력 데이터

교과7 결과를 `tools/export_final.py` 로 모은 `data/final` 900장 (JPG 900 / YOLO TXT 900).

| 분류 (`split_manifest.csv` 의 `group` 열) | 장 | 내용 |
|---|---|---|
| pool | 689 | pass·edited 를 거쳐 final 승인 |
| review | 40 | review 를 거쳐 final 승인 |
| excluded | 171 | 교과7 결과 폴더 final 단계에 없음 (아래 4절) |
| 합계 | 900 | 팀 회의 결정으로 900장 전체 사용 |

- 원본은 프로젝트 밖(`~/exe_01/이물검출_학습데이터1`, `이물검출_학습데이터2`)에 있어 원본 ↔ final 자동 비교는 생략. 900장 전체는 학습 폴더 기준으로 수량·짝·역할 겹침을 검사함 (`src/dataset_audit.py`)

## 2. 네 역할과 분할 방법

| 역할 | 장 | 사용 | 위치 |
|---|---|---|---|
| Train | 600 | 학습 | `data/yolo/{images,labels}/train` |
| Validation | 100 | Baseline · 개선 실험 비교 | `data/yolo/{images,labels}/val` |
| Frozen Test | 100 | Final Model 선택 후 1회 평가 (21) | `data/yolo/{images,labels}/test` |
| Bridge Holdout | 100 | 교과 14 보존 — 교과 8 학습·튜닝·선택·평가에 사용하지 않음 | `data/bridge_holdout/{images,labels}` · `dataset.yaml` 에 없음 |

- 방법: 이미지마다 대표 클래스(`primary_class` — 그 이미지 안에서 가장 드문 클래스)를 정하고, 대표 클래스별로 같은 비율이 되도록 층화 분할
- seed: 42 (`tools/build_split.py --seed 42`) · 학습 seed(0)와는 별개
- 결과 (클래스별 이미지 수 — 그 클래스 박스가 있는 이미지)

| 클래스 | train | val | test | holdout | 합계 (장 / 박스) |
|---|---|---|---|---|---|
| 0: 나뭇잎·종이류 | 192 | 32 | 36 | 43 | 303 / 745 |
| 1: 플라스틱·돌·금속류 | 355 | 57 | 65 | 65 | 542 / 1581 |
| 2: 나뭇가지류 | 232 | 41 | 48 | 43 | 364 / 880 |
| 3: 벌레류 | 131 | 22 | 24 | 19 | 196 / 378 |
| 4: 고무장갑 | 100 | 16 | 17 | 19 | 152 / 283 |
| 5: 병해·갈변 | 98 | 16 | 16 | 16 | 146 / 316 |
| 6: 파·고추 | 33 | 6 | 6 | 5 | 50 / 250 |

- 모든 역할에 7개 클래스가 모두 있음 · 빈 라벨 이미지 0장 (정상 김치 Negative Sample 없음 → 정상 김치 FP는 평가 불가)

| 분류 | train | val | test | holdout |
|---|---|---|---|---|
| pool | 458 | 77 | 78 | 76 |
| review | 29 | 4 | 3 | 4 |
| excluded | 113 | 19 | 19 | 20 |

## 3. Split Freeze (11.5)

| 항목 | 값 |
|---|---|
| Freeze 시점 | 2026-10-13 11:11:07 (`build_split_20261013_111107.md`) · commit `1b074fa` |
| `manifests/train.csv` | sha256 `8b9e6b7c4644` |
| `manifests/val.csv` | sha256 `eabbaa9b8f3a` |
| 함께 고정 | `split_manifest.csv` · `test.csv` · `bridge_holdout.csv` · `configs/dataset.yaml` |

- 이후 `build_split.py` 는 기존 배정을 재사용함. `--force`(새로 나누기) 는 사용하지 않음
- 라벨을 고치고 `export_final` 을 다시 하면 배정은 유지되지만 라벨이 바뀜 → 새 Dataset Version(kimchi_v2)으로 기록하고 Baseline과 직접 비교하지 않음

## 4. excluded 171장

교과7 결과 폴더 final 단계에 없는 이미지. 팀 회의 결정(900장 전체 사용)에 따라 포함.

| 구성 | 장 | 내용 |
|---|---|---|
| Class 4(고무장갑) 포함 | 152 | 고무장갑 이슈로 이슈노트 작성 후 학습 데이터로 넘긴 이미지 · Class 4 이미지 전체(152장)와 같음 |
| REVIEW · QA 대기 | 19 | `status=REVIEW`, `qa_status=WAIT` · 사유 `other` 13 · `class_ambiguous` 6 |

REVIEW · QA 대기 19장의 역할

| 역할 | 장 | 이미지 (사유) | 처리 |
|---|---|---|---|
| train | 13 | — | 학습에만 사용 |
| val | 3 | `250424_131927234268` (other) · `250424_142806480763` (class_ambiguous) · `250513_015923922984` (other) | Baseline Validation 지표에 포함됨. 6일차 Failure Analysis에서 "검수 대기 라벨"로 따로 표시 · `250424_142806480763` 은 실패 후보(`reports/failure_candidates.csv`) |
| test | 2 | `250410_181811462137` (class_ambiguous) · `250424_142938362989` (other) | Frozen Test 이전에 열람하지 않음. Final 평가 결과 해석 때 함께 기록 (21) |
| holdout | 1 | `250424_142451194734` (other) | 교과 14 인계 문서에 표시 |

## 5. Class 4 (고무장갑)

- 교과7 중간에 삭제했다가 팀 회의 결정으로 다시 사용 (Class ID 4 유지)
- 7클래스(`nc: 7`)로 학습 · 152장 / 283박스
- 가이드 15.1 예시의 `CLASS4_REVIEW` 표시는 사용하지 않음

## 6. Data Leakage 확인 (11.4 · 15.3)

| 확인 | 결과 | 방법 |
|---|---|---|
| 같은 파일 중복 | 0건 | 900장 파일 SHA-256 |
| 같은 이미지(픽셀) 중복 | 0건 | 900장 픽셀 SHA-256 |
| 같은 파일 이름이 두 역할에 | 0건 | `src/dataset_audit.py` `ROLE_OVERLAP` |
| Smoke 표본과 Test · Holdout 겹침 | 0장 | Smoke는 본 분할의 train 600장에서만 추출 (`build_split.py` v4) |
| Bridge Holdout 이 `dataset.yaml` 에 없음 | 확인 | `configs/dataset.yaml` |
| **capture_group (연속 촬영 · 유사 장면)** | **미확인** | `split_manifest.csv` 의 `group` 열은 검수 상태(pool/review/excluded)이며 촬영 묶음이 아님. capture_group 정보가 없음 |

- 촬영 묶음 기준 시간: **(공란)** — 파일 이름의 시간 정보(`YYMMDD_HHMMSS…`)가 촬영 묶음을 뜻하는지 확인된 바가 없음. 가이드 15.3에 따라 시간 문자열을 임의로 촬영 묶음으로 단정하지 않음
- 따라서 연속 촬영 · 유사 장면 누수는 확인하지 못한 상태로 둠. Validation · Frozen Test 결과를 해석할 때 이 한계를 함께 기록함 (분할은 Freeze 유지)

## 7. Smoke 분할

- 본 분할의 train 600장에서만 50장 추출 (35 / 10 / 5) · seed 42 · `configs/smoke_dataset.yaml`
- Frozen Test · Bridge Holdout 사용하지 않음 (16.8)
