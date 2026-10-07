"""독립 위젯 패널 — 작업자 선택 / 검수 상태 / Scene Type·REVIEW 사유 / 작업 이력"""
import tkinter as tk
from tkinter import ttk

from src.config import FONT, FONT_B, FONT_S


class PersonPanel(tk.LabelFrame):
    """작업자 정보 — 선택 목록(config.PEOPLE)에서 고르기만 함. 고르면 on_change() 호출"""

    def __init__(self, parent, title, labels, on_change=None):
        super().__init__(parent, text=title, font=FONT_B)
        self.var = tk.StringVar()
        self._on_change = on_change
        self.combo = ttk.Combobox(self, textvariable=self.var, values=labels,
                                  state="readonly", font=FONT, width=1)
        self.combo.pack(fill="x", padx=4, pady=(4, 2))
        self.combo.bind("<<ComboboxSelected>>", self._changed)
        self.roleLabel = tk.Label(self, text="이름을 선택하세요", font=FONT_S, fg="#666", anchor="w")
        self.roleLabel.pack(fill="x", padx=4, pady=(0, 4))

    def _changed(self, _=None):
        if self._on_change:
            self._on_change()

    def get_label(self):
        return self.var.get()

    def set_label(self, label):
        self.var.set(label)
        self._changed()

    def set_hint(self, text):
        self.roleLabel.config(text=text)


class ReviewPanel(tk.LabelFrame):
    """검수 상태(= 저장할 단계) 라디오버튼 — 3개씩 줄 배치. 선택 시 on_change(state) 호출"""

    def __init__(self, parent, states, on_change=None, per_row=3):
        super().__init__(parent, text="검수 상태", font=FONT_B)
        self.var = tk.StringVar(value="")
        self._on_change = on_change
        self.buttons = {}
        for k, st in enumerate(states):
            rb = tk.Radiobutton(self, text=st, value=st, variable=self.var,
                                tristatevalue="__none__", font=FONT, anchor="w",
                                command=self._changed)
            rb.grid(row=k // per_row, column=k % per_row, sticky="w", padx=(2, 0))
            self.buttons[st] = rb

    def _changed(self):
        if self._on_change:
            self._on_change(self.var.get())

    def get_state(self):
        return self.var.get()

    def set_state(self, state):
        self.var.set(state)

    def set_enabled(self, state, enabled):
        """선택지 하나를 누를 수 있게 / 없게"""
        self.buttons[state].config(state="normal" if enabled else "disabled")


class HistoryPanel(tk.LabelFrame):
    """작업 이력 (읽기 전용) — 위: 단계별 처음 저장한 사람(고정), 아래: 그 뒤 이동 기록"""

    def __init__(self, parent):
        super().__init__(parent, text="작업 이력", font=FONT_B)
        # 위: 단계별 처음 기록 (항상 보임)
        self.head = tk.Label(self, font=FONT_S, fg="#1e5aa8", justify="left", anchor="nw")
        self.head.pack(fill="x", padx=4, pady=(2, 0))
        tk.Frame(self, height=1, bg="#bbb").pack(fill="x", padx=4, pady=2)
        # 아래: 이후 기록 (길어지면 스크롤, 최신 기록이 보이게)
        self.text = tk.Text(self, width=24, height=2, font=FONT_S, wrap="char", fg="#555",
                            bg=self.cget("bg"), relief="flat", state="disabled", cursor="arrow")
        self.text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    def show(self, top, log):
        self.head.config(text="\n".join(top))
        t = self.text
        t.config(state="normal")
        t.delete("1.0", "end")
        t.insert("end", "\n".join(log) if log else "(이동 기록 없음)")
        t.config(state="disabled")
        t.see("end")


class ScenePanel(tk.LabelFrame):
    """Scene Type(이미지 유형)·REVIEW 사유 선택 — 목록에서 고르기만 (오타 방지). 값은 manifest 에 기록
       scenes: ((기록값, 설명), ...), reasons: (기록값, ...)"""

    def __init__(self, parent, scenes, reasons):
        super().__init__(parent, text="Scene Type / REVIEW 사유", font=FONT_B)
        self.columnconfigure(1, weight=1)
        self._scene_of = {f"{k} ({d})": k for k, d in scenes}     # 표시 글자 → 기록값
        self._label_of = {k: lbl for lbl, k in self._scene_of.items()}
        self.scene_var = tk.StringVar()
        self.reason_var = tk.StringVar()
        tk.Label(self, text="유형", font=FONT_S, anchor="w").grid(row=0, column=0, sticky="w", padx=(4, 2))
        ttk.Combobox(self, textvariable=self.scene_var, values=list(self._scene_of),
                     state="readonly", font=FONT_S, width=1).grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=(2, 1))
        tk.Label(self, text="사유", font=FONT_S, anchor="w").grid(row=1, column=0, sticky="w", padx=(4, 2))
        ttk.Combobox(self, textvariable=self.reason_var, values=list(reasons),
                     state="readonly", font=FONT_S, width=1).grid(row=1, column=1, sticky="ew", padx=(0, 4), pady=(1, 4))

    def get_scene(self):
        return self._scene_of.get(self.scene_var.get(), "")

    def get_reason(self):
        return self.reason_var.get()

    def set_values(self, scene, reason):
        """이미지를 열 때 manifest 값으로 채움 (없으면 빈칸)"""
        self.scene_var.set(self._label_of.get(scene, ""))
        self.reason_var.set(reason or "")
