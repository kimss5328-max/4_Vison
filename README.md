# 조각김치 이물검출 라벨링 툴

## 1. 프로젝트 소개

조각김치 이미지 900장과 기존 YOLO TXT를 불러와 BBox와 Class를 확인·수정하고, 검수가 끝난 최종 학습 데이터를 만드는 Tkinter 기반 라벨링 프로그램이다.

- 대상: 조각김치 이미지 900장 (JPG) + YOLO Detection TXT 900개
- 클래스: 7개 (Class 0~6, 현재 사용은 6개)
- 최종 목표: 교과 8 객체검출 모델 학습에 바로 사용할 수 있는 검수 완료 YOLO 데이터셋

---

## 2. 주요 기능

- 이미지 폴더 열기, 이미지 목록 표시
- 같은 이름의 기존 YOLO TXT 자동 불러오기
- 기존 BBox와 Class 표시
- BBox 추가 / 수정 / 삭제
- Class 지정 및 변경
- 이전 / 다음 이미지 이동, 저장, 저장 후 다음
- 확대 / 축소 / 원상태
- YOLO TXT 저장 및 다시 불러오기, 저장 유실 방지
- 진행률 표시
- 작업 단계 기록 (1차 / 2차 / review / final), 작업자·검수자 정보
- REVIEW 사유 지정 및 이슈 노트
- Validation (자동 오류 검증)
- 저장 시 Dataset Manifest(CSV) 기록

---

## 3. 프로젝트 폴더 구조

```text
4_Vison/
├── main.py                  
├── app.py                   
├── requirements.txt         
├── README.md
├── .gitignore
│
├── src/                         
│   ├── bbox/                
│   ├── ui/                  
│   ├── validation/        
│   ├── yolo/              
│   ├── __init__.py         
│   ├── app.py            
│   └── config.py                     
│
├── data/       
│   ├── dataset1_result/ #작업폴더명_result #work폴더            
│   ├── dataset2_result/ #작업폴더명_result #work폴더     
│   ├── final/      
│   └── raw/   
│
├── manifests/  
│   └── dataset_manifest.csv
│   
├── reviews/      
│
├── docs/       
│   ├── assets/
│   ├── project_baseline.md
│   ├── class_guide.md
│   ├── bbox_guide.md
│   └── subject08_handoff.md
│
└── reports/     
    ├── qa_summary.md
    └── test_report.md
```

---

## 4. 설치 및 실행 방법

### 필요한 환경

- Python 3.10 이상
- Tkinter (Windows Python에는 기본 포함)
- Pillow 등 `requirements.txt`에 적힌 패키지

### 4-1. 가져오기

```bash
git clone https://github.com/kimss5328-max/4_Vison.git
cd 4_Vison
```

### 4-2. 가상환경 만들기

```bash
python -m venv .venv
```

가상환경 켜기:

| 환경 | 명령어 |
|---|---|
| Linux / WSL (Ubuntu) | `source .venv/bin/activate` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |

PowerShell에서 "스크립트를 실행할 수 없습니다" 오류가 나면 켜지 않고 가상환경의 Python을 직접 실행해도 된다.

```powershell
.venv\Scripts\python.exe main.py
```

### 4-3. 패키지 설치

```bash
pip install -r requirements.txt
```

Linux / WSL(Ubuntu)에서는 Tkinter와 한글 폰트가 필요하다.

```bash
sudo apt install -y python3-tk fonts-nanum
```

### 4-4. 실행

```bash
python main.py
```

프로그램이 실행되면 작업할 이미지 폴더를 선택한다.

> Ubuntu(WSL)에서 창이 뜨려면 Windows 11 + WSLg가 필요하다. 창이 안 뜨면 Windows에서 직접 실행한다.

---

## 5. 기본 사용 순서

1. 이미지 폴더를 연다.
2. 이미지와 기존 YOLO TXT가 자동으로 불러와지는지 확인한다.
3. 기존 BBox와 Class를 확인한다.
4. 잘못된 BBox나 Class는 수정하고, 빠진 객체는 추가하고, 잘못 들어간 객체는 삭제한다.
5. 판단이 어려우면 임의로 정하지 않고 이슈 노트에 사유를 적는다.
6. 작업 단계와 작업자 정보를 입력한다.
7. 저장한다. (저장 시 Manifest에 기록된다.)
8. 다음 이미지로 이동했다가 돌아와서 수정한 BBox가 그대로 복원되는지 확인한다.
9. Validation을 실행한다.

---

## 6. YOLO Label 형식

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

---
## 7. Class 설정

| ID  | 이름          | 사용                                                  |
| --- | ----------- | --------------------------------------------------- |
| 0   | 나뭇잎·종이류     | 사용                                                  |
| 1   | 플라스틱류·돌·금속류 | 사용                                                  |
| 2   | 나뭇가지류       | 사용                                                  |
| 3   | 벌레류         | 사용                                                  |
| 4   | 고무장갑        | **사용하지 않음** (기존 TXT에서 발견되면 임의로 삭제하지 않고 `review` 처리) |
| 5   | 병해·갈변       | 사용                                                  |
| 6   | 파·고추        | 사용                                                  |

클래스별 판단 기준은 [Class 가이드](docs/class_guide.md)를 확인한다.

---
## 8. BBox 작업 기준

모든 클래스에 공통으로 적용되는 바운딩박스(BBox) 작성 규칙이다.

본 프로젝트의 BBox는 **객체의 실제 외곽선에 밀착하되, 외곽이 잘리지 않도록 2~4px의 최소 여백을 두는 Tight Box를 기본 원칙으로 한다.**

### 핵심 원칙

- 객체 외곽선과 BBox 사이에 **2~4px의 최소 여백을 둔다.**
- 기본 여백은 **2~4px**을 원칙으로 한다.
- 객체의 실제 외곽이 BBox 밖으로 잘리지 않도록 하되, 여백은 4px를 넘기지 않는다.
- 객체와 관계없는 배경이 BBox에 과도하게 포함되지 않도록 한다.
- 하나의 BBox에는 원칙적으로 하나의 객체만 포함한다.
- 판단이 어려운 경우 임의로 처리하지 않고 **REVIEW**로 분류한다.
 
BBox별 판단 기준은 [BBox 가이드](docs/bbox_guide.md)를 확인한다.

---
## 9. 작업 단계와 데이터 저장 위치

Class / BBox / Manifest / QA / Test 문서 위치가 안내되어 있다.

| 단계      | 설명               | 저장 위치         |
| ------- | ---------------- | ------------- |
| raw     | 원본 (수정 금지)       | `data/raw/`   |
| 1차 / 2차 | 라벨 작업과 교차검수      | `data/work/`  |
| review  | 판단이 어려운 건의 최종 판단 | `data/issues` |
| final   | 최종 QA 완료 데이터     | `data/final/` |

### Dataset Manifest

`manifests/` 폴더의 CSV에 저장할 때마다 한 줄씩 작업 이력이 추가된다. 900장의 작업상태를 확인할 수 있습니다.

| 항목               | 의미                                  | 예시                                                                   |
| ---------------- | ----------------------------------- | -------------------------------------------------------------------- |
| `file_name`      | 이미지 파일명                             | `250410_144403911987.jpg`                                            |
| `source_dataset` | 이미지가 온 출처                           | `raw`                                                                |
| `original_split` | 기존 train / validation 구분 (없으면 비워 둠) | `train`, `validation`                                                |
| `scene_type`     | 이미지 전체 장면 유형                        | `kimchi_with_target`, `normal_kimchi`, `object_only`, `other_review` |
| `worker`         | 작업자                                 | `4`                                                                  |
| `status`         | 작업 상태                               | `DONE`,  `EDIT`, `REVIEW`                                            |
| `qa_status`      | QA 진행 상태                            | `WAIT`                                                               |
| `review_reason`  | REVIEW 사유 (REVIEW가 아니면 비워 둠)        | `class_ambiguous`, `bbox_boundary_ambiguous`                         |

같은 이미지를 여러 번 저장하면 행이 여러 개 생긴다. 이미지별 현재 상태는 가장 최근 행으로 판단한다.

Dataset Manifest 작업 이력은 [Dataset Manifest](manifests/dataset_manifest.csv) 을 확인한다.

---

## 10. 문서

| 문서                                           | 내용                               |
| -------------------------------------------- | -------------------------------- |
| [Project Baseline](docs/project_baseline.md) | 프로젝트 기준, 데이터 운영 원칙, 검수 체계, 완료 기준 |
| [Class 기준서](docs/class_guide.md)             | 클래스별 포함 / 제외 / 애매한 경우            |
| [BBox 기준서](docs/bbox_guide.md)               | BBox 작성 규칙                       |
| [QA Summary](reports/qa_summary.md)          | 라벨 데이터 품질 검사 결과                  |
| [Test Report](reports/test_report.md)        | 프로그램 기능 테스트 결과                   |

---

## 11. QA 결과

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

---
## 12. FINAL Dataset

최종 QA가 완료된 데이터는 다음 위치에 정리합니다.

```text
data/final/
├── images/
└── labels/
```

FINAL 데이터는 교과 8 Object Detection 학습에 사용합니다.

---
## 13. 데이터 보안 및 주의사항

- data/raw/ 원본은 수정하지 않습니다.
- 실제 JPG와 TXT 전체 데이터는 GitHub에 업로드하지 않습니다.
- REVIEW 상태의 데이터는 FINAL에 포함하지 않습니다.
- 이미지와 TXT의 기본 파일명은 동일해야 합니다.
- 수정 후 반드시 저장과 Reload를 확인합니다.
- 최종 제출 전 Validation을 실행합니다.


