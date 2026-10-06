"""현재 이미지 열기 / 이전·다음 이동 / 이미지별 메모(이슈 노트·검수 상태)"""
import threading
from tkinter import messagebox

from PIL import Image

from src.config import UNUSED_CLASS


class NavigationMixin:
    def cur_path(self):
        return self.images[self.idx] if 0 <= self.idx < len(self.images) else None

    def cur_boxes(self):
        return self.annotations.setdefault(self.cur_path(), [])

    # ── 이미지별 메모 ──
    def save_current_note(self):
        p = self.cur_path()
        if p:
            self.notes[p] = self.issueNote.get("1.0", "end-1c")

    def on_review_select(self, state):
        p = self.cur_path()
        if p:
            self.review_status[p] = state
            self.status(f"검수 상태: {state}")

    def clear_view(self):
        """보여줄 이미지가 없을 때 화면 비우기"""
        self.img = None
        self.selected = []
        self.pending = None
        self.render()
        self.issueNote.delete("1.0", "end")
        self.reviewPanel.set_state("")
        self.refresh_info()

    # ── 이미지 열기 ──
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
            if not self.annotations[p] and p not in self.done and self.labeler.loaded:
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
        self.reviewPanel.set_state(self.review_status.get(p, ""))

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
        self.update_out_dir_label()
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

    # ── 이동 ──
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
