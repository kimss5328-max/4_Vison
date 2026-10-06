"""프로그램 전체에서 쓰는 상수 모음 — 클래스/색상/폰트 등은 여기서만 수정"""

# ── 이미지 / 클래스 ──
IMG_EXTS = (".jpg", ".png", ".jpeg")  # 필요 시 확장자 추가
CLASS_NAMES = ["나뭇잎·종이류", "플라스틱·돌·금속류", "나뭇가지류", "벌레류",
               "고무장갑(사용 안 함)", "병해·갈변", "파·고추"]   # 0~6, 4번은 사용 안 함
UNUSED_CLASS = 4
ISSUE_ID = -1                 # 이슈 박스 전용 클래스 번호
ISSUE_LABEL = "[이슈]"
REVIEW_STATES = ("pass", "edited", "review", "reviewed")  # 검수 상태 선택지
VIEW_FILTERS = (("all", "전체"), ("todo", "미라벨"), ("done", "라벨 완료"))  # 이미지 목록 보기 필터

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
