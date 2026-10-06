"""LabelingApp — 상태(변수) 초기화 + 기능 Mixin 조립만 담당"""
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

        # 폴더 / 이미지 상태
        self.projects = []         # 불러온 프로젝트(최상위 폴더) 목록 - dict 리스트
        self.proj_of = {}          # 이미지 경로 → 소속 프로젝트(dict)
        self.folders = {}          # "프로젝트명|상대경로" → 이미지 경로 리스트
        self.folder_keys = []
        self.folder_images = []    # 선택한 폴더의 전체 이미지 (보기 필터 적용 전)
        self.images = []           # 보기 필터가 적용된 실제 작업 목록
        self.view_filter = "all"   # all / todo(미라벨) / done(라벨 완료)
        self.idx = -1
        self.annotations = {}      # 이미지 경로 → 박스 리스트
        self.notes = {}            # 이미지 경로 → 이슈 노트
        self.review_status = {}    # 이미지 경로 → 검수 상태
        self.done = set()          # 저장 완료된 이미지 (목록 초록색 표시)
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
