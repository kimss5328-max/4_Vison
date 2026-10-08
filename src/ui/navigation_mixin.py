"""현재 이미지 열기 / 이전·다음 이동 / 이미지별 메모(이슈 노트) / 단계 흐름·수정 권한 표시"""
import threading
from tkinter import messagebox

from PIL import Image

from src.config import STAGES, ROLE_NAMES, SOURCE_LABEL
from src.validation.rules import describe_locked
from src.bbox.workflow import person_by_label


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
            self.status(f"검수 상태: {state}")

    # ── 작업자 / 단계 흐름 / 수정 권한 (규칙은 src/bbox/workflow.py) ──
    def current_person(self):
        """선택 목록에서 고른 사람 (config.PEOPLE 의 dict) / 안 골랐으면 None"""
        return person_by_label(self.personPanel.get_label())

    def update_review_buttons(self):
        """작업자를 고를 때마다 호출 → 권한·선택지 다시 판정 (이력은 다시 읽지 않음)"""
        person = self.current_person()
        if person:
            what = "모든 단계 작업 + final 판정" if person["role"] == "reviewer" else "final 외 작업·수정 → pass / edited / review"
            self.personPanel.set_hint(f"ID {person['id']} · {ROLE_NAMES[person['role']]}: {what}")
        else:
            self.personPanel.set_hint("이름을 선택하세요")
        self.refresh_workflow(reload=False)

    def refresh_workflow(self, reload=True):
        """현재 이미지의 단계 흐름으로 검수 상태 선택지·작업 이력·수정 권한 갱신"""
        p = self.cur_path()
        if not p or not self.img:
            self.cur_flow = None
            self.edit_ok, self.edit_why = False, ""
            for st in STAGES:
                self.reviewPanel.set_enabled(st, False)
            self.historyPanel.show([], [])
            return
        if reload or self.cur_flow is None or self._flow_path != p:
            self.cur_flow, self._flow_path = self.current_flow(p), p
        flow = self.cur_flow
        person = self.current_person()
        self.edit_ok, self.edit_why = flow.can_act(person)

        # 검수 상태: 이 사람이 보낼 수 있는 단계만 활성. 선택값이 없거나 안 되는 값이면 기본값
        targets = flow.targets(person)
        for st in STAGES:
            self.reviewPanel.set_enabled(st, self.edit_ok and st in targets)
        sel = self.reviewPanel.get_state()
        if reload or sel not in targets:
            sel = flow.default_target(person)
        self.reviewPanel.set_state(sel)

        self.historyPanel.show(*flow.history_lines())

    def check_edit(self):
        """박스를 그리거나 고치기 전에 호출 — 권한이 없으면 상태 표시줄에 이유를 보이고 False"""
        if not self.edit_ok:
            self.status("🔒 수정 불가: " + (self.edit_why or "이미지를 먼저 여세요."))
        return self.edit_ok

    def clear_view(self):
        """보여줄 이미지가 없을 때 화면 비우기"""
        self.img = None
        self.selected = []
        self.pending = None
        self.render()
        self.issueNote.delete("1.0", "end")
        self.reviewPanel.set_state("")
        self.scenePanel.set_values("", "")
        self.refresh_workflow()
        self.refresh_info()

    # ── 이미지 열기 ──
    def show_image(self, i):
        self.hide_stats()                    # 통계 화면이 열려 있으면 이미지 화면으로
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
        self.issueNote.see("end")                   # 이슈 기록이 길면 맨 아래(최근 기록·입력 위치)를 보여줌
        # 검수 상태 선택지·작업 이력·수정 권한 (현재 위치 + 이력 csv 기준)
        self.refresh_workflow()
        # Scene Type / REVIEW 사유 — 이 이미지의 manifest 값 (없으면 빈칸 → 이전 이미지 값이 남지 않음)
        row = self.manifest_row(p) or {}
        self.scenePanel.set_values(row.get("scene_type", ""), row.get("review_reason", ""))

        self.imageList.selection_clear(0, "end")
        self.imageList.selection_set(i)
        self.imageList.see(i)
        self.set_zoom_mode(False)
        self.fit_view()
        self.refresh_info()
        w, h = self.img.size
        loc = self.location(p) or SOURCE_LABEL
        msg = f"{self.disp(p)}   ({w} x {h})   [{i + 1} / {len(self.images)}]   위치: {loc}"
        n_auto = sum(1 for b in self.cur_boxes() if b.get("auto"))
        if n_auto:
            msg += f"   🤖 자동 BBox {n_auto}개 → 확인/수정 후 저장하세요"
        locked = describe_locked(self.cur_boxes())
        if locked:
            msg += "   ⚠ 지정 불가 클래스: " + ", ".join(locked) + " (저장 시 확인)"
        if self.is_in_progress(p):
            msg += "   ✎ 작업 중 (임시 저장됨, [저장] 전)"
        if not self.edit_ok:
            msg += "   🔒 " + self.edit_why
        self.status(msg)
        self.update_out_dir_label()
        self.remember_folder()               # 보던 이미지 기억 → 꺼져도 다시 켜면 여기부터
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
