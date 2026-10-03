import os
import math
import shutil
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
IMG_EXTS = (".jpg", ".png", ".jpeg")  # 필요 시 확장자 추가
CLASS_NAMES = ["나뭇잎·종이류", "플라스틱·돌·금속류", "나뭇가지류", "벌레류",
               "고무장갑(사용 안 함)", "병해·갈변", "파·고추"]   # 0~6, 4번은 사용 안 함
UNUSED_CLASS = 4
HANDLE_R = 7              # 크기조절 핸들 클릭 반경(px)
ISSUE_ID = -1                                             # 이슈 박스 전용 클래스 번호
ISSUE_LABEL = "[이슈]"

COLORS = ["#2f80ed", "#27ae60", "#f2994a", "#9b51e0",
          "#9e9e9e", "#d6336c", "#8d6e63", "#5c6bc0"]
ISSUE_COLOR = "#e53935"
PENDING_COLOR = "#fbc02d"
AUTO_LIST_COLOR = "#e67e22"   # 일괄 추론 결과가 대기 중인 이미지 (목록 주황색)

FONT = ("맑은 고딕", 10)
FONT_B = ("맑은 고딕", 10, "bold")
MAX_ZOOM = 20.0           # 원상태 대비 최대 확대 배율
SHIFT, CTRL = 0x0001, 0x0004


class LabelingApp:
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
        self.images = []
        self.idx = -1
        self.annotations = {}      # 이미지 경로 → 박스 리스트
        self.notes = {}            # 이미지 경로 → 이슈 노트
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
        self.mode = None           # press / draw / pan / zoomsel
        self.zoom_mode = False
        self.press_xy = None
        self.temp_rect = None
        self.sidebar_on = True
        self._cache = {}           # 다음 이미지 미리 읽기
        self._cursor = None
        self.resize_hd = None

        # 자동 추론(YOLO) 상태
        self.model = None          # ultralytics YOLO 객체 (best.pt)
        self.model_name = ""
        self.auto_pred = {}        # 이미지 경로 → [(cls, (xc,yc,w,h), conf)] 일괄 추론 결과(정규화 좌표)
        self._batch_running = False
        self._batch_stop = False
        self._batch_total = 0
        self._batch_n = 0

        self.build_ui()

    # ─────────────────────────────────────────
    # UI 구성
    # ─────────────────────────────────────────
    def build_ui(self):
        r = self.root
        r.columnconfigure(1, weight=1)
        r.rowconfigure(1, weight=1)

        # [0,0~1] 상단 바: 사이드바 on/off + 진행률
        #  → 버튼을 0열 밖(상단 바)에 두어야 사이드바를 숨길 때 0열 폭이 0이 됨
        progress = tk.Frame(r)
        progress.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))
        self.sidebarToggleBtn = tk.Button(progress, text="◀ 사이드바 off", font=FONT, width=13,
                                          command=self.toggle_sidebar)
        self.sidebarToggleBtn.pack(side="left", padx=(0, 12))
        tk.Label(progress, text="진행률 (완료 / 전체)", font=FONT_B).pack(side="left")
        self.progressBar = ttk.Progressbar(progress, mode="determinate", maximum=100)
        self.progressBar.pack(side="left", fill="x", expand=True, padx=8)
        self.progressText = tk.Label(progress, text="0 / 0  (0.0%)", font=FONT, width=18)
        self.progressText.pack(side="left")

        # [1,0] 왼쪽 사이드바
        self.sidebar = tk.Frame(r)
        self.sidebar.grid(row=1, column=0, sticky="ns", padx=(6, 0), pady=4)

        lf_folder = tk.LabelFrame(self.sidebar, text="폴더 분류", font=FONT_B)
        lf_folder.pack(fill="x")
        self.openFolderBtn = tk.Button(lf_folder, text="폴더 열기", font=FONT,
                                       command=self.open_folder)
        self.openFolderBtn.pack(fill="x", padx=4, pady=(4, 2))
        self.folderSelect = ttk.Combobox(lf_folder, state="readonly", font=FONT)
        self.folderSelect.pack(fill="x", padx=4, pady=(2, 6))
        self.folderSelect.bind("<<ComboboxSelected>>", self.on_folder_select)

        lf_list = tk.LabelFrame(self.sidebar, text="폴더 내 이미지", font=FONT_B)
        lf_list.pack(fill="both", expand=True, pady=(6, 0))
        sb = tk.Scrollbar(lf_list)
        sb.pack(side="right", fill="y")
        self.imageList = tk.Listbox(lf_list, width=24, font=FONT,
                                    exportselection=False, yscrollcommand=sb.set)
        self.imageList.pack(side="left", fill="both", expand=True)
        sb.config(command=self.imageList.yview)
        self.imageList.bind("<<ListboxSelect>>", self.on_image_list_select)

        # [1,1] 가운데: 이미지 + 하단 도구
        center = tk.Frame(r)
        center.grid(row=1, column=1, sticky="nsew", padx=6, pady=4)
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        self.imageCanvas = tk.Canvas(center, bg="#2b2b2b", highlightthickness=0,
                                     cursor="crosshair")
        self.imageCanvas.grid(row=0, column=0, sticky="nsew")
        self.imageCanvas.bind("<Configure>", self.on_canvas_resize)
        self.imageCanvas.bind("<ButtonPress-1>", self.on_press)
        self.imageCanvas.bind("<B1-Motion>", self.on_drag)
        self.imageCanvas.bind("<ButtonRelease-1>", self.on_release)
        self.imageCanvas.bind("<Delete>", lambda e: self.delete_selected())
        self.imageCanvas.bind("<Escape>", self.on_escape)
        self.imageCanvas.bind("<Motion>", self.on_motion)

        bottom = tk.Frame(center)
        bottom.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.resetViewBtn = tk.Button(bottom, text="원상태", font=FONT, width=8,
                                      command=self.reset_view)
        self.resetViewBtn.pack(side="left")
        self.zoomBtn = tk.Button(bottom, text="확대", font=FONT, width=8,
                                 command=self.toggle_zoom_mode)
        self.zoomBtn.pack(side="left", padx=(4, 0))
        self.zoomOutBtn = tk.Button(bottom, text="축소", font=FONT, width=8,
                                    command=self.zoom_out)
        self.zoomOutBtn.pack(side="left", padx=(4, 0))
        self.zoomWindowBtn = tk.Button(bottom, text="확대된 이미지 창 생성", font=FONT,
                                       command=self.open_zoom_window)
        self.zoomWindowBtn.pack(side="left", padx=(4, 0))
        self.deleteBtn = tk.Button(bottom, text="삭제", font=FONT, fg="#c62828",
                                   command=self.delete_selected)
        self.deleteBtn.pack(side="right")

        # [0~1,2] 오른쪽 패널
        right = tk.Frame(r)
        right.grid(row=0, column=2, rowspan=2, sticky="ns", padx=(0, 6), pady=6)

        nav = tk.Frame(right)
        nav.pack(side="bottom", fill="x", pady=(6, 0))
        for c in range(4):
            nav.columnconfigure(c, weight=1)
        self.prevBtn = tk.Button(nav, text="이전", font=FONT, height=2,
                                 command=self.prev_image)
        self.prevBtn.grid(row=0, column=0, sticky="ew", padx=1)
        self.nextBtn = tk.Button(nav, text="다음", font=FONT, height=2,
                                 command=self.next_image)
        self.nextBtn.grid(row=0, column=1, sticky="ew", padx=1)
        self.saveBtn = tk.Button(nav, text="저장", font=FONT_B, height=2,
                                 command=self.save)
        self.saveBtn.grid(row=0, column=2, sticky="ew", padx=(10, 1))
        self.saveNextBtn = tk.Button(nav, text="저장 후 다음", font=FONT_B, height=2,
                                     command=self.save_and_next)
        self.saveNextBtn.grid(row=0, column=3, sticky="ew", padx=1)

        upper = tk.Frame(right)
        upper.pack(side="top", fill="x")

        lf_cls = tk.LabelFrame(upper, text="클래스 분류", font=FONT_B)
        lf_cls.grid(row=0, column=0, sticky="nsew")
        self.classList = tk.Listbox(lf_cls, width=14, height=14, font=FONT,
                                    exportselection=False)
        self.classList.pack(fill="both", expand=True, padx=4, pady=4)
        for i, name in enumerate(CLASS_NAMES):
            self.classList.insert("end", f"{i}: {name}")
            self.classList.itemconfig(i, fg=COLORS[i % len(COLORS)])
        self.classList.insert("end", ISSUE_LABEL)
        self.classList.itemconfig(len(CLASS_NAMES), fg=ISSUE_COLOR)
        self.classList.bind("<<ListboxSelect>>", self.on_class_select)

        lf_info = tk.LabelFrame(upper, text="클래스 크기 정보", font=FONT_B)
        lf_info.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cols = ("no", "cls", "x", "y", "w", "h")
        heads = ("No", "클래스", "X", "Y", "W", "H")
        widths = (30, 56, 58, 58, 58, 58)
        self.labelList = ttk.Treeview(lf_info, columns=cols, show="headings", height=6)
        for c, h, w in zip(cols, heads, widths):
            self.labelList.heading(c, text=h)
            self.labelList.column(c, width=w, anchor="center", stretch=False)
        self.labelList.pack(fill="x", padx=4, pady=4)
        self.labelList.bind("<<TreeviewSelect>>", self.on_tree_select)

        detail = tk.Frame(lf_info)
        detail.pack(fill="x", padx=4, pady=(0, 4))
        self.labelDetail = {}
        for row, key in enumerate(("Class", "X(중심)", "Y(중심)", "너비", "높이")):
            tk.Label(detail, text=key, font=FONT, anchor="w", width=8).grid(row=row, column=0, sticky="w")
            v = tk.StringVar()
            tk.Entry(detail, textvariable=v, font=FONT, state="readonly",
                     width=16).grid(row=row, column=1, sticky="ew", pady=1)
            self.labelDetail[key] = v

        lf_author = tk.LabelFrame(right, text="작성자", font=FONT_B)
        lf_author.pack(side="top", fill="x", pady=(6, 0))
        self.workerVar = tk.StringVar()
        tk.Entry(lf_author, textvariable=self.workerVar, font=FONT).pack(fill="x", padx=4, pady=4)

        # ── 자동 라벨링 (YOLO) ──
        lf_auto = tk.LabelFrame(right, text="자동 라벨링 (YOLO)", font=FONT_B)
        lf_auto.pack(side="top", fill="x", pady=(6, 0))

        row1 = tk.Frame(lf_auto)
        row1.pack(fill="x", padx=4, pady=(4, 0))
        self.loadModelBtn = tk.Button(row1, text="모델(best.pt) 불러오기", font=FONT,
                                      command=self.load_model)
        self.loadModelBtn.pack(side="left")
        self.modelLabel = tk.Label(row1, text="(모델 없음)", font=("맑은 고딕", 8),
                                   fg="#666", anchor="w")
        self.modelLabel.pack(side="left", padx=6)

        row2 = tk.Frame(lf_auto)
        row2.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(row2, text="신뢰도(conf)", font=FONT).pack(side="left")
        self.confVar = tk.StringVar(value="0.25")
        tk.Spinbox(row2, from_=0.05, to=0.95, increment=0.05, format="%.2f",
                   textvariable=self.confVar, width=6, font=FONT).pack(side="left", padx=6)
        self.autoOnOpen = tk.BooleanVar(value=False)
        tk.Checkbutton(row2, text="열 때 자동 추론", font=FONT,
                       variable=self.autoOnOpen).pack(side="left", padx=(6, 0))

        row3 = tk.Frame(lf_auto)
        row3.pack(fill="x", padx=4, pady=(4, 0))
        self.autoCurBtn = tk.Button(row3, text="현재 이미지 추론", font=FONT,
                                    command=self.run_auto_current)
        self.autoCurBtn.pack(side="left")
        self.autoBatchBtn = tk.Button(row3, text="미라벨 이미지 일괄 추론", font=FONT,
                                      command=self.toggle_batch)
        self.autoBatchBtn.pack(side="left", padx=(4, 0))

        tk.Label(lf_auto, font=("맑은 고딕", 8), fg="#666", justify="left",
                 text="※ 자동 BBox는 점선 + 'AI %' 로 표시됩니다.\n"
                      "   확인/수정 후 '저장'을 누르면 확정됩니다.\n"
                      "   (잘못된 박스: 선택 후 삭제 / 클래스 재지정)"
                 ).pack(anchor="w", padx=4, pady=(2, 4))

        lf_issue = tk.LabelFrame(right, text="이슈 노트", font=FONT_B)
        lf_issue.pack(side="top", fill="both", expand=True, pady=(6, 0))
        self.issueNote = tk.Text(lf_issue, width=1, height=8, wrap="word", font=FONT)
        self.issueNote.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(lf_issue, font=("맑은 고딕", 8), fg="#666", justify="left",
                 text="※ 이슈 내용 또는 [이슈] 박스가 있으면\n   이미지와 txt를 issues 폴더에 함께 저장").pack(anchor="w", padx=4)

        # [2,*] 상태 표시줄
        self.statusBar = tk.Label(r, text="'폴더 열기'로 이미지 폴더를 선택하세요.",
                                  font=FONT, anchor="w", fg="#444")
        self.statusBar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 4))

    def status(self, msg):
        self.statusBar.config(text=msg)

    def toggle_sidebar(self):
        # 폴더 분류 + 폴더 내 이미지(self.sidebar) 전체를 숨기거나 다시 표시
        if self.sidebar_on:
            self.sidebar.grid_remove()
            self.sidebarToggleBtn.config(text="▶ 사이드바 on")
        else:
            self.sidebar.grid()
            self.sidebarToggleBtn.config(text="◀ 사이드바 off")
        self.sidebar_on = not self.sidebar_on
        # 레이아웃을 즉시 반영한 뒤, 늘어난/줄어든 캔버스 폭에 맞춰 이미지 다시 그리기
        self.root.update_idletasks()
        self.on_canvas_resize()

    # ─────────────────────────────────────────
    # 프로젝트 / 경로 도우미
    # ─────────────────────────────────────────
    def P(self, p):
        """이미지 경로 → 소속 프로젝트(dict)"""
        return self.proj_of[p]

    def rel_of(self, p):
        return os.path.relpath(p, self.P(p)["img_root"])

    def disp(self, p):
        """화면 표시용 이름 (프로젝트가 2개 이상이면 프로젝트명 포함)"""
        rel = self.rel_of(p)
        return f"{self.P(p)['name']}/{rel}" if len(self.projects) > 1 else rel

    # ─────────────────────────────────────────
    # 폴더 / 이미지 목록
    # ─────────────────────────────────────────
    @staticmethod
    def _has_both(p):
        return (
            os.path.isdir(os.path.join(p, "images"))
            and os.path.isdir(os.path.join(p, "labels"))
        )

    def _find_roots(self, d):
        d = os.path.normpath(d)

        # 1. 선택한 폴더 자체가 프로젝트인 경우
        if self._has_both(d):
            return [
                (d, os.path.join(d, "images"))
            ]

        # 2. 선택한 폴더 자체가 images 폴더인 경우
        if os.path.basename(d).lower() == "images":
            return [
                (os.path.dirname(d), d)
            ]

        # 3. 선택한 폴더 바로 아래에 있는 프로젝트만 확인
        subs = []
        try:
            for name in sorted(os.listdir(d)):
                sub = os.path.join(d, name)
                if not os.path.isdir(sub):
                    continue
                # _labeled 폴더 제외
                if name.endswith("_labeled"):
                    continue
                if self._has_both(sub):
                    subs.append(
                        (sub, os.path.join(sub, "images"))
                    )
        except OSError:
            pass

        if subs:
            return subs

        # 4. 아무 프로젝트도 없으면 선택한 폴더 자체를 이미지 폴더로 사용
        return [(d, d)]

    def open_folder(self):
        self.save_current_note()

        picked = []
        while True:
            d = filedialog.askdirectory(title="최상위 폴더 선택 (images + labels 가 있는 폴더, 또는 그 상위 폴더)")
            if not d:
                break
            for item in self._find_roots(d):
                if item not in picked:
                    picked.append(item)
            names = "\n".join("  ./ " + os.path.basename(pr) for pr, _ in picked)
            if not messagebox.askyesno("폴더 추가",
                                       f"현재 {len(picked)}개 폴더가 선택되었습니다.\n{names}\n\n"
                                       f"다른 폴더도 추가하시겠습니까?"):
                break
        if not picked:
            return

        projects, proj_of, folders = [], {}, {}
        used = set()
        for proj, img_root in picked:
            name = os.path.basename(proj)
            if name in used:
                name += f"({len(used)})"
            used.add(name)
            pj = {"proj": proj, "img_root": img_root, "name": name,
                  "out_dir": None, "by_rel": {}, "by_name": {}}
            if img_root != proj:
                lbl_root = os.path.join(proj, "labels")
                for dp, _, files in os.walk(lbl_root):
                    for f in files:
                        # ────────── 수정: txt와 csv 모두 인식하도록 변경 ──────────
                        if f.lower().endswith((".txt", ".csv")):
                            q = os.path.join(dp, f)
                            rel = os.path.splitext(os.path.relpath(q, lbl_root))[0]
                            pj["by_rel"][rel] = q
                            pj["by_name"].setdefault(os.path.splitext(f)[0], q)
            cand = self.default_out_dir(pj)
            pj["out_dir"] = cand if os.path.isdir(cand) else None
            projects.append(pj)

            for cur, _, files in os.walk(img_root):
                imgs = sorted(f for f in files if f.lower().endswith(IMG_EXTS))
                if imgs:
                    rel = os.path.relpath(cur, img_root)
                    lst = [os.path.join(cur, f) for f in imgs]
                    folders[f"{name}|{rel}"] = lst
                    for q in lst:
                        proj_of[q] = pj

        if not folders:
            messagebox.showwarning("알림", "선택한 폴더에 이미지가 없습니다.")
            return

        self.projects, self.proj_of, self.folders = projects, proj_of, folders
        keys = sorted(self.folders)
        self.folder_keys = ["__all__"] + keys
        multi = len(projects) > 1
        names = ["(전체 이미지)"]
        for k in keys:
            pname, rel = k.split("|", 1)
            if rel == ".":
                names.append(pname)
            else:
                names.append(f"{pname}/{rel}" if multi else rel)
        self.folderSelect["values"] = names
        self.folderSelect.current(0)

        self.annotations.clear()
        self.notes.clear()
        self.done.clear()
        self.passed.clear()
        self.auto_pred.clear()
        for k in keys:
            for p in self.folders[k]:
                if self.P(p)["out_dir"] and os.path.exists(self.out_paths(p)["label"]):
                    self.done.add(p)
        self.passed = set(self.done)

        self.idx = -1
        self.load_folder("__all__")

    def on_folder_select(self, _=None):
        i = self.folderSelect.current()
        if i >= 0:
            self.save_current_note()
            self.idx = -1
            self.load_folder(self.folder_keys[i])

    def load_folder(self, key):
        if key == "__all__":
            all_images = [
                p for k in sorted(self.folders) for p in self.folders[k]
            ]
            self.images = list(dict.fromkeys(all_images))
        else:
            self.images = list(dict.fromkeys(self.folders[key]))
        self.refresh_image_list()
        self.update_progress()
        if self.images:
            self.show_image(0)

    def refresh_image_list(self):
        self.imageList.delete(0, "end")
        for i, p in enumerate(self.images):
            self.imageList.insert("end", self.disp(p))
            if p in self.done:
                fg = "#1e8e3e"
            elif self.auto_pred.get(p):      # 일괄 추론 결과가 있고 아직 확인 전
                fg = AUTO_LIST_COLOR
            else:
                fg = "black"
            self.imageList.itemconfig(i, fg=fg)

    def update_progress(self):
        total = len(self.images)
        done = sum(1 for p in self.images if p in self.passed)
        pct = done / total * 100 if total else 0
        self.progressBar["value"] = pct
        self.progressText.config(text=f"{done} / {total}  ({pct:.1f}%)")

    def on_image_list_select(self, _=None):
        sel = self.imageList.curselection()
        if sel and sel[0] != self.idx:
            self.show_image(sel[0])

    # ─────────────────────────────────────────
    # 이미지 표시 / 이동
    # ─────────────────────────────────────────
    def cur_path(self):
        return self.images[self.idx] if 0 <= self.idx < len(self.images) else None

    def cur_boxes(self):
        return self.annotations.setdefault(self.cur_path(), [])

    def save_current_note(self):
        p = self.cur_path()
        if p:
            self.notes[p] = self.issueNote.get("1.0", "end-1c")

    def show_image(self, i):
        self.discard_pending(silent=True)
        self.save_current_note()
        p = self.images[i]
        try:
            cached = self._cache.pop(p, None)
            if cached is not None:
                self.img = cached
            else:
                img = Image.open(p)
                img.load()
                self.img = img.convert("RGB")
        except Exception as e:
            messagebox.showerror("오류", f"이미지를 열 수 없습니다.\n{p}\n{e}")
            return

        self.idx = i
        if p not in self.annotations:
            self.annotations[p], self.notes[p] = self.load_saved(p)
            # 기존 라벨이 없고 저장된 적도 없는 이미지 → 자동 BBox 적용
            if not self.annotations[p] and p not in self.done and self.model is not None:
                preds = self.auto_pred.pop(p, None)          # 일괄 추론 결과 우선
                if preds is None and self.autoOnOpen.get() and not self._batch_running:
                    try:
                        preds = self.predict_image(self.img)
                    except Exception as e:
                        preds = None
                        self.status(f"자동 추론 실패: {e}")
                if preds:
                    self.apply_auto(p, preds)
        self.selected = []
        self.pending = None

        self.issueNote.delete("1.0", "end")
        self.issueNote.insert("1.0", self.notes.get(p, ""))

        self.imageList.selection_clear(0, "end")
        self.imageList.selection_set(i)
        self.imageList.see(i)
        self.set_zoom_mode(False)
        self.fit_view()
        self.refresh_info()
        w, h = self.img.size
        msg = f"{self.disp(p)}   ({w} x {h})   [{i + 1} / {len(self.images)}]"
        n_auto = sum(1 for b in self.cur_boxes() if b.get("auto"))
        if n_auto:
            msg += f"   🤖 자동 BBox {n_auto}개 → 확인/수정 후 저장하세요"
        if any(b["cls"] == UNUSED_CLASS for b in self.cur_boxes()):
            msg += "   ⚠ Class 4(사용 안 함) 박스 있음 → 확인 필요 (자동 삭제 안 함)"
        self.status(msg)
        self.prefetch(i + 1)

    def prefetch(self, j):
        if not 0 <= j < len(self.images):
            return
        q = self.images[j]
        if q in self._cache:
            return

        def work():
            try:
                im = Image.open(q)
                im.load()
                self._cache.clear()
                self._cache[q] = im.convert("RGB")
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def prev_image(self):
        if not self.images:
            return
        if self.idx > 0:
            self.show_image(self.idx - 1)
            self.passed.discard(self.images[self.idx])
            self.update_progress()
        else:
            messagebox.showinfo("알림", "첫 번째 이미지입니다.")

    def next_image(self, last_msg="마지막 이미지입니다."):
        if not self.images:
            return
        cur = self.cur_path()
        if cur:
            self.passed.add(cur)
        self.update_progress()
        if self.idx < len(self.images) - 1:
            self.show_image(self.idx + 1)
        else:
            messagebox.showinfo("알림", last_msg)

    # ─────────────────────────────────────────
    # 좌표 변환 / 뷰(확대·축소·이동)
    # ─────────────────────────────────────────
    def canvas_size(self):
        return max(self.imageCanvas.winfo_width(), 1), max(self.imageCanvas.winfo_height(), 1)

    def to_canvas(self, x, y):
        return x * self.scale + self.ox, y * self.scale + self.oy

    def to_image(self, cx, cy):
        return (cx - self.ox) / self.scale, (cy - self.oy) / self.scale

    def clamp_img_pt(self, x, y):
        iw, ih = self.img.size
        return min(max(x, 0), iw), min(max(y, 0), ih)

    def fit_view(self):
        if not self.img:
            return
        cw, ch = self.canvas_size()
        iw, ih = self.img.size
        s = min(cw / iw, ch / ih)
        self.fit_scale = self.scale = s
        self.ox = (cw - iw * s) / 2
        self.oy = (ch - ih * s) / 2
        self.is_fit = True
        self.render()

    def clamp_view(self):
        cw, ch = self.canvas_size()
        iw, ih = self.img.size
        dw, dh = iw * self.scale, ih * self.scale
        self.ox = (cw - dw) / 2 if dw <= cw else min(0, max(cw - dw, self.ox))
        self.oy = (ch - dh) / 2 if dh <= ch else min(0, max(ch - dh, self.oy))

    def zoom_at(self, factor, cx, cy):
        if not self.img:
            return
        new = min(max(self.scale * factor, self.fit_scale), self.fit_scale * MAX_ZOOM)
        if new <= self.fit_scale * 1.0001:
            self.fit_view()
            return
        self.ox = cx - (cx - self.ox) * new / self.scale
        self.oy = cy - (cy - self.oy) * new / self.scale
        self.scale = new
        self.is_fit = False
        self.clamp_view()
        self.render()

    def zoom_to_rect(self, x1, y1, x2, y2):
        cw, ch = self.canvas_size()
        s = min(cw / (x2 - x1), ch / (y2 - y1))
        s = min(max(s, self.fit_scale), self.fit_scale * MAX_ZOOM)
        self.scale = s
        self.ox = cw / 2 - (x1 + x2) / 2 * s
        self.oy = ch / 2 - (y1 + y2) / 2 * s
        self.is_fit = s <= self.fit_scale * 1.0001
        self.clamp_view()
        self.render()

    def reset_view(self):
        self.set_zoom_mode(False)
        self.fit_view()

    def zoom_out(self):
        cw, ch = self.canvas_size()
        self.zoom_at(1 / 1.25, cw / 2, ch / 2)

    def set_zoom_mode(self, on):
        self.zoom_mode = on
        self.zoomBtn.config(relief="sunken" if on else "raised",
                            bg="#cfe3ff" if on else "SystemButtonFace"
                            if os.name == "nt" else "#d9d9d9")
        self.imageCanvas.config(cursor="plus" if on else "crosshair")

    def toggle_zoom_mode(self):
        if not self.img:
            return
        self.set_zoom_mode(not self.zoom_mode)
        if self.zoom_mode:
            self.status("확대 모드: 확대할 영역을 드래그로 지정하세요. (Esc: 취소)")

    def on_canvas_resize(self, _=None):
        if not self.img:
            return
        if self.is_fit:
            self.fit_view()
        else:
            self.clamp_view()
            self.render()

    def visible_rect(self, margin=0):
        cw, ch = self.canvas_size()
        iw, ih = self.img.size
        x0, y0 = self.clamp_img_pt(*self.to_image(-margin, -margin))
        x1, y1 = self.clamp_img_pt(*self.to_image(cw + margin, ch + margin))
        x0, y0 = int(x0), int(y0)
        x1, y1 = min(iw, math.ceil(x1)), min(ih, math.ceil(y1))
        if x1 <= x0 or y1 <= y0:
            return None
        return x0, y0, x1, y1

    # ─────────────────────────────────────────
    # 그리기
    # ─────────────────────────────────────────
    def color_of(self, cls):
        if cls is None:
            return PENDING_COLOR
        if cls == ISSUE_ID:
            return ISSUE_COLOR
        return COLORS[cls % len(COLORS)]

    def name_of(self, cls):
        if cls is None:
            return "클래스 선택 필요"
        if cls == ISSUE_ID:
            return "이슈"
        return f"{cls}: {CLASS_NAMES[cls]}" if cls < len(CLASS_NAMES) else str(cls)

    def is_selected(self, b):
        return any(b is s for s in self.selected)

    def render(self, margin=0):
        c = self.imageCanvas
        c.delete("all")
        self.temp_rect = None
        if not self.img:
            return
        vr = self.visible_rect(margin)
        if vr:
            x0, y0, x1, y1 = vr
            s = self.scale
            dw = max(1, round((x1 - x0) * s))
            dh = max(1, round((y1 - y0) * s))
            method = Image.NEAREST if s >= 3 else Image.BILINEAR
            region = self.img.crop(vr).resize((dw, dh), method)
            self.tkimg = ImageTk.PhotoImage(region)
            cx, cy = self.to_canvas(x0, y0)
            c.create_image(cx, cy, image=self.tkimg, anchor="nw", tags="img")
        self.draw_boxes()

    def draw_boxes(self):
        c = self.imageCanvas
        for b in self.cur_boxes():
            x1, y1 = self.to_canvas(b["x1"], b["y1"])
            x2, y2 = self.to_canvas(b["x2"], b["y2"])
            color = self.color_of(b["cls"])
            sel = self.is_selected(b)
            opt = {"outline": color, "width": 3 if sel else 2, "tags": "box"}
            if b["cls"] is None or b["cls"] == ISSUE_ID:
                opt["dash"] = (6, 3)
            elif b.get("auto"):                       # 자동 BBox: 점선 (확인 전)
                opt["dash"] = (4, 3)
            c.create_rectangle(x1, y1, x2, y2, **opt)

            label = self.name_of(b["cls"])
            if b.get("auto"):
                label = f"AI {b.get('conf', 0) * 100:.0f}%  {label}"
            t = c.create_text(x1 + 3, y1 - 2, text=label,
                              anchor="sw", fill="white", font=FONT_B, tags="box")
            bg = c.create_rectangle(c.bbox(t), fill=color, outline=color, tags="box")
            c.tag_raise(t, bg)

            if sel:
                for hx, hy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                    c.create_rectangle(hx - 4, hy - 4, hx + 4, hy + 4,
                                       fill="white", outline=color, tags="box")

    def redraw_boxes(self):
        if not self.img:
            return
        self.imageCanvas.delete("box")
        self.draw_boxes()

    def hit_test(self, cx, cy):
        x, y = self.to_image(cx, cy)
        hits = [b for b in self.cur_boxes()
                if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]]
        if not hits:
            return None
        return min(hits, key=lambda b: (b["x2"] - b["x1"]) * (b["y2"] - b["y1"]))

    # ─────────────────────────────────────────
    # 마우스 이벤트
    # ─────────────────────────────────────────
    def handle_at(self, cx, cy):
        if len(self.selected) != 1 or self.zoom_mode or not self.img:
            return None
        b = self.selected[0]
        for name, (px, py) in (("nw", (b["x1"], b["y1"])), ("ne", (b["x2"], b["y1"])),
                               ("sw", (b["x1"], b["y2"])), ("se", (b["x2"], b["y2"]))):
            hx, hy = self.to_canvas(px, py)
            if abs(cx - hx) <= HANDLE_R and abs(cy - hy) <= HANDLE_R:
                return name
        return None

    def on_motion(self, e):
        if self.mode:
            return
        want = "sizing" if self.handle_at(e.x, e.y) else ("plus" if self.zoom_mode else "crosshair")
        if want != self._cursor:
            self.imageCanvas.config(cursor=want)
            self._cursor = want

    def on_press(self, e):
        if not self.img:
            return
        self.imageCanvas.focus_set()
        self.discard_pending()

        hd = self.handle_at(e.x, e.y)
        if hd and not (e.state & (SHIFT | CTRL)):
            self.mode, self.resize_hd = "resize", hd
            self.status("크기 조절 중... (놓으면 확정)")
            return

        if e.state & SHIFT:
            if self.is_fit:
                self.mode = None
                self.status("원상태에서는 이미지를 이동할 수 없습니다.")
                return
            self.mode = "pan"
            self.press_xy = (e.x, e.y)
            self.imageCanvas.config(cursor="fleur")
            self.render(margin=max(self.canvas_size()) // 2)
            return

        if e.state & CTRL:
            self.mode = None
            b = self.hit_test(e.x, e.y)
            if b:
                if self.is_selected(b):
                    self.selected = [s for s in self.selected if s is not b]
                else:
                    self.selected.append(b)
                self.redraw_boxes()
                self.refresh_info()
            return

        self.press_xy = (e.x, e.y)
        self.mode = "zoomsel" if self.zoom_mode else "press"

    def on_drag(self, e):
        if self.mode == "pan":
            px, py = self.press_xy
            ox0, oy0 = self.ox, self.oy
            self.ox += e.x - px
            self.oy += e.y - py
            self.press_xy = (e.x, e.y)
            self.clamp_view()
            self.imageCanvas.move("all", self.ox - ox0, self.oy - oy0)
            return

        if self.mode == "resize":
            b = self.selected[0]
            x, y = self.clamp_img_pt(*self.to_image(e.x, e.y))
            hd = self.resize_hd
            if "w" in hd:
                b["x1"] = min(x, b["x2"] - 2)
            else:
                b["x2"] = max(x, b["x1"] + 2)
            if "n" in hd:
                b["y1"] = min(y, b["y2"] - 2)
            else:
                b["y2"] = max(y, b["y1"] + 2)
            self.redraw_boxes()
            return

        if self.mode not in ("press", "draw", "zoomsel"):
            return
        px, py = self.press_xy
        if self.mode == "press":
            if abs(e.x - px) < 4 and abs(e.y - py) < 4:
                return
            self.mode = "draw"

        x0, y0 = self.to_canvas(*self.clamp_img_pt(*self.to_image(px, py)))
        x1, y1 = self.to_canvas(*self.clamp_img_pt(*self.to_image(e.x, e.y)))
        if self.temp_rect:
            self.imageCanvas.coords(self.temp_rect, x0, y0, x1, y1)
        else:
            color = "white" if self.mode == "zoomsel" else PENDING_COLOR
            self.temp_rect = self.imageCanvas.create_rectangle(
                x0, y0, x1, y1, outline=color, width=2, dash=(5, 3))

    def on_release(self, e):
        mode, self.mode = self.mode, None
        if self.temp_rect:
            self.imageCanvas.delete(self.temp_rect)
            self.temp_rect = None
        if mode == "pan":
            self.imageCanvas.config(cursor="crosshair")
            self.render()
            return
        if mode == "resize":
            # 사람이 크기를 수정한 박스 → 자동 표시 해제(확인된 박스)
            if self.selected:
                self.selected[0]["auto"] = False
            self.redraw_boxes()
            self.refresh_info()
            self.status("크기 조절 완료")
            return

        if mode in ("draw", "zoomsel"):
            ax, ay = self.clamp_img_pt(*self.to_image(*self.press_xy))
            bx, by = self.clamp_img_pt(*self.to_image(e.x, e.y))
            x1, x2 = sorted((ax, bx))
            y1, y2 = sorted((ay, by))

            if mode == "zoomsel":
                if (x2 - x1) * self.scale >= 8 and (y2 - y1) * self.scale >= 8:
                    self.set_zoom_mode(False)
                    self.zoom_to_rect(x1, y1, x2, y2)
                    self.status("확대 완료  |  Shift+드래그: 이동  |  원상태: 전체 보기")
                else:
                    self.redraw_boxes()
                return

            if x2 - x1 >= 2 and y2 - y1 >= 2:
                b = {"cls": None, "x1": x1, "y1": y1, "x2": x2, "y2": y2}
                self.cur_boxes().append(b)
                self.pending = b
                self.selected = [b]
                self.classList.selection_clear(0, "end")
                self.status("오른쪽 '클래스 분류'에서 클래스를 선택하세요. (선택하지 않으면 박스가 삭제됩니다)")
            self.redraw_boxes()
            self.refresh_info()
            return

        if mode == "press":
            b = self.hit_test(e.x, e.y)
            self.selected = [b] if b else []
            self.classList.selection_clear(0, "end")
            if b and b["cls"] is not None:
                i = len(CLASS_NAMES) if b["cls"] == ISSUE_ID else b["cls"]
                self.classList.selection_set(i)
            self.redraw_boxes()
            self.refresh_info()

    def on_escape(self, _=None):
        if self.zoom_mode:
            self.set_zoom_mode(False)
            self.status("확대 모드 취소")
        else:
            self.discard_pending()

    # ─────────────────────────────────────────
    # 클래스 지정 / 삭제
    # ─────────────────────────────────────────
    def on_class_select(self, _=None):
        sel = self.classList.curselection()
        if not sel or not self.img:
            return
        i = sel[0]
        if i == UNUSED_CLASS:
            messagebox.showwarning("알림", "4번 클래스는 사용하지 않습니다.\n판단이 어려우면 이슈 노트에 기록해 주세요.")
            self.classList.selection_clear(0, "end")
            return
        cls = ISSUE_ID if i == len(CLASS_NAMES) else i
        if self.pending:
            self.pending["cls"] = cls
            self.pending = None
            self.status(f"클래스 지정: {self.name_of(cls)}")
        elif self.selected:
            for b in self.selected:
                b["cls"] = cls
                b["auto"] = False      # 사람이 클래스를 지정한 박스 → 확인된 박스
            self.status(f"선택한 박스 {len(self.selected)}개 → {self.name_of(cls)}")
        else:
            return
        self.redraw_boxes()
        self.refresh_info()
        self.imageCanvas.focus_set()

    def discard_pending(self, silent=False):
        if not self.pending:
            return False
        p = self.pending
        self.pending = None
        boxes = self.cur_boxes()
        boxes[:] = [b for b in boxes if b is not p]
        self.selected = [s for s in self.selected if s is not p]
        if not silent:
            self.status("클래스를 선택하지 않아 박스가 삭제되었습니다.")
            self.redraw_boxes()
            self.refresh_info()
        return True

    def delete_selected(self):
        if not self.img:
            return
        if not self.selected:
            messagebox.showinfo("알림", "삭제할 박스를 먼저 선택하세요.\n(Ctrl+클릭으로 여러 개 선택)")
            return
        n = len(self.selected)
        if not messagebox.askyesno("경고",
                                   f"선택한 BBox {n}개를 삭제합니다.\n"
                                   f"삭제 후에는 되돌릴 수 없습니다. 계속하시겠습니까?",
                                   icon="warning"):
            return
        boxes = self.cur_boxes()
        boxes[:] = [b for b in boxes if not self.is_selected(b)]
        if self.pending and self.is_selected(self.pending):
            self.pending = None
        self.selected = []
        self.redraw_boxes()
        self.refresh_info()
        self.status(f"박스 {n}개 삭제됨")

    # ─────────────────────────────────────────
    # 크기 정보 패널
    # ─────────────────────────────────────────
    def box_to_yolo(self, b):
        iw, ih = self.img.size
        return ((b["x1"] + b["x2"]) / 2 / iw, (b["y1"] + b["y2"]) / 2 / ih,
                (b["x2"] - b["x1"]) / iw, (b["y2"] - b["y1"]) / ih)

    def yolo_to_box(self, cls, xc, yc, w, h):
        iw, ih = self.img.size
        return {"cls": cls,
                "x1": (xc - w / 2) * iw, "y1": (yc - h / 2) * ih,
                "x2": (xc + w / 2) * iw, "y2": (yc + h / 2) * ih}

    def refresh_info(self):
        self.labelList.delete(*self.labelList.get_children())
        if self.img:
            for i, b in enumerate(self.cur_boxes()):
                xc, yc, w, h = self.box_to_yolo(b)
                cls = "이슈" if b["cls"] == ISSUE_ID else ("?" if b["cls"] is None else b["cls"])
                if b.get("auto"):
                    cls = f"{cls}*"        # * = 자동 BBox(미확인)
                self.labelList.insert("", "end", iid=str(i),
                                      values=(i + 1, cls, f"{xc:.4f}", f"{yc:.4f}", f"{w:.4f}", f"{h:.4f}"))
                if self.is_selected(b):
                    self.labelList.selection_add(str(i))
        self.update_detail()

    def update_detail(self):
        vals = {k: "" for k in self.labelDetail}
        if self.selected and self.img:
            b = self.selected[0]
            xc, yc, w, h = self.box_to_yolo(b)
            vals = {"Class": self.name_of(b["cls"]),
                    "X(중심)": f"{xc:.4f}", "Y(중심)": f"{yc:.4f}",
                    "너비": f"{w:.4f}", "높이": f"{h:.4f}"}
        for k, v in vals.items():
            self.labelDetail[k].set(v)

    def on_tree_select(self, _=None):
        boxes = self.cur_boxes() if self.img else []
        sel = [boxes[int(i)] for i in self.labelList.selection() if int(i) < len(boxes)]
        if [id(b) for b in sel] == [id(b) for b in self.selected]:
            return
        self.selected = sel
        self.redraw_boxes()
        self.update_detail()

    # ─────────────────────────────────────────
    # 확대 이미지 새 창
    # ─────────────────────────────────────────
    def open_zoom_window(self):
        if not self.img:
            return
        vr = self.visible_rect()
        if not vr:
            return
        x0, y0, x1, y1 = vr
        crop = self.img.crop(vr)
        f = min(900 / crop.width, 700 / crop.height)
        size = (max(1, round(crop.width * f)), max(1, round(crop.height * f)))
        crop = crop.resize(size, Image.NEAREST if f >= 3 else Image.BICUBIC)

        d = ImageDraw.Draw(crop)
        for b in self.cur_boxes():
            rx1, ry1 = (b["x1"] - x0) * f, (b["y1"] - y0) * f
            rx2, ry2 = (b["x2"] - x0) * f, (b["y2"] - y0) * f
            color = self.color_of(b["cls"])
            d.rectangle((rx1, ry1, rx2, ry2), outline=color, width=2)
            tag = "ISSUE" if b["cls"] == ISSUE_ID else ("?" if b["cls"] is None else str(b["cls"]))
            d.text((rx1 + 3, ry1 + 2), tag, fill=color)

        win = tk.Toplevel(self.root)
        win.title(f"확대 이미지 - {os.path.basename(self.cur_path())}  ({x0},{y0})-({x1},{y1})")
        win.photo = ImageTk.PhotoImage(crop)
        tk.Label(win, image=win.photo, bg="#2b2b2b").pack()

    # ─────────────────────────────────────────
    # 자동 추론 (YOLO best.pt)
    # ─────────────────────────────────────────
    def conf_value(self):
        try:
            return min(max(float(self.confVar.get()), 0.01), 0.99)
        except ValueError:
            return 0.25

    def load_model(self):
        """학습된 best.pt 를 불러온다. (ultralytics 는 이 시점에 처음 import)"""
        path = filedialog.askopenfilename(
            title="학습된 YOLO 모델 선택 (best.pt)",
            filetypes=[("YOLO 모델", "*.pt"), ("모든 파일", "*.*")])
        if not path:
            return False
        try:
            from ultralytics import YOLO
        except ImportError:
            messagebox.showerror("ultralytics 없음",
                                 "자동 추론에는 ultralytics 패키지가 필요합니다.\n\n"
                                 "    pip install ultralytics\n\n"
                                 "설치 후 다시 시도하세요.")
            return False
        self.status("모델을 불러오는 중입니다...")
        self.root.update_idletasks()
        try:
            model = YOLO(path)
        except Exception as e:
            messagebox.showerror("모델 오류", f"모델을 불러오지 못했습니다.\n{e}")
            self.status("모델 불러오기 실패")
            return False
        self.model = model
        self.model_name = os.path.basename(path)
        self.modelLabel.config(text=self.model_name)
        names = getattr(model, "names", None) or {}
        if len(names) != len(CLASS_NAMES):
            messagebox.showwarning(
                "클래스 수 확인",
                f"모델 클래스 수({len(names)})가 프로그램 클래스 수({len(CLASS_NAMES)})와 다릅니다.\n"
                f"클래스 번호(0~{len(CLASS_NAMES) - 1})가 서로 같은지 확인하세요.\n"
                f"범위를 벗어나거나 4번(사용 안 함)인 결과는 무시됩니다.")
        self.status(f"모델 로드 완료: {self.model_name}")
        return True

    def ensure_model(self):
        if self.model is not None:
            return True
        return self.load_model() and self.model is not None

    def predict_image(self, im, conf=None):
        """PIL(RGB) 이미지 1장 추론 → [(cls, (xc,yc,w,h) 정규화, conf)]"""
        conf = self.conf_value() if conf is None else conf
        iw, ih = im.size
        res = self.model.predict(im, conf=conf, verbose=False)[0]
        out = []
        if res.boxes is None or len(res.boxes) == 0:
            return out
        xyxy = res.boxes.xyxy.cpu().numpy()
        cls = res.boxes.cls.cpu().numpy().astype(int)
        cfs = res.boxes.conf.cpu().numpy()
        for (x1, y1, x2, y2), c, s in zip(xyxy, cls, cfs):
            c = int(c)
            if c == UNUSED_CLASS or not 0 <= c < len(CLASS_NAMES):
                continue
            out.append((c, (((x1 + x2) / 2) / iw, ((y1 + y2) / 2) / ih,
                            (x2 - x1) / iw, (y2 - y1) / ih), float(s)))
        return out

    def apply_auto(self, p, preds):
        """현재 이미지(p)에 추론 결과를 자동 BBox 로 반영. 이전 자동 박스는 교체, 수동 박스는 유지."""
        boxes = self.annotations.setdefault(p, [])
        boxes[:] = [b for b in boxes if not b.get("auto")]
        for cls, (xc, yc, w, h), conf in preds:
            b = self.yolo_to_box(cls, xc, yc, w, h)
            b["auto"] = True
            b["conf"] = conf
            boxes.append(b)
        return len(preds)

    def run_auto_current(self):
        if not self.img:
            messagebox.showinfo("알림", "먼저 폴더를 열어 이미지를 선택하세요.")
            return
        if self._batch_running:
            messagebox.showinfo("알림", "일괄 추론 중에는 사용할 수 없습니다.")
            return
        if not self.ensure_model():
            return
        p = self.cur_path()
        self.discard_pending()
        self.status("추론 중...")
        self.root.update_idletasks()
        try:
            preds = self.predict_image(self.img)
        except Exception as e:
            messagebox.showerror("추론 오류", str(e))
            return
        self.auto_pred.pop(p, None)
        n = self.apply_auto(p, preds)
        self.selected = []
        self.redraw_boxes()
        self.refresh_info()
        self.status(f"자동 BBox {n}개 생성 (conf ≥ {self.conf_value():.2f}) → 확인/수정 후 저장하세요")

    # ── 일괄 추론 ──
    def toggle_batch(self):
        if self._batch_running:
            self._batch_stop = True
            self.status("일괄 추론 중지 요청...")
            return
        if not self.images:
            messagebox.showinfo("알림", "먼저 폴더를 열어 주세요.")
            return
        if not self.ensure_model():
            return
        # 대상: 저장된 적 없고, 기존 라벨도 없고, 아직 열어보지 않은 이미지
        targets = [p for p in self.images
                   if p not in self.done and p not in self.annotations
                   and p not in self.auto_pred and not self.raw_label_path(p)]
        if not targets:
            messagebox.showinfo("알림", "추론할 미라벨 이미지가 없습니다.")
            return
        if not messagebox.askyesno("일괄 추론",
                                   f"현재 목록의 미라벨 이미지 {len(targets)}장을 추론합니다.\n"
                                   f"(결과는 목록에 주황색으로 표시되며, 이미지를 열면 자동 BBox로 나타납니다.)\n\n"
                                   f"진행하시겠습니까?"):
            return
        self._batch_running = True
        self._batch_stop = False
        self._batch_total = len(targets)
        self._batch_n = 0
        self.autoBatchBtn.config(text="일괄 추론 중지")
        self.autoCurBtn.config(state="disabled")
        threading.Thread(target=self._batch_work, args=(targets, self.conf_value()),
                         daemon=True).start()
        self.root.after(300, self._batch_poll)

    def _batch_work(self, targets, conf):
        try:
            for p in targets:
                if self._batch_stop:
                    break
                try:
                    im = Image.open(p)
                    im.load()
                    self.auto_pred[p] = self.predict_image(im.convert("RGB"), conf)
                except Exception:
                    pass
                self._batch_n += 1
        finally:
            self._batch_running = False

    def _batch_poll(self):
        if self._batch_running:
            self.status(f"일괄 추론 중... {self._batch_n} / {self._batch_total}")
            self.root.after(300, self._batch_poll)
            return
        self.autoBatchBtn.config(text="미라벨 이미지 일괄 추론")
        self.autoCurBtn.config(state="normal")
        found = sum(1 for p in self.images if self.auto_pred.get(p))
        # 목록 색상 갱신 (현재 선택 유지)
        self.refresh_image_list()
        if 0 <= self.idx < len(self.images):
            self.imageList.selection_set(self.idx)
        stopped = " (중지됨)" if self._batch_stop else ""
        self.status(f"일괄 추론 완료{stopped}: {self._batch_n}장 처리, "
                    f"검출된 이미지 {found}장 (주황색 표시) → 열어서 확인/수정 후 저장하세요")

    # ─────────────────────────────────────────
    # 저장 / 불러오기
    # ─────────────────────────────────────────
    def default_out_dir(self, pj):
        parent = os.path.dirname(pj["proj"])
        return os.path.join(parent, os.path.basename(pj["proj"]) + "_labeled")

    def out_paths(self, p):
        pj = self.P(p)
        od = pj["out_dir"]
        rel = self.rel_of(p)
        stem = os.path.splitext(rel)[0]
        issue_dir = os.path.join(od, "issues", stem)
        # ────────── 수정: 저장되는 라벨과 Class4 체크 파일을 .csv 로 변경 ──────────
        return {"label": os.path.join(od, "labels", stem + ".csv"),
                "image": os.path.join(od, "images", rel),
                "issue_dir": issue_dir,
                "issue_img": os.path.join(issue_dir, os.path.basename(p)),
                "issue_txt": os.path.join(issue_dir, os.path.basename(stem) + "_issue.txt"),
                "c4_dir": os.path.join(od, "class4_check", stem),
                "c4_img": os.path.join(od, "class4_check", stem, os.path.basename(p)),
                "c4_txt": os.path.join(od, "class4_check", stem, os.path.basename(stem) + ".csv")}

    def raw_label_path(self, p):
        pj = self.P(p)
        rel = os.path.splitext(self.rel_of(p))[0]
        q = pj["by_rel"].get(rel) or pj["by_name"].get(os.path.basename(rel))
        if q:
            return q
        # ────────── 수정: 기존 .txt와 새로운 .csv 를 모두 찾아오도록 개선 ──────────
        base_csv = os.path.splitext(p)[0] + ".csv"
        base_txt = os.path.splitext(p)[0] + ".txt"
        alt_csv = base_csv.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        alt_txt = base_txt.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        for q in (alt_csv, base_csv, alt_txt, base_txt):
            if os.path.exists(q):
                return q
        return None

    def read_label_file(self, path):
        boxes = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                # ────────── 수정: 기존 공백 분리 뿐 아니라 CSV의 쉼표도 정상 분리하도록 수정 ──────────
                v = line.replace(',', ' ').split()
                if len(v) == 5:
                    try:
                        boxes.append(self.yolo_to_box(int(v[0]), *map(float, v[1:])))
                    except ValueError:
                        pass
        return boxes

    def load_saved(self, p):
        boxes, note = [], ""
        raw = self.raw_label_path(p)
        if not self.P(p)["out_dir"]:
            return (self.read_label_file(raw) if raw else boxes), note
        paths = self.out_paths(p)
        if not os.path.exists(paths["label"]) and raw:
            boxes = self.read_label_file(raw)
        if os.path.exists(paths["label"]):
            with open(paths["label"], encoding="utf-8") as f:
                for line in f:
                    # ────────── 수정: 저장된 csv 파일을 읽을 때 쉼표를 공백으로 치환 후 파싱 ──────────
                    v = line.replace(',', ' ').split()
                    if len(v) == 5:
                        boxes.append(self.yolo_to_box(int(v[0]), *map(float, v[1:])))
        if os.path.exists(paths["issue_txt"]):
            section, lines = None, []
            with open(paths["issue_txt"], encoding="utf-8") as f:
                for line in f.read().splitlines():
                    if line.startswith("[이슈 박스]"):
                        section = "box"
                    elif line.startswith("[이슈 내용]"):
                        section = "note"
                    elif line.startswith("작성자:") and not self.workerVar.get():
                        self.workerVar.set(line.split(":", 1)[1].strip())
                    elif section == "box":
                        v = line.replace(',', ' ').split()
                        if len(v) == 4:
                            boxes.append(self.yolo_to_box(ISSUE_ID, *map(float, v)))
                    elif section == "note":
                        lines.append(line)
            note = "\n".join(lines).strip()
        return boxes, note

    def ensure_out_dir(self, pj):
        if pj["out_dir"]:
            return
        pj["out_dir"] = self.default_out_dir(pj)
        for sub in ("images", "labels", "issues", "class4_check"):
            os.makedirs(os.path.join(pj["out_dir"], sub), exist_ok=True)
        with open(os.path.join(pj["out_dir"], "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(CLASS_NAMES) + "\n")
        messagebox.showinfo("저장 폴더 생성",
                            f"첫 저장이므로 저장 폴더를 생성했습니다.\n\n{pj['out_dir']}\n\n"
                            f"이후 저장되는 이미지와 라벨은 이 폴더에 저장됩니다.")

    @staticmethod
    def copy_if_needed(src, dst):
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            return
        shutil.copy2(src, dst)

    def save(self):
        p = self.cur_path()
        if not p or not self.img:
            return False
        self.discard_pending()
        self.save_current_note()
        try:
            self.ensure_out_dir(self.P(p))
            paths = self.out_paths(p)
            boxes = self.cur_boxes()

            # 1) 라벨(YOLO) + 이미지
            os.makedirs(os.path.dirname(paths["label"]), exist_ok=True)
            os.makedirs(os.path.dirname(paths["image"]), exist_ok=True)
            with open(paths["label"], "w", encoding="utf-8") as f:
                for b in boxes:
                    if b["cls"] is None or b["cls"] == ISSUE_ID:
                        continue
                    xc, yc, w, h = self.box_to_yolo(b)
                    # ────────── 수정: 공백 대신 쉼표(,)를 사용하여 CSV 형식으로 저장 ──────────
                    f.write(f"{b['cls']},{xc:.6f},{yc:.6f},{w:.6f},{h:.6f}\n")
            self.copy_if_needed(p, paths["image"])

            # 1-2) Class 4 박스가 있으면 삭제하지 않고 별도 폴더에도 저장 (확인용)
            c4_boxes = [b for b in boxes if b["cls"] == UNUSED_CLASS]
            if c4_boxes:
                os.makedirs(paths["c4_dir"], exist_ok=True)
                self.copy_if_needed(p, paths["c4_img"])
                with open(paths["c4_txt"], "w", encoding="utf-8") as f:
                    for b in boxes:
                        if b["cls"] is None or b["cls"] == ISSUE_ID:
                            continue
                        xc, yc, w, h = self.box_to_yolo(b)
                        # ────────── 수정: 여기도 쉼표(,)로 저장하도록 수정 ──────────
                        f.write(f"{b['cls']},{xc:.6f},{yc:.6f},{w:.6f},{h:.6f}\n")
            elif os.path.isdir(paths["c4_dir"]):      
                shutil.rmtree(paths["c4_dir"], ignore_errors=True)

            # 2) 이슈: 이미지 + txt 를 하나의 폴더로 (이슈는 텍스트 형식을 유지합니다)
            issue_boxes = [b for b in boxes if b["cls"] == ISSUE_ID]
            note = self.notes.get(p, "").strip()
            if issue_boxes or note:
                os.makedirs(paths["issue_dir"], exist_ok=True)
                self.copy_if_needed(p, paths["issue_img"])
                with open(paths["issue_txt"], "w", encoding="utf-8") as f:
                    f.write(f"작성자: {self.workerVar.get().strip()}\n")
                    f.write(f"이미지: {self.disp(p)}\n")
                    f.write(f"저장시각: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
                    f.write("[이슈 박스] (x_center y_center width height)\n")
                    for b in issue_boxes:
                        f.write("{:.6f} {:.6f} {:.6f} {:.6f}\n".format(*self.box_to_yolo(b)))
                    f.write("[이슈 내용]\n")
                    f.write(note + "\n")
        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

        # 저장 = 사람이 확인한 최종 라벨 → 자동 BBox 표시 해제
        for b in self.cur_boxes():
            b["auto"] = False
        self.auto_pred.pop(p, None)
        self.redraw_boxes()
        self.refresh_info()

        self.done.add(p)
        self.imageList.itemconfig(self.idx, fg="#1e8e3e")
        self.status(f"저장 완료: {self.disp(p)}")
        return True

    def save_and_next(self):
        if not self.save():
            return
        self.next_image("마지막 이미지까지 저장했습니다.")


if __name__ == "__main__":
    root = tk.Tk()
    LabelingApp(root)
    root.mainloop()