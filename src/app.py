"""LabelingApp — 상태(변수) 초기화 + 기능 Mixin 조립 + 시작·종료 처리"""
from tkinter import messagebox

from src.yolo.auto_label import YoloAutoLabeler
from src.ui.layout_mixin import LayoutMixin
from src.ui.folder_mixin import FolderMixin
from src.ui.navigation_mixin import NavigationMixin
from src.ui.view_mixin import ViewMixin
from src.ui.edit_mixin import EditMixin
from src.yolo.auto_mixin import AutoLabelMixin
from src.bbox.storage_mixin import StorageMixin


class LabelingApp(LayoutMixin, FolderMixin, NavigationMixin, ViewMixin,
                  EditMixin, AutoLabelMixin, StorageMixin):
    def __init__(self, root):
        self.root = root
        root.title("라벨링 프로그램")
        root.geometry("1440x860")
        root.minsize(1100, 680)
        root.protocol("WM_DELETE_WINDOW", self.on_closing)   # 창 닫기(X) → 저장 확인

        # 폴더 / 이미지 상태
        self.projects = []         # 불러온 프로젝트(데이터 폴더) 목록 - dict 리스트
        self.proj_of = {}          # 이미지 경로 → 소속 프로젝트(dict)
        self.folders = {}          # "프로젝트명|상대경로" → 이미지 경로 리스트
        self.folder_keys = []
        self.folder_images = []    # 선택한 폴더의 전체 이미지 (단계 보기 적용 전)
        self.images = []           # 단계 보기가 적용된 실제 작업 목록
        self.view_filter = "all"   # all / 1차 / 2차 / review / final
        self.idx = -1
        self.annotations = {}      # 이미지 경로 → 박스 리스트
        self.notes = {}            # 이미지 경로 → 이슈 노트
        self.review_status = {}    # 이미지 경로 → 검수 상태 (1차 / 2차 / review / final)
        self.last_stage = ""       # 마지막으로 고른 검수 상태
        self.done = set()          # 저장된 이미지 (목록 초록색 표시)
        self.passed = set()        # 진행률용: 다음/저장 후 다음으로 넘긴 이미지

        # 화면(뷰) 상태
        self.img = None
        self.tkimg = None
        self.scale = 1.0
        self.fit_scale = 1.0
        self.ox = self.oy = 0.0
        self.is_fit = True

        # 마우스 / 선택 상태
        self.selected = []
        self.pending = None        # 클래스 미지정 박스
        self.mode = None           # press / draw / pan / zoomsel / resize
        self.zoom_mode = False
        self.press_xy = None
        self.temp_rect = None
        self.sidebar_on = True
        self._cache = {}           # 다음 이미지 미리 읽기
        self._cursor = None
        self.resize_hd = None
        self._label_hits = []      # 캔버스 위 이름표 영역 → 박스 (이름표 클릭 선택용)

        # 자동 추론(YOLO) 상태
        self.labeler = YoloAutoLabeler()
        self.auto_pred = {}        # 이미지 경로 → [(cls, (xc,yc,w,h), conf)] 일괄 추론 결과
        self._batch_running = False
        self._batch_stop = False
        self._batch_total = 0
        self._batch_n = 0

        self.build_ui()

        # 마우스 휠 확대·축소 (Windows·macOS: MouseWheel / 리눅스·WSL: Button-4, Button-5)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.imageCanvas.bind(seq, self.on_wheel)

        # 화면이 다 그려진 뒤 마지막에 열었던 폴더를 자동으로 열기
        self.root.after(150, self._auto_load_last_folder)

    # ── 시작 / 종료 ──
    def _auto_load_last_folder(self):
        picked, last_img = self.load_last_folder()
        if picked:
            self.open_folder(auto_picked=picked, auto_last_img=last_img)

    def save(self):
        ok = super().save()
        if ok:
            self.remember_folder()           # 저장할 때마다 열린 폴더·보던 이미지 기억
        return ok

    def save_and_next(self):
        super().save_and_next()
        self.remember_folder()

    def on_closing(self):
        p = self.cur_path()
        if p and self.img and p not in self.done:
            answer = messagebox.askyesnocancel(
                "종료 확인",
                "현재 이미지는 아직 저장하지 않았습니다.\n\n"
                "[예] 저장 후 종료\n[아니요] 저장하지 않고 종료\n[취소] 돌아가기",
                icon="warning")
            if answer is None:               # 취소
                return
            if answer and not self.save():   # 저장 실패(검수 상태 미선택 등) → 종료하지 않음
                return
        self.remember_folder()
        self.root.destroy()
