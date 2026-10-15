"""화면 배치(UI 구성) 전담 — 위치·크기 변경은 이 파일만 수정"""
import tkinter as tk
from tkinter import ttk

from src.config import (COLORS, LOCKED_CLASS_COLOR, STAGES, STAGE_FILTERS, DEFAULT_CONF,
                        SCENE_TYPES, REVIEW_REASONS,
                    FONT, FONT_B, FONT_S)
from src.ui.panels import PersonPanel, ReviewPanel, HistoryPanel, ScenePanel
from src.bbox.workflow import people_labels
from src.validation.rules import list_ids, display_name, is_selectable


class LayoutMixin:
    def build_ui(self):
        r = self.root
        r.columnconfigure(1, weight=1)
        r.rowconfigure(1, weight=1)

        self._build_top_bar(r)        # [0,0~1] 사이드바 버튼 + 진행률
        self._build_sidebar(r)        # [1,0]   폴더 / 이미지 목록
        self._build_center(r)         # [1,1]   캔버스 + 하단 도구
        self._build_right_panel(r)    # [0~1,2] 오른쪽 패널

        # [2,*] 상태 표시줄
        self.statusBar = tk.Label(r, text="'폴더 열기'로 이미지 폴더를 선택하세요.",
                                  font=FONT, anchor="w", fg="#444")
        self.statusBar.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 4))

    # ── 상단 바 ──
    def _build_top_bar(self, r):
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

    # ── 왼쪽 사이드바 ──
    def _build_sidebar(self, r):
        self.sidebar = tk.Frame(r)
        self.sidebar.grid(row=1, column=0, sticky="ns", padx=(6, 0), pady=4)

        lf_folder = tk.LabelFrame(self.sidebar, text="폴더 분류", font=FONT_B)
        lf_folder.pack(fill="x")
        self.openFolderBtn = tk.Button(lf_folder, text="폴더 열기", font=FONT,
                                       command=self.open_folder)
        self.openFolderBtn.pack(fill="x", padx=4, pady=(4, 2))
        # 저장 위치 표시 + [변경] (기본: 데이터 폴더의 images·labels/train/train_done)
        outRow = tk.Frame(lf_folder)
        outRow.pack(fill="x", padx=4)
        self.outDirChangeBtn = tk.Button(outRow, text="변경", font=FONT_S, padx=4, pady=0,
                                         command=self.change_out_dir)
        self.outDirChangeBtn.pack(side="right", anchor="n")
        self.outDirLabel = tk.Label(outRow, text="저장 위치: -", font=FONT_S, fg="#666",
                                    anchor="w", justify="left", wraplength=150)
        self.outDirLabel.pack(side="left", fill="x", expand=True)
        self.folderSelect = ttk.Combobox(lf_folder, state="readonly", font=FONT)
        self.folderSelect.pack(fill="x", padx=4, pady=(2, 6))
        self.folderSelect.bind("<<ComboboxSelected>>", self.on_folder_select)

        # (전체 이미지)를 골랐을 때만 보이는 단계 선택: 전체 / 1차 / 2차 / review / final
        self.stageRow = tk.Frame(lf_folder)
        tk.Label(self.stageRow, text="단계", font=FONT_B).pack(side="left", padx=(0, 4))
        self.stageSelect = ttk.Combobox(self.stageRow, state="readonly", font=FONT, width=14,
                                        values=[name for _, name in STAGE_FILTERS])
        self.stageSelect.pack(side="left", fill="x", expand=True)
        self.stageSelect.current(0)
        self.stageSelect.bind("<<ComboboxSelected>>", self.on_stage_filter_select)

        lf_list = tk.LabelFrame(self.sidebar, text="폴더 내 이미지", font=FONT_B)
        lf_list.pack(fill="both", expand=True, pady=(6, 0))
        sb = tk.Scrollbar(lf_list)
        sb.pack(side="right", fill="y")
        self.imageList = tk.Listbox(lf_list, width=24, font=FONT,
                                    exportselection=False, yscrollcommand=sb.set)
        self.imageList.pack(side="left", fill="both", expand=True)
        sb.config(command=self.imageList.yview)
        self.imageList.bind("<<ListboxSelect>>", self.on_image_list_select)

    # ── 가운데: 캔버스 + 하단 도구 ──
    def _build_center(self, r):
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
        self._build_stats_view(center)        # 단계 보기 '그래프' — 같은 자리에 겹쳐 두고 평소엔 숨김 (stats_mixin)

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
        self.deleteBtn = tk.Button(bottom, text="삭제", font=FONT, fg="#c62828",
                                   command=self.delete_selected)
        self.deleteBtn.pack(side="right")

    # ── 오른쪽 패널 (위 → 아래 순서 = 호출 순서, nav 는 맨 아래 고정) ──
    def _build_right_panel(self, r):
        right = tk.Frame(r)
        right.grid(row=0, column=2, rowspan=2, sticky="ns", padx=(0, 6), pady=6)
        self._build_nav(right)            # side="bottom" 이라 먼저 pack
        self._build_class_panel(right)
        self._build_auto_panel(right)
        self._build_lower_panel(right)

    def _build_nav(self, right):
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

    def _build_class_panel(self, right):
        upper = tk.Frame(right)
        upper.pack(side="top", fill="x")

        lf_cls = tk.LabelFrame(upper, text="클래스 분류", font=FONT_B)
        lf_cls.grid(row=0, column=0, sticky="nsew")
        self.classList = tk.Listbox(lf_cls, width=14, height=14, font=FONT,
                                    exportselection=False)
        self.classList.pack(fill="both", expand=True, padx=4, pady=4)
        # 숨김(hidden)이 아닌 클래스를 번호 순으로 표시 (목록 줄 i = list_ids()[i])
        # 지정 불가 클래스는 회색 + '(지정 불가 → N번)' — 클릭해도 지정되지 않음 (edit_mixin.on_class_select)
        for row, cid in enumerate(list_ids()):
            self.classList.insert("end", display_name(cid))
            color = COLORS[cid % len(COLORS)] if is_selectable(cid) else LOCKED_CLASS_COLOR
            self.classList.itemconfig(row, fg=color)
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

    def _build_auto_panel(self, right):
        # 자동 라벨링(왼쪽) + 작업 이력(오른쪽 남는 공간)
        mid = tk.Frame(right)
        mid.pack(side="top", fill="x", pady=(6, 0))
        lf_auto = tk.LabelFrame(mid, text="자동 라벨링 (YOLO)", font=FONT_B)
        lf_auto.pack(side="left", fill="y")
        self.historyPanel = HistoryPanel(mid)
        self.historyPanel.pack(side="left", fill="both", expand=True, padx=(6, 0))

        row1 = tk.Frame(lf_auto)
        row1.pack(fill="x", padx=4, pady=(4, 0))
        self.loadModelBtn = tk.Button(row1, text="모델(best.pt) 불러오기", font=FONT,
                                      command=self.load_model)
        self.loadModelBtn.pack(side="left")
        self.modelLabel = tk.Label(row1, text="(모델 없음)", font=FONT_S,
                                   fg="#666", anchor="w")
        self.modelLabel.pack(side="left", padx=6)

        row2 = tk.Frame(lf_auto)
        row2.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(row2, text="신뢰도(conf)", font=FONT).pack(side="left")
        self.confVar = tk.StringVar(value=f"{DEFAULT_CONF:.2f}")
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

        tk.Label(lf_auto, font=FONT_S, fg="#666", justify="left",
                 text="※ 자동 BBox(점선 + 'AI %') → 확인·수정 후 저장하면 확정"
                 ).pack(anchor="w", padx=4, pady=(2, 4))

    def _build_lower_panel(self, right):
        # 왼쪽 절반(검수 상태·작업자) / 오른쪽 절반(이슈 노트)
        lower = tk.Frame(right)
        lower.pack(side="top", fill="both", expand=True, pady=(6, 0))
        lower.columnconfigure(0, weight=1, uniform="half")   # uniform → 두 열 폭을 똑같이
        lower.columnconfigure(1, weight=1, uniform="half")
        lower.rowconfigure(0, weight=1)

        left = tk.Frame(lower)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 3))

        # ① 검수 상태 = 저장할 단계 (고를 수 있는 단계는 사람 역할에 따라 — src/bbox/workflow.py)
        self.reviewPanel = ReviewPanel(left, STAGES, on_change=self.on_review_select)
        self.reviewPanel.pack(side="top", fill="x")

        # ② 작업자 정보 — 선택 목록(config.PEOPLE)에서 고르기만
        self.personPanel = PersonPanel(left, "작업자 정보", people_labels(),
                                       on_change=self.update_review_buttons)
        self.personPanel.pack(side="top", fill="x", pady=(6, 0))

        # ③ Scene Type / REVIEW 사유 → manifest (저장 시 유형 필수, review 로 보낼 때 사유 필수)
        self.scenePanel = ScenePanel(left, SCENE_TYPES, REVIEW_REASONS)
        self.scenePanel.pack(side="top", fill="x", pady=(6, 0))

        # 오른쪽 절반: 이슈 노트
        lf_issue = tk.LabelFrame(lower, text="이슈 노트", font=FONT_B)
        lf_issue.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        self.issueNote = tk.Text(lf_issue, width=1, height=8, wrap="word", font=FONT)
        self.issueNote.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(lf_issue, font=FONT_S, fg="#666", justify="left",
                 text="※ 지난 이슈 기록 아래에 적고 저장하면\n   issues 에 추가 (공백만 있으면 무시)"
                 ).pack(anchor="w", padx=4)

    # ── 공용 ──
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