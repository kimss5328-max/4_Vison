"""프로그램 전체에서 쓰는 상수 모음 — 경로/클래스/단계/색상/폰트 등은 여기서만 수정"""
import os

# ── 경로 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 프로그램 폴더 (visol04) = 결과 기준 위치
PICK_START_DIR = os.path.expanduser("~/exe_01")          # 이미지 폴더 선택 창의 시작 위치
SETTINGS_PATH = os.path.expanduser("~/.labeling_tool_config.json")   # 마지막 폴더 기억 (저장소 밖)

# 결과 구조 — (상위, 하위, ...) 튜플은 BASE_DIR(visol04) 기준 경로
#   visol04/
#   ├── data/
#   │   ├── raw/      img, txt   원본 사본 (작업 전)
#   │   ├── work/1차/ img, txt   작업 중 + 1차 저장 (이력 csv 기록으로 구분)
#   │   ├── work/2차/ img, txt   2차 저장
#   │   ├── final/    img, txt   최종 승인 → 학습용
#   │   ├── issues/   img, txt   이슈 노트가 있는 이미지 사본 (추가만)
#   │   ├── csv/                 이미지별 이력 csv (추가만)
#   │   └── classes.txt
#   ├── reviews/      img, txt   검수(review) 대상 — 박스를 그려 넣은 확인용 이미지
#   └── manifests/dataset_manifest.csv   전체 진행 대장 (추가만)
IMG_SUB, TXT_SUB = "img", "txt"
RAW_DIR = ("data", "raw")
ISSUES_DIR = ("data", "issues")
CSV_DIR = ("data", "csv")
STAGE_DIRS = {"1차": ("data", "work", "1차"),
              "2차": ("data", "work", "2차"),
              "review": ("reviews",),
              "final": ("data", "final")}
WORK_START = "1차"            # 작업을 시작하면(첫 편집) raw → work/1차 로 이동
MANIFEST_DIR = "manifests"
MANIFEST_FILE = "dataset_manifest.csv"

# 이전 버전 결과 폴더 — 원본 목록에 섞이지 않게 탐색에서 제외
DONE_SUFFIX = "_done"            # train/train_done
DEFAULT_DONE = "train_done"
LEGACY_OUT = {"images": ("yolo", "review"), "labels": ("yolo", "csv", "issues")}

# ── 이미지 / 클래스 ──
IMG_EXTS = (".jpg", ".png", ".jpeg")  # 필요 시 확장자 추가
CLASS_NAMES = ["나뭇잎·종이류", "플라스틱·돌·금속류", "나뭇가지류", "벌레류",
               "고무장갑(사용 안 함)", "병해·갈변", "파·고추"]   # 0~6, 4번은 사용 안 함
UNUSED_CLASS = 4
# 클래스 목록에 보이는(선택 가능한) 번호 — 4번은 숨김. 번호는 YOLO 모델과 맞추기 위해 그대로 유지
CLASS_IDS = [i for i in range(len(CLASS_NAMES)) if i != UNUSED_CLASS]
ISSUE_ID = -1                 # (예전 이슈 박스용 번호 — 이제 목록에서는 선택 불가)

# 검수 단계: (화면 이름, 폴더 이름) — 실제 위치는 STAGE_DIRS
STAGES = (("1차", "1차"), ("2차", "2차"), ("review", "review"), ("final", "final"))
WORKER_STAGES = ("1차", "2차")          # 작업자 정보를 다 입력해야 선택 가능
REVIEWER_STAGES = ("review", "final")   # 검수자 정보를 다 입력해야 선택 가능
STAGE_FILTERS = (("all", "전체"),) + tuple((st, st) for st, _ in STAGES)   # (전체 이미지) 단계 보기

# ── 색상 ──
COLORS = ["#2f80ed", "#27ae60", "#f2994a", "#9b51e0",
          "#9e9e9e", "#d6336c", "#8d6e63", "#5c6bc0"]
ISSUE_COLOR = "#e53935"
PENDING_COLOR = "#fbc02d"
AUTO_LIST_COLOR = "#e67e22"   # 일괄 추론 결과가 대기 중인 이미지 (목록 주황색)
DONE_LIST_COLOR = "#1e8e3e"   # 저장 완료된 이미지 (목록 초록색)

# ── 폰트 ──
FONT = ("맑은 고딕", 10)
FONT_B = ("맑은 고딕", 10, "bold")
FONT_S = ("맑은 고딕", 8)

# 확인용 이미지에 한글 클래스 이름을 쓰기 위한 글꼴 (앞에서부터 있는 것을 사용)
PREVIEW_FONTS = ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
                 "/mnt/c/Windows/Fonts/malgunbd.ttf", "/mnt/c/Windows/Fonts/malgun.ttf",
                 "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                 "/usr/share/fonts/truetype/nanum/NanumGothic.ttf")

# ── 조작 ──
HANDLE_R = 7                  # 크기조절 핸들 클릭 반경(px)
MAX_ZOOM = 20.0               # 원상태 대비 최대 확대 배율
WHEEL_STEP = 1.2              # 마우스 휠 한 칸당 확대·축소 배율
SHIFT, CTRL = 0x0001, 0x0004  # 키보드 수정키 비트
