# 교과7 · 교과8 저장소 분리 가이드

- 목적: 하나로 섞여 있는 저장소를 교과7(라벨링)과 교과8(객체검출) 두 프로그램으로 나누고, 폴더 이름을 수행가이드 지정대로 맞춤
- 근거: 교과7 산출물 예시 2절 (`subject7_kimchi_labeling/`) · 교과8 수행가이드 7절 · 7.2 · 8절 (`subject8_kimchi_detection/`)
- 팀 합의: 위치는 두 프로그램을 나란히, Git은 저장소 하나 (최상위 새 폴더 금지 규칙은 이 작업에 한해 변경)
- 시작 브랜치: `feature/7_8` → 작업 브랜치 `feature/split_7_8`
- 원칙: **숫자(Baseline 결과 · Dataset Version)가 하나도 바뀌지 않아야 성공**. 다시 학습하지 않음, 분할 다시 하지 않음

---

## 0. 작업 전에 알아둘 것

| 구분 | 내용 |
|---|---|
| GitHub에 있는 것 | 코드 · 설정 · manifest csv · 문서 (이 가이드의 1~6단계) |
| GitHub에 없는 것 (NDA) | 이미지 · 라벨 txt · Weight(`.pt`) · `runs/` · 그래프 png · 예측 이미지 → **데이터 담당에게 따로 받음** (7단계) |
| 하면 안 되는 것 | `scripts/03_build_split.py --apply` / `--force` 실행 · Baseline 다시 학습 · 이미지나 라벨을 `git add` |
| 막히면 | 그 단계에서 멈추고 출력 결과를 공유. 다음 단계로 넘어가지 않음 |

---

## 1. 목표 구조

```text
~/exe_01/
├── 이물검출_학습데이터1/  이물검출_학습데이터2/      ← 원본. 저장소 밖 (손대지 않음)
└── 4_Vison/                                          ← 저장소 루트
    ├── README.md                                     ← 두 프로그램 안내만
    ├── .gitignore                                    ← 공통 규칙
    │
    ├── subject7_kimchi_labeling/                     ← 교과7
    │   ├── main.py
    │   ├── requirements.txt
    │   ├── README.md                                 ← 기존 README 1~13절
    │   ├── .gitignore
    │   ├── configs/classes.yaml
    │   ├── src/        (app.py · config.py · bbox/ · ui/ · validation/ · yolo/)
    │   ├── tools/      (export_final.py · merge_manifest.py · migrate_result.py)
    │   ├── data/       (raw/ · dataset1_result/ · dataset2_result/ · final/)   ← Git 밖
    │   ├── manifests/dataset_manifest.csv
    │   ├── docs/       (bbox_guide · class_guide · project_baseline · assets/)
    │   ├── reports/    (qa_summary · test_report · subject08_handoff · logs/)
    │   └── handoff_subject08/
    │
    └── subject8_kimchi_detection/                    ← 교과8 (7절 그대로)
        ├── README.md                                 ← 기존 README 14절
        ├── requirements.txt
        ├── .gitignore
        ├── configs/    (dataset.yaml · smoke_dataset.yaml)
        ├── data/       (subject7_final/ · yolo/ · bridge_holdout/ · smoke/ · new_unlabeled/)   ← Git 밖
        ├── manifests/  (split_manifest · train · val · test · bridge_holdout · smoke_split_manifest)
        ├── src/        (__init__.py · dataset_audit.py · train_detector.py)
        ├── scripts/    (03_build_split.py · 06_train_baseline.py)
        ├── models/     (baseline/ · improved/ · final/)   ← Git 밖
        ├── runs/                                         ← Git 밖
        ├── reports/    (baseline_* · dataset_summary · smoke_test · failure_candidates · figures/ · logs/build_split/)
        ├── demo/
        ├── docs/       (split_policy.md)
        └── presentation/
```

- 저장소를 새로 만들지 않고 **`git mv` 로 옮김** → 교과7 커밋 이력(교과7 산출물 2)이 이어짐. 파일별 이력은 `git log --follow <파일>`
- 루트 폴더 이름은 Git과 무관한 로컬 이름. 새로 clone 하면 `4_Vison` 으로 만들어짐

---

## 2. 단계별 진행

### 1단계 — 받기와 브랜치

```bash
cd ~/exe_01
git clone https://github.com/kimss5328-max/4_Vison.git
cd 4_Vison
git switch feature/7_8
git switch -c feature/split_7_8
git ls-files | cut -d/ -f1 | sort | uniq -c        # 최상위 항목별 파일 수 — 2·3단계 분류표와 대조
```

- 이미 clone이 있으면 진행 중인 변경을 먼저 커밋하거나 정리한 뒤 `git pull`

### 2단계 — 교과7 파일 옮기기 (`git mv`)

분류 기준표 — `git ls-files` 결과를 이 표로 나눔

| 지금 위치 | 옮길 곳 |
|---|---|
| `main.py`, `requirements.txt` | `subject7_kimchi_labeling/` |
| `configs/classes.yaml` | `subject7_kimchi_labeling/configs/` |
| `src/app.py`, `src/config.py`, `src/__init__.py`, `src/bbox/`, `src/ui/`, `src/validation/`, `src/yolo/` | `subject7_kimchi_labeling/src/` |
| `tools/export_final.py`, `tools/merge_manifest.py`, `tools/migrate_result.py` | `subject7_kimchi_labeling/tools/` |
| `manifests/dataset_manifest.csv` | `subject7_kimchi_labeling/manifests/` |
| `docs/bbox_guide.md`, `docs/class_guide.md`, `docs/project_baseline.md`, `docs/assets/` | `subject7_kimchi_labeling/docs/` |
| `reports/qa_summary.md`, `reports/test_report.md`, `reports/subject08_handoff.md`, `reports/validation_report.csv`, `reports/assets/` | `subject7_kimchi_labeling/reports/` |
| `handoff_subject08/` | `subject7_kimchi_labeling/` |
| `data/` 아래 `.gitkeep` · `data/*.md` · `reviews/` | `subject7_kimchi_labeling/data/` · `subject7_kimchi_labeling/reviews/` |
| `README.md` | `subject7_kimchi_labeling/README.md` (14절은 4단계에서 떼어냄) |

```bash
mkdir -p subject7_kimchi_labeling/{configs,src,tools,manifests,docs,reports}
git mv main.py requirements.txt subject7_kimchi_labeling/
git mv configs/classes.yaml subject7_kimchi_labeling/configs/
git mv src/app.py src/config.py src/bbox src/ui src/validation src/yolo subject7_kimchi_labeling/src/
# … 표의 나머지도 같은 방식
git status --short | grep -v '^R' | head      # R(이름 변경) 말고 다른 표시가 있으면 확인
git commit -m "refactor: 교과7 라벨링 프로그램을 subject7_kimchi_labeling/ 로 이동 (내용 변경 없음)"
```

- `src/__init__.py` 는 교과7·교과8 둘 다 필요 → 교과7로 `git mv` 하고 교과8은 3단계에서 빈 파일을 새로 만듦
- 표에 없는 파일이 나오면 옮기지 말고 공유

### 3단계 — 교과8 파일 옮기기 (`git mv`)

| 지금 위치 | 옮길 곳 |
|---|---|
| `configs/dataset.yaml`, `configs/smoke_dataset.yaml` | `subject8_kimchi_detection/configs/` |
| `manifests/split_manifest.csv`, `train.csv`, `val.csv`, `test.csv`, `bridge_holdout.csv`, `smoke_split_manifest.csv` | `subject8_kimchi_detection/manifests/` |
| `src/dataset_audit.py`, `src/train_detector.py` | `subject8_kimchi_detection/src/` |
| `tools/build_split.py` | `subject8_kimchi_detection/scripts/03_build_split.py` |
| `tools/06_train_baseline.py` | `subject8_kimchi_detection/scripts/06_train_baseline.py` |
| `reports/baseline_training_condition.md`, `baseline_metrics.csv`, `failure_candidates.csv`, `dataset_summary.csv`, `smoke_test.md`, `reports/logs/build_split/` | `subject8_kimchi_detection/reports/` |
| `docs/split_policy.md`, `docs/restructure_guide.md` (이 문서) | `subject8_kimchi_detection/docs/` |

```bash
mkdir -p subject8_kimchi_detection/{configs,manifests,src,scripts,reports/logs,docs}
git mv configs/dataset.yaml configs/smoke_dataset.yaml subject8_kimchi_detection/configs/
git mv tools/build_split.py subject8_kimchi_detection/scripts/03_build_split.py
git mv tools/06_train_baseline.py subject8_kimchi_detection/scripts/06_train_baseline.py
# … 표의 나머지도 같은 방식
touch subject8_kimchi_detection/src/__init__.py && git add subject8_kimchi_detection/src/__init__.py
mkdir -p subject8_kimchi_detection/{data/{subject7_final,yolo,bridge_holdout,smoke,new_unlabeled},models/{baseline,improved,final},runs,demo/failure_analysis,presentation}
for d in data/subject7_final data/yolo data/bridge_holdout data/smoke data/new_unlabeled models/baseline models/improved models/final demo/failure_analysis presentation; do
  touch subject8_kimchi_detection/$d/.gitkeep; done
git status --short | grep -v '^R' | head
git commit -m "refactor: 교과8 학습 파이프라인을 subject8_kimchi_detection/ 로 이동 (가이드 7절 구조)"
```

- 이 단계가 끝나면 루트에 `configs/ src/ tools/ manifests/ docs/ reports/` 가 비어 있어야 함 (`ls`)

### 4단계 — `.gitignore` 와 README 나누기

`.gitignore` 규칙은 **그 파일이 있는 폴더 기준**으로 동작함. 폴더가 한 단계 내려갔으므로 그대로 두면 이미지·라벨 제외 규칙이 빠질 수 있음 (NDA)

| 파일 | 넣을 규칙 |
|---|---|
| 루트 `.gitignore` | 공통: `*.jpg` `*.jpeg` `*.png` `*.bmp` `*.npy` `*.pt` `*.zip` `*.tar.gz` · `venv/` `__pycache__/` `*.pyc` · `*Zone.Identifier` · `id_*` `*.pem` `*.key` `.env` · `backup/` |
| `subject7_kimchi_labeling/.gitignore` | 기존 `.gitignore` 의 교과7 규칙 (`data/**` + `!data/**/` + `!data/**/.gitkeep`, `reviews/**` 같은 형식, `reports/*` + 교과7 문서 `!` 예외, `이물검출_학습데이터*/`, `*_labeled/` `*_done/`) |
| `subject8_kimchi_detection/.gitignore` | `data/**` + `!data/**/` + `!data/**/.gitkeep` · `models/**` + `!models/**/` + `!models/**/.gitkeep` · `runs/` · `demo/**` + `!demo/**/` + `!demo/**/.gitkeep` · `reports/figures/` · `reports/*` 다음에 교과8 문서 `!` 예외 (`baseline_training_condition.md` `baseline_metrics.csv` `failure_candidates.csv` `dataset_summary.csv` `smoke_test.md` `logs/` `logs/build_split/` 와 그 안의 md 2개) |

- 이미지 문서(`docs/assets/*.png`, `reports/assets/last.png`)는 이미 추적 중이라 `.gitignore` 와 관계없이 계속 올라감 → NDA 확인은 팀 결정 사항으로 따로 처리
- README: 기존 README 의 14절을 잘라 `subject8_kimchi_detection/README.md` 로, 1~13절은 `subject7_kimchi_labeling/README.md`. 루트 `README.md` 는 두 폴더 안내 몇 줄만 새로 작성

```bash
git add .gitignore subject7_kimchi_labeling/.gitignore subject8_kimchi_detection/.gitignore README.md subject*/README.md
git commit -m "chore: .gitignore·README 를 프로그램별로 분리"
```

### 5단계 — 코드 안의 경로 수정

먼저 찾기

```bash
grep -rn "visol04\|/home/\|data/final\|dataset1_result\|dataset2_result\|tools/\|reports/logs" --include=*.py --include=*.yaml subject8_kimchi_detection | head -30
grep -rn "visol04\|/home/" --include=*.py --include=*.yaml --include=*.json subject7_kimchi_labeling | head -20
```

| 파일 | 바꿀 곳 | 바꾸는 이유 |
|---|---|---|
| `subject8…/configs/dataset.yaml`, `smoke_dataset.yaml` | `path:` → `data/yolo` (smoke는 `data/smoke`) | 12절 · 다른 PC에서도 동작. 루트에서 실행할 때 기준 |
| `subject8…/src/dataset_audit.py` | 입력 `data/dataset{n}_result/final` · `manifests/dataset_manifest.csv` · `data/raw/images` → `data/subject7_final/…` | 교과8은 교과7 결과의 **복사본**만 읽음 (7.2) |
| `subject8…/scripts/03_build_split.py` | `data/final` → `data/subject7_final`, `manifests/dataset_manifest.csv` → `data/subject7_final/dataset_manifest.csv`, `REPORT_DIR` 그대로 | 같은 이유. 파일이 `scripts/` 로 왔으므로 `parents[1]` 은 그대로 맞음 |
| `subject8…/scripts/06_train_baseline.py` | 바꿀 것 없음 (`parents[1]` · 상대경로 사용) | — |
| `subject7…/src/config.py` 등 | grep에 걸린 절대경로만 | 폴더가 한 단계 내려감 |
| 문서 (`*.md`) | `tools/build_split.py` → `scripts/03_build_split.py`, `runs/baseline_v1/weights/baseline_best.pt` → `models/baseline/baseline_best.pt` 등 | 9단계에서 한꺼번에 |

```bash
cd subject8_kimchi_detection && python -m py_compile src/*.py scripts/*.py && echo "문법 OK" && cd ..
git commit -am "fix: 분리 후 경로 수정 (dataset.yaml 상대경로, subject7_final 입력)"
```

### 6단계 — 가상환경 다시 만들기

venv 안에는 처음 만든 위치의 절대경로가 들어 있어서 **폴더를 옮기면 동작하지 않음**. 프로그램마다 새로 만듦

```bash
cd ~/exe_01/4_Vison/subject7_kimchi_labeling
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && deactivate

cd ../subject8_kimchi_detection
python3 -m venv venv && source venv/bin/activate
pip install ultralytics==8.4.175 pyyaml
pip freeze | grep -iE "ultralytics|torch|numpy|opencv|pyyaml" > requirements.txt
```

- PyTorch는 GPU에 맞는 버전 확인 (`python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` → `True`)
- 교과8 `requirements.txt` 는 7절 필수 파일 → 커밋 대상

### 7단계 — GitHub에 없는 데이터 놓기 (데이터 담당에게 받음)

| 받는 것 | 놓을 곳 | 확인 |
|---|---|---|
| 교과7 결과 `data/raw/`, `data/dataset1_result/`, `data/dataset2_result/`, `data/final/` | `subject7_kimchi_labeling/data/` | 라벨링 프로그램에서 폴더 열기 |
| `data/final` 900장 + `dataset_manifest.csv` 사본 | `subject8_kimchi_detection/data/subject7_final/` | JPG 900 · TXT 900 |
| `data/yolo/` | `subject8_kimchi_detection/data/yolo/` | train 600 · val 100 · test 100 |
| `data/bridge_holdout/` | `subject8_kimchi_detection/data/bridge_holdout/` | 100 |
| `data/smoke/` | `subject8_kimchi_detection/data/smoke/` | 35 / 10 / 5 |
| `runs/baseline_v1/` (학습 기록) | `subject8_kimchi_detection/runs/baseline_v1/` | `results.csv` 100행 |
| `baseline_best.pt` | `subject8_kimchi_detection/models/baseline/baseline_best.pt` | sha256 앞 12자리 `c90f9767442e` |
| `reports/figures/*.png` | `subject8_kimchi_detection/reports/figures/` | 2장 |
| 예측 이미지 | `subject8_kimchi_detection/runs/predict/baseline_val_images/` | 100장 |

- `subject7_final` 은 교과7 `data/final` 의 **복사본**. 하드링크(`cp -l`)·심볼릭 링크 금지 — 라벨링 프로그램이 txt를 덮어쓰면 교과8 입력까지 바뀜
- 전달은 팀 규칙에 따른 방법으로만 (GitHub · 공개 메신저 금지)
- `labels/*.cache` 파일은 지워도 됨 (Ultralytics가 다시 만듦)

### 8단계 — 검증 (전부 통과해야 커밋)

`subject8_kimchi_detection/` 에서 venv 켜고 실행

| # | 확인 | 명령 | 통과 기준 |
|---|---|---|---|
| 1 | Dataset Version | `for s in train val; do echo "$s $(cat data/yolo/labels/$s/*.txt \| sha256sum \| cut -c1-12)"; done` | train `57f0bf5121e4` · val `ab6cc7f98da7` |
| 2 | 분할 Freeze | `sha256sum manifests/train.csv manifests/val.csv \| cut -c1-12` | `8b9e6b7c4644` · `eabbaa9b8f3a` |
| 3 | 데이터 검사 | `python src/dataset_audit.py` → `grep "Split Role" reports/dataset_summary.csv` | 600 · 100 · 100 · 100 · Total 900 · PASS |
| 4 | 분할 재현 (미리보기만) | `python scripts/03_build_split.py` (옵션 없이 미리보기) | 배정 변경 0 · `--apply` 쓰지 않음 |
| 5 | Baseline 재현 | `yolo detect val model=models/baseline/baseline_best.pt data=configs/dataset.yaml imgsz=1920 batch=3` | 전체 P 0.926 · R 0.849 · mAP50 0.889 · mAP50-95 0.780 |
| 6 | 학습 Script | `python -u scripts/06_train_baseline.py --epochs 1 --name split_check` | `runs/split_check` 생성 · 확인 후 삭제 |
| 7 | 교과7 프로그램 | `cd ../subject7_kimchi_labeling && python main.py` | 폴더 열기 · BBox 표시 · 저장 · 자동 검사 동작 |
| 8 | NDA | `git ls-files \| grep -Ei '\.(jpg\|jpeg\|png\|npy\|pt\|zip\|gz)$\|/labels/'` | `docs/assets` · `reports/assets` 기존 png 5개 외 0줄 |

- 5번이 다르면 경로가 다른 데이터를 가리키는 것 → 1번부터 다시 확인
- 4번 미리보기 출력 형식은 Freeze 때 기록(`reports/logs/build_split/build_split_20261013_111107.md`)과 비교

### 9단계 — 문서 경로 수정

```bash
grep -rln "tools/build_split\|tools/06_train\|runs/baseline_v1/weights\|visol04" --include=*.md subject8_kimchi_detection subject7_kimchi_labeling
```

- 걸린 문서의 경로를 새 위치로 수정
- `subject8…/README.md` 의 "가이드와 다른 점" 표 → 이제 남는 차이만 남김 (`tools/` · `models/` 항목 삭제)
- `runs/*/args.yaml` 안의 옛 경로는 과거 기록이므로 **고치지 않음**. `baseline_training_condition.md` 비고에 "학습 당시 경로는 분리 이전 구조" 한 줄 추가

### 10단계 — 커밋 · push · 폴더 이름

```bash
git add -A subject7_kimchi_labeling subject8_kimchi_detection README.md .gitignore
git diff --cached --name-only | grep -Ei '\.(jpg|jpeg|png|bmp|npy|pt|zip|gz)$|/labels/|id_rsa|\.pem$|\.key$|\.env$' || echo "NDA OK"
git commit -m "docs: 분리 후 문서 경로 갱신 · 교과8 requirements.txt"
git push -u origin feature/split_7_8
```

- 새로 clone 하면 폴더 이름이 이미 `4_Vison` 이므로 이름 변경은 필요 없음. 기존 `visol04` 폴더에서 작업하던 PC만 병합 후 `pull` 하고 폴더 이름을 바꿈 (venv는 6단계처럼 새로 만듦)

- push 후 Pull Request로 `feature/7_8` 에 병합 요청 → 데이터 담당이 8단계 결과를 보고 승인

---

## 3. 문제가 생기면

| 상황 | 원인 후보 | 조치 |
|---|---|---|
| `git status` 에 `R` 대신 `D` + `??` | `git mv` 대신 `mv` 사용 | `git add -A <폴더>` 하면 대부분 `R` 로 인식 |
| `ModuleNotFoundError: src…` | 실행 위치가 프로그램 루트가 아님 | `cd subject8_kimchi_detection` 후 실행 (9.0) |
| `Dataset not found` | `dataset.yaml` 상대경로 + 다른 위치에서 실행 | 프로그램 루트에서 실행 |
| `yolo: command not found` | venv 꺼짐 | `source venv/bin/activate` |
| 8단계 1 · 2번 해시 다름 | 받은 데이터가 다른 판 | 멈추고 데이터 담당에게 확인 (새 Dataset Version 금지) |
| 이미지가 `git status` 에 보임 | `.gitignore` 규칙 누락 | 커밋하지 말고 4단계 표의 규칙 다시 확인 |

**되돌리기**

- push 전: `git switch feature/7_8 && git branch -D feature/split_7_8`
- push 후: PR을 닫고 브랜치 삭제 (`feature/7_8` 은 그대로)
- 데이터: 같은 디스크 안 이동이면 반대로 `mv`

---

## 4. 이 작업에서 하지 않는 것 (다음 리팩토링)

- `scripts/03_build_split.py` 를 `src/split_builder.py`(기능) + `scripts/03_build_split.py`(실행)로 나누기 (8절)
- 나머지 실행 Script (`01_check_environment` · `02_audit_subject7_final` · `04_preview_dataset` · `05_smoke_train` · `07~12`) 만들기
- 교과7 프로그램 내부 구조 변경
