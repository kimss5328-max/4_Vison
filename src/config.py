"""프로그램 전체에서 쓰는 상수 모음 — 경로/클래스/단계/색상/폰트 등은 여기서만 수정"""
import os

# ── 경로 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 프로그램 폴더 (visol04) = 결과 기준 위치
PICK_START_DIR = os.path.expanduser("~/exe_01")          # 이미지 폴더 선택 창의 시작 위치
SETTINGS_PATH = os.path.expanduser("~/.labeling_tool_config.json")   # 마지막 폴더 기억 (저장소 밖)

# 결과 구조 — 데이터셋마다 결과 폴더를 따로 만듦 (원본은 고른 경로의 images·labels 에서 읽기만)
#   visol04/
#   ├── data/
#   │   ├── dataset1_result/          ← <데이터셋 이름(DATASET_NAMES)>_result
#   │   │   ├── work/                 작업자가 보낸 결과
#   │   │   │   ├── pass/    img, txt   딥러닝 결과 그대로 문제없음
#   │   │   │   ├── edited/  img, txt   추가·수정함
#   │   │   │   └── review/  img, txt   검수자에게 판단 요청 (+ preview/ 박스를 그려 넣은 확인용 이미지)
#   │   │   ├── view/        img, txt   검수자 → 작업자: 재작업 요청
#   │   │   ├── final/       img, txt   검수자: 최종 승인 → 학습용
#   │   │   ├── working/     txt        편집했지만 아직 [저장] 안 한 박스 (임시, 저장하면 지워짐)
#   │   │   ├── issues/      img, txt   이슈 노트에 글자를 적어 저장한 이미지 사본 + <이미지>_issue.txt (추가만)
#   │   │   ├── csv/                    이미지별 이력 csv (추가만)
#   │   │   └── classes.txt
#   │   └── dataset2_result/ …
#   └── manifests/dataset_manifest.csv  데이터 대장 (모든 데이터셋 1개 파일, source_dataset 으로 구분)
#   img·txt 아래는 원본 images 폴더 구조 그대로 — 예) data/dataset1_result/work/pass/img/train/a.jpg
RESULT_DIR = "data"              # visol04/data
RESULT_SUFFIX = "_result"        # dataset1 → dataset1_result
IMG_SUB, TXT_SUB = "img", "txt"
PREVIEW_SUB = "preview"          # review/preview — 확인용 이미지
# 아래 튜플은 결과 폴더(<데이터셋>_result) 기준 경로
WORKING_DIR = ("working",)
ISSUES_DIR = ("issues",)
CSV_DIR = ("csv",)
STAGE_DIRS = {"pass": ("work", "pass"),
              "edited": ("work", "edited"),
              "review": ("work", "review"),
              "view": ("view",),
              "final": ("final",)}
PREVIEW_STAGES = ("review",)     # 이 단계에 저장할 때 preview/ 확인용 이미지도 만듦
MANIFEST_DIR = "manifests"
MANIFEST_FILE = "dataset_manifest.csv"

# ── 데이터 대장(manifest) — 이미지 1장당 1행, 저장할 때마다 그 행을 최신 값으로 덮어씀 ──
#   이력(누가·언제·어디로)은 data/<데이터셋>_result/csv/<이미지>.csv 에 따로 쌓임. manifest 는 '현재 상태' 결과표
MANIFEST_HEADER = ["file_name", "source_dataset", "original_split", "scene_type",
                   "worker", "status", "qa_status", "review_reason"]
# 저장 단계 → (status, qa_status).  view 는 표에 없음 → status 는 직전 값 유지, qa_status = WAIT
STAGE_STATUS = {"pass": ("DONE", "WAIT"),
                "edited": ("EDITED", "WAIT"),
                "review": ("REVIEW", "WAIT"),
                "final": ("FINAL", "PASS")}
QA_WAIT = "WAIT"
# source_dataset — 데이터셋 폴더(images·labels 를 담은 폴더) 이름 → manifest 에 적을 이름
#   표에 없는 데이터셋은 폴더 이름 그대로 기록하고, 폴더를 열 때 알림. 새 데이터셋은 여기에 한 줄 추가
DATASET_NAMES = {
    "이물검출_학습데이터1": "dataset1",
    "이물검출_학습데이터2": "dataset2",
}
# original_split — 이미지가 들어 있는 폴더 경로에서 찾음 (왼쪽: 폴더 이름, 오른쪽: 기록값)
SPLIT_NAMES = {"train": "train", "validation": "validation", "val": "validation", "valid": "validation"}
# scene_type — (기록값, 화면 설명)
SCENE_TYPES = (("kimchi_with_target", "김치 + 검출 대상 객체"),
               ("normal_kimchi", "정상 김치"),
               ("object_only", "검출 대상 객체 단독"),
               ("other_review", "바로 구분하기 어려움"))
# review_reason — REVIEW 로 저장할 때 필수. 한 번 기록되면 지우지 않고 새로 고를 때만 바뀜
REVIEW_REASONS = ("class_ambiguous", "bbox_boundary_ambiguous", "object_unclear",
                  "empty_label_check", "other")

# 이전 버전 결과 폴더 — 원본 목록에 섞이지 않게 탐색에서 제외
DONE_SUFFIX = "_done"            # train/train_done
DEFAULT_DONE = "train_done"
LEGACY_OUT = {"images": ("yolo", "review"), "labels": ("yolo", "csv", "issues")}

# ── 이미지 ──
IMG_EXTS = (".jpg", ".png", ".jpeg")  # 필요 시 확장자 추가

# ── 클래스 정의 — 클래스 규칙은 이 표만 고치면 전체에 반영됨 ──
#   id           : 클래스 번호. 0 부터 빠짐없이, YOLO 모델 학습 번호와 같아야 함 (바꾸지 말 것)
#   name         : 표시 이름
#   selectable   : 목록에서 지정 가능한지 (적지 않으면 True)
#   hidden       : True 면 클래스 목록에서 숨김 (번호는 유지, 자동으로 지정 불가)
#   replace_with : 지정 불가일 때 대신 쓸 클래스 번호 (적지 않으면 None → 저장 시 삭제 확인)
#   auto_label   : 자동 라벨링이 이 클래스로 예측했을 때
#                  "keep" 그대로 / "drop" 버림 / "replace" replace_with 번호로 바꿔 점선 박스로 (적지 않으면 "keep")
#   예) 3번도 막고 0번으로:  {"id": 3, "name": "벌레류", "selectable": False, "replace_with": 0}
#   예) 4번을 다시 쓰기  :  {"id": 4, "name": "고무장갑"}   (hidden 도 지우면 목록에 다시 표시)
CLASSES = [
    {"id": 0, "name": "나뭇잎·종이류"},
    {"id": 1, "name": "플라스틱·돌·금속류"},
    {"id": 2, "name": "나뭇가지류"},
    {"id": 3, "name": "벌레류"},
    # 고무장갑은 실제로 1번(플라스틱·돌·금속류)으로 분석해 온 이력이 있어 4번 삭제(숨김) 확정
    #   번호 4 는 모델 학습 번호 맞춤용으로 남기고, 목록에서 숨김 + 라벨에 있으면 1번으로 변경 안내
    {"id": 4, "name": "고무장갑", "selectable": False, "hidden": True,
     "replace_with": 1, "auto_label": "drop"},
    {"id": 5, "name": "병해·갈변"},
    {"id": 6, "name": "파·고추"},
]
CLASS_NAMES = [c["name"] for c in sorted(CLASSES, key=lambda c: c["id"])]   # 번호 순 이름 (classes.txt 등)
ISSUE_ID = -1                 # (예전 이슈 박스용 번호 — 목록에서는 선택 불가)

# ── 작업자 / 검수자 ──
#   INFO_FIELDS: (화면 이름, csv 열 이름 꼬리) — csv 열: worker_<꼬리>, reviewer_<꼬리>
#   저장한 사람의 역할 열만 채움 (작업자 저장 → worker_*, 검수자 저장 → reviewer_*)
INFO_FIELDS = (("이름", "name"), ("ID", "id"))

# 선택 목록 — 사람 추가·제거는 여기서만 (화면에서는 고르기만)
#   role: "reviewer"(검수자) / "worker"(작업자). 검수자는 작업자가 할 수 있는 일도 전부 가능
PEOPLE = [
    {"name": "1", "id": "1", "role": "reviewer"},
    {"name": "2", "id": "2", "role": "reviewer"},
    {"name": "3", "id": "3", "role": "worker"},
    {"name": "4", "id": "4", "role": "worker"},
    {"name": "5", "id": "5", "role": "worker"},
]
ROLE_NAMES = {"worker": "작업자", "reviewer": "검수자"}

# 검수 상태 (= 저장할 폴더). 순서 = 화면 배치 순서
STAGES = ("pass", "edited", "review", "view", "final")
WORKER_TARGETS = ("pass", "edited", "review")        # 작업자가 보낼 수 있는 곳
REVIEWER_TARGETS = STAGES                            # 검수자는 전부 (작업자 일 포함)
SOURCE_LABEL = "원본"              # 아직 저장 안 한 이미지의 위치 표시 (csv 'from' 칸·상태 표시줄)
# 작업자가 다룰 수 있는 이미지의 현재 위치 ('' = 원본) — 저장한 뒤(pass·edited·review)에도 다시 고칠 수 있음
#   (작업자라면 누구나. final 만 검수자 전용)
WORKER_EDITABLE = ("", "pass", "edited", "review", "view")
DEFAULT_TARGET = "pass"            # 검수 상태 기본값
STAGE_LABELS = {st: st for st in STAGES}             # 작업 이력 패널 표시 이름

# 단계 보기 ((전체 이미지) 선택 시) — (키, 표시 이름)
#   working: 편집했지만 저장 안 한 이미지 / issue: 이슈 기록(issues/txt/<이미지>_issue.txt)이 있는 이미지
STAGE_FILTERS = ((("all", "전체"), ("working", "working"))
                 + tuple((st, st) for st in STAGES) + (("issue", "이슈"),))

# ── 색상 ──
COLORS = ["#2f80ed", "#27ae60", "#f2994a", "#9b51e0",
          "#9e9e9e", "#d6336c", "#8d6e63", "#5c6bc0"]
ISSUE_COLOR = "#e53935"
PENDING_COLOR = "#fbc02d"
AUTO_LIST_COLOR = "#e67e22"   # 일괄 추론 결과가 대기 중인 이미지 (목록 주황색)
DONE_LIST_COLOR = "#1e8e3e"   # 저장 완료된 이미지 (목록 초록색)
LOCKED_CLASS_COLOR = "#9e9e9e"   # 지정 불가 클래스 (목록 회색)

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
MIN_BOX_PX = 2                # 이보다 작은 박스(이미지 픽셀)는 만들지 않음 / 크기 조절 최소값
DEFAULT_CONF = 0.25           # 자동 라벨링 기본 신뢰도
MAX_ZOOM = 20.0               # 원상태 대비 최대 확대 배율
WHEEL_STEP = 1.2              # 마우스 휠 한 칸당 확대·축소 배율
SHIFT, CTRL = 0x0001, 0x0004  # 키보드 수정키 비트
