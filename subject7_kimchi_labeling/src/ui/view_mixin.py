"""좌표 변환 / 확대·축소·이동 / 캔버스 그리기 / 클릭 위치의 박스 찾기"""
import math
import os

from PIL import Image, ImageTk

from src.bbox import geometry
from src.config import (CLASS_NAMES, COLORS, ISSUE_ID, ISSUE_COLOR, PENDING_COLOR,
                    FONT_B, MAX_ZOOM)


class ViewMixin:
    # ── 좌표 변환 ──
    def canvas_size(self):
        return max(self.imageCanvas.winfo_width(), 1), max(self.imageCanvas.winfo_height(), 1)

    def to_canvas(self, x, y):
        return x * self.scale + self.ox, y * self.scale + self.oy

    def to_image(self, cx, cy):
        return (cx - self.ox) / self.scale, (cy - self.oy) / self.scale

    def clamp_img_pt(self, x, y):
        iw, ih = self.img.size
        return min(max(x, 0), iw), min(max(y, 0), ih)

    def box_to_yolo(self, b):
        return geometry.box_to_yolo(b, *self.img.size)

    def yolo_to_box(self, cls, xc, yc, w, h):
        return geometry.yolo_to_box(cls, xc, yc, w, h, *self.img.size)

    # ── 확대 / 축소 / 이동 ──
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

    # ── 그리기 ──
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
        self._label_hits = []
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
        self._label_hits = []
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
            tb = c.bbox(t)
            bg = c.create_rectangle(tb, fill=color, outline=color, tags="box")
            c.tag_raise(t, bg)
            self._label_hits.append((tb, b))       # 이름표 클릭 → 이 박스 선택

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
        """캔버스 좌표(cx, cy)에 있는 박스 찾기 — 이름표 → 박스 내부 순"""
        # ① 이름표: 박스 바깥 위쪽에 그려지므로 따로 검사 (나중에 그린 = 위에 보이는 것 우선)
        for (x0, y0, x1, y1), b in reversed(self._label_hits):
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return b
        # ② 박스 내부: 겹치면 가장 작은 박스
        x, y = self.to_image(cx, cy)
        hits = [b for b in self.cur_boxes()
                if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]]
        if not hits:
            return None
        return min(hits, key=lambda b: (b["x2"] - b["x1"]) * (b["y2"] - b["y1"]))
