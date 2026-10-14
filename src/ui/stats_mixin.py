"""통계 화면 — 단계 보기에서 '그래프'를 고르면 가운데 이미지 영역 대신 표시
   작업 상태별 분포(도넛) + 데이터 품질 지표(표, final 까지) + 범위(볼 단계) 체크 상자를 화면 가운데에
   계산은 src/bbox/stats.py, 그리기는 Tkinter Canvas (추가 설치 없음)
   목록에서 이미지를 고르거나 다른 단계를 고르면 원래 이미지 화면으로 돌아감"""
import csv
import math
import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from src.config import (BASE_DIR, STATS_DIR, MANIFEST_DIR, MANIFEST_FILE, DATASET_NAMES,
                        STATS_FONT, STATS_FONT_B, STATS_FONT_BIG, STATS_ROW_H,
                        STATS_DONUT_W, STATS_DONUT_H, STATS_LABEL_MIN, STATS_STAGES)
from src.bbox import stats, manifest


class StatsMixin:
    # ── 화면 만들기 (layout_mixin._build_center 에서 호출, 처음에는 숨김) ──
    #   ┌ 제목 ─────────────────────────── [새로고침] [CSV 저장] ┐
    #   │                 (위 여백 — 가운데 정렬용)               │
    #   │  ┌ 작업 상태별 분포 ┐  ┌ 데이터 품질 지표 ┐            │
    #   │  │ 도넛 (비율 표시) │  │ 표 (final 까지)  │            │
    #   │  └──────────────────┘  └──────────────────┘            │
    #   │  ┌ 범위 — 볼 단계 선택 ───────────────────────────┐     │
    #   │  │ [v] 전체  [v] 미작업  [v] pass  [v] edited ... │     │
    #   │  └────────────────────────────────────────────────┘     │
    #   │                 (아래 여백)                              │
    def _build_stats_view(self, center):
        bg = self.root.cget("bg")
        self.statsFrame = tk.Frame(center, bg=bg)
        self.statsFrame.grid(row=0, column=0, sticky="nsew")
        self.statsFrame.grid_remove()
        self.statsFrame.columnconfigure(0, weight=1)
        self.statsFrame.rowconfigure(1, weight=1)       # 위 여백
        self.statsFrame.rowconfigure(4, weight=1)       # 아래 여백 → 내용이 세로 가운데

        top = tk.Frame(self.statsFrame, bg=bg)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.statsTitle = tk.Label(top, text="작업 결과 통계", font=STATS_FONT_B, bg=bg)
        self.statsTitle.pack(side="left")
        tk.Button(top, text="CSV 저장", font=STATS_FONT, command=self.save_stats_csv).pack(side="right")
        tk.Button(top, text="새로고침", font=STATS_FONT, command=self.refresh_stats).pack(side="right", padx=4)

        body = tk.Frame(self.statsFrame, bg=bg)
        body.grid(row=2, column=0)                      # sticky 없음 → 가로 가운데
        self.statsStagePanel = tk.LabelFrame(body, text="작업 상태별 분포", font=STATS_FONT_B)
        self.statsStagePanel.grid(row=0, column=0, sticky="nsew", padx=6)
        self.statsStageCanvas = tk.Canvas(self.statsStagePanel, bg=bg, highlightthickness=0,
                                          width=STATS_DONUT_W, height=STATS_DONUT_H)
        self.statsStageCanvas.pack(padx=6, pady=6)

        lf_table = tk.LabelFrame(body, text="데이터 품질 지표", font=STATS_FONT_B)
        lf_table.grid(row=0, column=1, sticky="nsew", padx=6)
        style = ttk.Style()
        style.configure("Stats.Treeview", font=STATS_FONT, rowheight=STATS_ROW_H)
        style.configure("Stats.Treeview.Heading", font=STATS_FONT_B)
        cols = ("item", "value", "ratio")
        self.statsTable = ttk.Treeview(lf_table, columns=cols, show="headings", height=7,
                                       style="Stats.Treeview")
        for c, h, w, anchor in (("item", "항목", 150, "w"), ("value", "값", 70, "e"),
                                ("ratio", "비율", 85, "e")):
            self.statsTable.heading(c, text=h)
            self.statsTable.column(c, width=w, anchor=anchor)
        self.statsTable.pack(fill="both", expand=True, padx=6, pady=6)

        # 범위 — 검수 상태처럼 테두리 상자 안의 체크박스 (처음 '그래프'를 열 때 한 번 만듦)
        self.scopeRow = tk.LabelFrame(self.statsFrame, text="범위 — 볼 단계 선택 (체크해서 넣고 빼기)", font=STATS_FONT_B)
        self.scopeRow.grid(row=3, column=0, pady=(10, 0))
        self.scope_vars = {}            # 단계 키('' = 미작업) → BooleanVar
        self.scope_all = tk.BooleanVar(value=True)

        self.stats_on = False
        self._stats = None

    # ── 보이기 / 숨기기 ──
    def show_stats(self):
        if not self.proj_of:
            messagebox.showinfo("알림", "먼저 폴더를 열어 주세요.")
            return False
        self.discard_pending(silent=True)
        self.save_current_note()
        self._build_scope_checks()
        self.imageCanvas.grid_remove()
        self.statsFrame.grid()
        self.stats_on = True
        self.refresh_stats()
        return True

    def hide_stats(self):
        if not self.stats_on:
            return
        self.stats_on = False
        self.statsFrame.grid_remove()
        self.imageCanvas.grid()
        self.update_stage_counts()              # 드롭다운을 원래 단계 보기로 되돌림

    # ── 범위 체크박스: 전체 + 작업 상태(미작업 ~ final)별 ──
    def _build_scope_checks(self):
        if self.scope_vars:                              # 한 번 만들면 그대로 (선택 유지)
            return
        per_row = 4                                      # 한 줄에 4칸 (첫 칸은 '전체')
        tk.Checkbutton(self.scopeRow, text="전체", font=STATS_FONT_B, variable=self.scope_all,
                       anchor="w", command=self._on_scope_all).grid(row=0, column=0, sticky="w",
                                                                    padx=(6, 10), pady=2)
        for i, (key, name, color) in enumerate(STATS_STAGES, start=1):
            v = tk.BooleanVar(value=True)
            self.scope_vars[key] = v
            tk.Checkbutton(self.scopeRow, text=name, font=STATS_FONT, fg=color, variable=v,
                           anchor="w", command=self._on_scope_one).grid(
                row=i // per_row, column=i % per_row, sticky="w", padx=(6, 10), pady=2)

    def _scope_names(self):
        """체크한 단계 이름 목록 — 예) ['pass', 'edited']"""
        return [name for key, name, _ in STATS_STAGES if self.scope_vars[key].get()]

    def _on_scope_all(self):
        for v in self.scope_vars.values():
            v.set(self.scope_all.get())
        self.refresh_stats()

    def _on_scope_one(self):
        self.scope_all.set(all(v.get() for v in self.scope_vars.values()))
        self.refresh_stats()

    # ── 집계 ──
    def _stats_entries(self):
        """선택한 범위의 이미지 → stats.summarize 에 넘길 정보 목록"""
        try:
            rows = manifest.read_rows(os.path.join(BASE_DIR, MANIFEST_DIR, MANIFEST_FILE))
        except (OSError, manifest.ManifestFormatError):
            rows = []
        scene_of = {(r.get("source_dataset", ""), r.get("original_split", ""), r.get("file_name", "")):
                    r.get("scene_type", "") for r in rows}
        checked = {key for key, v in self.scope_vars.items() if v.get()}
        entries = []
        for p in self.folder_images:                    # 폴더 분류에서 고른 폴더의 이미지 중 체크한 단계만
            stage = self.latest_stage(p)
            if stage not in checked:
                continue
            label = self._saved_label(p) if self.P(p)["out_dir"] else self.raw_label_path(p)
            entries.append({"stage": stage,
                            "classes": self._label_classes(label),
                            "scene": scene_of.get(self.manifest_key(p), ""),
                            "issue": self.has_issue(p)})
        return entries

    @staticmethod
    def _label_classes(path):
        """라벨 파일의 클래스 번호 목록 (파일이 없으면 빈 목록)"""
        out = []
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    v = line.replace(",", " ").split()
                    if len(v) == 5:
                        try:
                            out.append(int(v[0]))
                        except ValueError:
                            pass
        return out

    def refresh_stats(self):
        if not self.stats_on:
            return
        self.status("통계 계산 중...")
        self.root.update_idletasks()
        self._stats = stats.summarize(self._stats_entries())
        s = self._stats
        n_scope = sum(v.get() for v in self.scope_vars.values())
        self.statsTitle.config(text=f"작업 결과 통계 — {self._stats_folder_name()} "
                                    f"({n_scope}/{len(self.scope_vars)}개 단계)")
        self.statsStagePanel.config(text=f"작업 상태별 분포 (총 {s['total']}장)")
        self.statsTable.delete(*self.statsTable.get_children())
        color_of = {name: color for name, _, color in s["stages"]}
        shown = set(self._scope_names())
        for item, val, ratio in stats.stage_table_rows(s):
            if item in color_of and item not in shown:   # 체크 안 한 단계는 표에서 뺌
                continue
            if item in color_of:                     # 단계 줄 = 도넛 색 글씨 + ■ (범례 역할)
                self.statsTable.insert("", "end", values=(f"■ {item}", val, ratio), tags=(item,))
                self.statsTable.tag_configure(item, foreground=color_of[item])
            else:
                self.statsTable.insert("", "end", values=(item, val, ratio), tags=("total",))
        self.statsTable.tag_configure("total", font=STATS_FONT_B)
        self._redraw_stats()
        self.status(f"통계: 선택 범위 {s['total']}장 — 체크박스로 범위를 넣고 뺄 수 있습니다. "
                    f"목록에서 이미지를 누르면 이미지 화면으로 돌아갑니다.")

    def _stats_folder_name(self):
        """제목용 폴더 이름 — 데이터셋 폴더는 짧은 이름으로 (이물검출_학습데이터1/train → dataset1/train)"""
        name = self.folderSelect.get() or "(전체 이미지)"
        for folder, short in DATASET_NAMES.items():
            name = name.replace(folder, short)
        return name

    # ── 그리기 ──
    def _redraw_stats(self):
        if not self.stats_on or not self._stats:
            return
        s = self._stats
        self._draw_donut(self.statsStageCanvas, [(n, c, k) for n, k, c in s["stages"]],
                         s["total"], f"{s['total']}장")

    def _draw_donut(self, cv, items, total, center_text):
        """items: [(이름, 색, 개수)] — 가운데 도넛 (범례는 오른쪽 표의 색 글씨가 대신함)"""
        cv.delete("all")
        w = max(cv.winfo_width(), int(cv.cget("width")))      # 아직 화면에 안 그려졌으면 설정 크기
        h = max(cv.winfo_height(), int(cv.cget("height")))
        r = min(w, h) / 2 - 8
        ir = r * 0.5                                 # 가운데 구멍 반지름 (도넛 두께 = r 의 절반)
        cx, cy = w / 2, h / 2
        labels = []                                  # (x, y, '91.1%') — 조각을 다 그린 뒤 위에 씀
        if total:
            start = 90.0
            for _, color, n in items:
                if not n:
                    continue
                ext = -360.0 * n / total
                if abs(ext) >= 359.99:              # 한 종류가 100% → 원
                    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
                else:
                    cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=ext,
                                  fill=color, outline="white", width=2, style=tk.PIESLICE)
                ratio = n / total * 100
                if ratio >= STATS_LABEL_MIN:         # 큰 조각만 비율 표시 (작은 조각은 글씨가 넘침)
                    mid = math.radians(start + ext / 2)
                    rr = (r + ir) / 2                # 도넛 두께의 가운데
                    labels.append((cx + rr * math.cos(mid), cy - rr * math.sin(mid), f"{ratio:.1f}%"))
                start += ext
        else:
            cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#bbb")
        # 가운데 구멍 — 흰색으로 또렷하게
        cv.create_oval(cx - ir, cy - ir, cx + ir, cy + ir, fill="white", outline="#cfcfcf")
        cv.create_text(cx, cy, text=center_text, font=STATS_FONT_BIG)
        for x, y, text in labels:
            cv.create_text(x, y, text=text, font=STATS_FONT_B, fill="white")

    # ── CSV 저장 ──
    def save_stats_csv(self):
        if not self._stats:
            return
        scope = self._scope_names()
        d = os.path.join(BASE_DIR, STATS_DIR)
        path = os.path.join(d, f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["구분", "항목", "값", "비율"])
                wr.writerows(stats.csv_rows(self._stats, scope))
        except OSError as e:
            messagebox.showerror("CSV 저장 실패", str(e))
            return
        messagebox.showinfo("CSV 저장", f"통계를 저장했습니다.\n\n{os.path.relpath(path, BASE_DIR)}")
