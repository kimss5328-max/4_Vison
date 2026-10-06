"""독립 위젯 패널 — 검수 상태 / 작업자·검수자 정보"""
import tkinter as tk

from src.config import FONT, FONT_B


class InfoPanel(tk.LabelFrame):
    """'라벨 + 입력칸' 여러 줄로 된 정보 입력 패널 (작업자/검수자 공용)"""

    def __init__(self, parent, title, fields):
        super().__init__(parent, text=title, font=FONT_B)
        self.columnconfigure(1, weight=1)
        self.vars = {}
        for row, name in enumerate(fields):
            tk.Label(self, text=name, font=FONT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(4, 2), pady=1)
            v = tk.StringVar()
            tk.Entry(self, textvariable=v, font=FONT, width=1).grid(
                row=row, column=1, sticky="ew", padx=(0, 4), pady=1)
            self.vars[name] = v

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
        for k, st in enumerate(states):
            tk.Radiobutton(self, text=st, value=st, variable=self.var,
                           tristatevalue="__none__", font=FONT, anchor="w",
                           command=self._changed
                           ).grid(row=k // 2, column=k % 2, sticky="w", padx=2)

    def _changed(self):
        if self._on_change:
            self._on_change(self.var.get())

    def get_state(self):
        return self.var.get()

    def set_state(self, state):
        self.var.set(state)
