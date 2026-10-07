"""독립 위젯 패널 — 검수 상태 / 작업자·검수자 정보"""
import tkinter as tk

from src.config import FONT, FONT_B, SCENE_TYPES, REVIEW_REASONS


class InfoPanel(tk.LabelFrame):
    """'라벨 + 입력칸' 여러 줄로 된 정보 입력 패널 (작업자/검수자 공용)"""

    def __init__(self, parent, title, fields, on_change=None):
        super().__init__(parent, text=title, font=FONT_B)
        self.columnconfigure(1, weight=1)
        self.vars = {}
        self._on_change = on_change
        for row, name in enumerate(fields):
            tk.Label(self, text=name, font=FONT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(4, 2), pady=1)
            v = tk.StringVar()
            tk.Entry(self, textvariable=v, font=FONT, width=1).grid(
                row=row, column=1, sticky="ew", padx=(0, 4), pady=1)
            v.trace_add("write", self._changed)     # 글자를 칠 때마다 알림
            self.vars[name] = v

    def _changed(self, *_):
        if self._on_change:
            self._on_change()

    def is_complete(self):
        """모든 칸이 채워졌는지"""
        return all(v.get().strip() for v in self.vars.values())

    def get_data(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def set_data(self, data):
        for k, v in self.vars.items():
            v.set(data.get(k, ""))


class ReviewPanel(tk.LabelFrame):
    """검수 상태 라디오버튼 (2열 배치). 선택 시 on_change(state) 호출"""

    def __init__(self, parent, states, on_change=None):
        super().__init__(parent, text="검수 상태", font=FONT_B)
        self.var = tk.StringVar(value="")
        self._on_change = on_change
        self.buttons = {}
        for k, st in enumerate(states):
            rb = tk.Radiobutton(self, text=st, value=st, variable=self.var,
                                tristatevalue="__none__", font=FONT, anchor="w",
                                command=self._changed)
            rb.grid(row=k // 2, column=k % 2, sticky="w", padx=2)
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


class SceneTypePanel(tk.LabelFrame):
    """scene_type 선택 + review_reason 콤보 (저장 시 manifest 에 기록)"""

    def __init__(self, parent):
        super().__init__(parent, text="Scene Type", font=FONT_B)
        self.scene_var = tk.StringVar(value="")
        for i, st in enumerate(SCENE_TYPES):
            tk.Radiobutton(self, text=st, value=st, variable=self.scene_var,
                           font=FONT, anchor="w").grid(
                row=i, column=0, sticky="w", padx=4, pady=1)
        tk.Label(self, text="REVIEW 이유", font=FONT, anchor="w").grid(
            row=len(SCENE_TYPES), column=0, sticky="w", padx=4, pady=(6, 0))
        self.reason_var = tk.StringVar(value="")
        import tkinter.ttk as ttk
        ttk.Combobox(self, textvariable=self.reason_var,
                     values=REVIEW_REASONS, font=FONT, state="normal",
                     width=22).grid(row=len(SCENE_TYPES)+1, column=0,
                                    sticky="ew", padx=4, pady=(2, 4))

    def get_scene(self):
        return self.scene_var.get()

    def get_reason(self):
        return self.reason_var.get().strip()

    def set_scene(self, val):
        self.scene_var.set(val if val in SCENE_TYPES else "")

    def set_reason(self, val):
        self.reason_var.set(val)