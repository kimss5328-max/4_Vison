"""자동 라벨링 화면 연동 — 모델 불러오기 / 현재 이미지 추론 / 일괄 추론
   (실제 모델 처리는 auto_label.YoloAutoLabeler 가 담당)"""
import threading
from tkinter import filedialog, messagebox

from PIL import Image

from src.config import CLASS_NAMES


class AutoLabelMixin:
    def conf_value(self):
        try:
            return min(max(float(self.confVar.get()), 0.01), 0.99)
        except ValueError:
            return 0.25

    def load_model(self):
        path = filedialog.askopenfilename(
            title="학습된 YOLO 모델 선택 (best.pt)",
            filetypes=[("YOLO 모델", "*.pt"), ("모든 파일", "*.*")])
        if not path:
            return False
        self.status("모델을 불러오는 중입니다...")
        self.root.update_idletasks()
        try:
            n_cls = self.labeler.load(path)
        except ImportError:
            messagebox.showerror("ultralytics 없음",
                                 "자동 추론에는 ultralytics 패키지가 필요합니다.\n\n"
                                 "    pip install ultralytics\n\n"
                                 "설치 후 다시 시도하세요.")
            self.status("모델 불러오기 실패")
            return False
        except Exception as e:
            messagebox.showerror("모델 오류", f"모델을 불러오지 못했습니다.\n{e}")
            self.status("모델 불러오기 실패")
            return False
        self.modelLabel.config(text=self.labeler.name)
        if n_cls != len(CLASS_NAMES):
            messagebox.showwarning(
                "클래스 수 확인",
                f"모델 클래스 수({n_cls})가 프로그램 클래스 수({len(CLASS_NAMES)})와 다릅니다.\n"
                f"클래스 번호(0~{len(CLASS_NAMES) - 1})가 서로 같은지 확인하세요.\n"
                f"범위를 벗어나거나 4번(사용 안 함)인 결과는 무시됩니다.")
        self.status(f"모델 로드 완료: {self.labeler.name}")
        return True

    def ensure_model(self):
        if self.labeler.loaded:
            return True
        return self.load_model() and self.labeler.loaded

    def predict_image(self, im, conf=None):
        return self.labeler.predict(im, self.conf_value() if conf is None else conf)

    def apply_auto(self, p, preds):
        """이미지(p)에 추론 결과를 자동 BBox 로 반영. 이전 자동 박스는 교체, 수동 박스는 유지."""
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
                    self.auto_pred[p] = self.labeler.predict(im.convert("RGB"), conf)
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
        self.refresh_image_list()                         # 목록 색상 갱신
        if 0 <= self.idx < len(self.images):
            self.imageList.selection_set(self.idx)        # 현재 선택 유지
        stopped = " (중지됨)" if self._batch_stop else ""
        self.status(f"일괄 추론 완료{stopped}: {self._batch_n}장 처리, "
                    f"검출된 이미지 {found}장 (주황색 표시) → 열어서 확인/수정 후 저장하세요")
