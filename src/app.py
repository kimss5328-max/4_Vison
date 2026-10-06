"""LabelingApp — 상태(변수) 초기화 + 기능 Mixin 조립만 담당"""
import os
import json
from tkinter import messagebox

from src.yolo.auto_label import YoloAutoLabeler
from src.ui.layout_mixin import LayoutMixin
from src.ui.folder_mixin import FolderMixin
from src.ui.navigation_mixin import NavigationMixin
from src.ui.view_mixin import ViewMixin
from src.ui.edit_mixin import EditMixin
from src.yolo.auto_mixin import AutoLabelMixin
from src.bbox.storage_mixin import StorageMixin

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(CURRENT_DIR, "labeling_tool_config.json")


class LabelingApp(LayoutMixin, FolderMixin, NavigationMixin, ViewMixin,
                  EditMixin, AutoLabelMixin, StorageMixin):
    def __init__(self, root):
        self.root = root
        root.title("라벨링 프로그램")
        root.geometry("1440x860")
        root.minsize(1100, 680)

        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 폴더 / 이미지 상태
        self.projects = []
        self.proj_of = {}
        self.folders = {}
        self.folder_keys = []
        self.folder_images = []
        self.images = []
        self.view_filter = "all"
        self.idx = -1
        self.annotations = {}
        self.notes = {}
        self.review_status = {}
        self.done = set()
        self.passed = set()

        # 화면(뷰) 상태
        self.img = None
        self.tkimg = None
        self.scale = 1.0
        self.fit_scale = 1.0
        self.ox = self.oy = 0.0
        self.is_fit = True

        # 마우스 / 선택 상태
        self.selected = []
        self.pending = None
        self.mode = None
        self.zoom_mode = False
        self.press_xy = None
        self.temp_rect = None
        self.sidebar_on = True
        self._cache = {}
        self._cursor = None
        self.resize_hd = None
        self._label_hits = []

        # 자동 추론(YOLO) 상태
        self.labeler = YoloAutoLabeler()
        self.auto_pred = {}
        self._batch_running = False
        self._batch_stop = False
        self._batch_total = 0
        self._batch_n = 0

        self.build_ui()

        # 프로그램 실행 시 마지막 폴더와 마지막 작업 이미지 자동 복원
        self.root.after(150, self._auto_load_last_folder)

    def _auto_load_last_folder(self):
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    picked = data.get("last_picked", [])
                    last_img = data.get("last_img", None)
                    valid_picked = [(pr, ir) for pr, ir in picked if os.path.isdir(pr)]
                    if valid_picked:
                        self.open_folder(auto_picked=valid_picked, auto_last_img=last_img)
        except Exception as e:
            print(f"[DEBUG] 자동 복원 실패: {e}")

    def save(self):
        res = super().save()
        if res and hasattr(self, 'projects') and self.projects:
            picked = [(pj["proj"], pj["img_root"]) for pj in self.projects]
            cur = self.cur_path() if hasattr(self, 'cur_path') else None
            self.save_last_folder(picked, last_img=cur)
        return res

    def save_and_next(self):
        res = super().save_and_next()
        if hasattr(self, 'projects') and self.projects:
            picked = [(pj["proj"], pj["img_root"]) for pj in self.projects]
            cur = self.cur_path() if hasattr(self, 'cur_path') else None
            self.save_last_folder(picked, last_img=cur)
        return res

    def on_closing(self):
        p = self.cur_path() if hasattr(self, 'cur_path') else None
        
        # 이미 저장을 완료했거나(done/passed) 열린 이미지가 없으면 팝업 없이 즉시 종료
        if not p or not self.img or p in self.done or p in self.passed:
            self.root.destroy()
            return
            
        msg = "저장되지 않은 변경사항이 있습니다. 프로그램을 종료하시겠습니까?\n\n[예]: 현재 이미지 저장 후 종료\n[아니요]: 저장하지 않고 종료\n[취소]: 돌아가기"
        answer = messagebox.askyesnocancel("종료 확인", msg, icon="warning")
        
        if answer is True:
            if hasattr(self, 'save'):
                self.save()
            self.root.destroy()
        elif answer is False:
            self.root.destroy()