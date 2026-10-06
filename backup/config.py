"""프로그램 전체에서 쓰는 상수 모음 — 클래스/색상/폰트 등은 여기서만 수정"""
from pathlib import Path

# ── 경로 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent        # 프로그램 폴더 (visol04)

# ── 저장 폴더 — 원본 하위 폴더(train) 아래에 '폴더명_done' 을 만들고 결과를 모두 그 안에 둠 ──
#   images/train/train_done/yolo    final 승인 이미지   ┐ 이름을 맞춰 둠 → 학습 시 images/.../yolo 만
#   labels/train/train_done/yolo    final YOLO txt     ┘ 지정하면 labels/.../yolo 의 라벨을 자동으로 찾음
#   images/train/train_done/review  review 이미지
#   labels/train/train_done/csv     단계별 기록 (1_1차 / 2_2차 / 3_review / 4_final)
#   labels/train/train_done/issues  이슈 노트 txt
DONE_SUFFIX = "_done"            # train → train_done
DEFAULT_DONE = "train_done"      # 이미지가 images/ 바로 아래에 있을 때 쓰는 이름
DONE_IMG_FINAL = "yolo"
DONE_IMG_REVIEW = "review"
DONE_LBL_YOLO = "yolo"
DONE_LBL_CSV = "csv"
DONE_LBL_ISSUES = "issues"
# 이전 버전이 images/·labels/ 바로 아래 만들던 결과 폴더 — 원본 목록에 섞이지 않게 탐색에서 제외
LEGACY_OUT = {"images": ("yolo", "review"), "labels": ("yolo", "csv", "issues")}

# ── 이미지 / 클래스 ──
IMG_EXTS = (".jpg", ".png", ".jpeg")  # 필요 시 확장자 추가
CLASS_NAMES = ["나뭇잎·종이류", "플라스틱·돌·금속류", "나뭇가지류", "벌레류",
               "고무장갑(사용 안 함)", "병해·갈변", "파·고추"]   # 0~6, 4번은 사용 안 함
UNUSED_CLASS = 4
# 클래스 목록에 보이는(선택 가능한) 번호 — 4번은 숨김. 번호는 YOLO 모델과 맞추기 위해 그대로 유지
CLASS_IDS = [i for i in range(len(CLASS_NAMES)) if i != UNUSED_CLASS]
ISSUE_ID = -1                 # (예전 이슈 박스용 번호 — 이제 목록에서는 선택 불가)

# 검수 단계: (화면 이름, labels/csv 아래 폴더 이름)
STAGES = (("1차", "1_1차"), ("2차", "2_2차"), ("review", "3_review"), ("final", "4_final"))
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

# ── 조작 ──
HANDLE_R = 7                  # 크기조절 핸들 클릭 반경(px)
MAX_ZOOM = 20.0               # 원상태 대비 최대 확대 배율
SHIFT, CTRL = 0x0001, 0x0004  # 키보드 수정키 비트
