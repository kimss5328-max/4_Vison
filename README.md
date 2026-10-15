# 조각김치 이물검출 프로젝트 (교과 7 & 교과 8 통합 저장소)

본 저장소는 **교과 7 (조각김치 이물검출 라벨링 프로그램)**과 **교과 8 (Vision 기반 객체검출 모듈)**의 수행 프로그램을 최상위 폴더별로 명확히 분리하여 구성한 프로젝트입니다.

---

## 1. 전체 파이프라인 구조

```text
[교과 7: subject7_kimchi_labeling]
  - 조각김치 이미지 900장 BBox / Class 라벨링 및 검수
  - 자동 검사(Validation) 및 검수 단계 워크플로우 (pass / edited / review / final)
  - 최종 검수 승인 완료 데이터셋 추출 (data/final: JPG 900장 + TXT 900개)
                  │
                  ▼ (Handoff)
[교과 8: subject8_kimchi_detection]
  - 교과 7 FINAL 데이터 수령 및 층화 분할 (Train 600 / Val 100 / Test 100 / Holdout 100)
  - Split Freeze 검증 (split_manifest.csv)
  - YOLO11n Baseline 모델 학습 (1920 해상도, 100 epochs, seed 0)
  - Validation 평가 및 오검출/미검출 실패분석 (Failure Analysis)
  - 개선 실험 및 최종 모델 선정
```

---

## 2. 최상위 디렉토리 안내

| 디렉토리 | 교과 | 내용 | 실행 진입점 |
|---|---|---|---|
| [`subject7_kimchi_labeling/`](subject7_kimchi_labeling/) | **교과 7** | Tkinter 기반 조각김치 이물 라벨링 및 검수 도구 | `python main.py` |
| [`subject8_kimchi_detection/`](subject8_kimchi_detection/) | **교과 8** | Ultralytics YOLO11 기반 이물 객체검출 모듈 | `python scripts/06_train_baseline.py` |

---

## 3. 교과별 빠른 시작 (Quick Start)

### 3-1. [교과 7] 조각김치 라벨링 프로그램 실행

```bash
cd subject7_kimchi_labeling
pip install -r requirements.txt
python main.py
```
* 상세 사용법 및 산출물 안내: [`subject7_kimchi_labeling/README.md`](subject7_kimchi_labeling/README.md)

### 3-2. [교과 8] YOLO11 객체검출 학습 및 평가

```bash
cd subject8_kimchi_detection
pip install -r requirements.txt

# 1. Split Freeze 검증
python scripts/01_build_split.py --freeze-only

# 2. Baseline 모델 학습 (WSL/GPU 환경 권장)
python -u scripts/06_train_baseline.py 2>&1 | tee runs/baseline_v1.log

# 3. Validation 평가
python scripts/06_evaluate.py
```
* 상세 실행 스크립트 및 모델 지표: [`subject8_kimchi_detection/README.md`](subject8_kimchi_detection/README.md)

---

## 4. 데이터 보안 및 NDA 지침

* 기업 제공 원본 데이터셋(`.jpg`, `.png`, `.txt`), 학습 가중치(`.pt`), 시각화 결과물은 보안 및 NDA 규정에 따라 Git 추적에서 제외됩니다.
* 각 폴더 내 `manifests/` 대장 및 `reports/` 문서에는 수치, 통계, 분석 내용만 기록됩니다.
