"""마우스로 박스 그리기·선택·크기조절 / 휠 확대·축소 / 클래스 지정 / 삭제 / 크기 정보 패널"""
from tkinter import messagebox

from src.config import (CLASS_IDS, ISSUE_ID, PENDING_COLOR,
                    HANDLE_R, SHIFT, CTRL, WHEEL_STEP)


class EditMixin:
    # ── 마우스 이벤트 ──
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
        # 클래스 미지정 박스 자신(또는 그 이름표)을 누른 경우는 지우지 않고 유지
        if not (self.pending and self.hit_test(e.x, e.y) is self.pending):
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
            self.autosave_work()             # 작업 중 자동 저장
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
            if b and b["cls"] in CLASS_IDS:
                self.classList.selection_set(CLASS_IDS.index(b["cls"]))
            self.redraw_boxes()
            self.refresh_info()

    # ── 마우스 휠 확대·축소 ──
    def on_wheel(self, e):
        """휠 위로 = 확대, 아래로 = 축소 (마우스 포인터 위치를 중심으로)
           Windows·macOS: <MouseWheel> 이벤트의 delta 부호로 방향 판단
           리눅스(WSL)  : <Button-4> = 위, <Button-5> = 아래"""
        if not self.img or self.mode:          # 박스를 그리거나 이동하는 중에는 무시
            return "break"
        up = getattr(e, "num", None) == 4 or getattr(e, "delta", 0) > 0
        self.zoom_at(WHEEL_STEP if up else 1 / WHEEL_STEP, e.x, e.y)
        return "break"

    def on_escape(self, _=None):
        if self.zoom_mode:
            self.set_zoom_mode(False)
            self.status("확대 모드 취소")
        else:
            self.discard_pending()

    # ── 클래스 지정 / 삭제 ──
    def on_class_select(self, _=None):
        sel = self.classList.curselection()
        if not sel or not self.img:
            return
        cls = CLASS_IDS[sel[0]]           # 목록 줄 번호 → 실제 클래스 번호
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
        self.autosave_work()                 # 박스 확정·클래스 변경 → 작업 중 자동 저장

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
        self.autosave_work()                 # 삭제 → 작업 중 자동 저장

    # ── 크기 정보 패널 ──
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
