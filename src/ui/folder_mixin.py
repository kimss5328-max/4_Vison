"""폴더 열기 / 프로젝트 구성 / 이미지 목록 / 진행률"""
import os
from tkinter import filedialog, messagebox

from src.config import IMG_EXTS, AUTO_LIST_COLOR, DONE_LIST_COLOR, VIEW_FILTERS


class FolderMixin:
    # ── 프로젝트 / 경로 도우미 ──
    def P(self, p):
        """이미지 경로 → 소속 프로젝트(dict)"""
        return self.proj_of[p]

    def rel_of(self, p):
        return os.path.relpath(p, self.P(p)["img_root"])

    def disp(self, p):
        """화면 표시용 이름 (프로젝트가 2개 이상이면 프로젝트명 포함)"""
        rel = self.rel_of(p)
        return f"{self.P(p)['name']}/{rel}" if len(self.projects) > 1 else rel

    # ── 프로젝트 폴더 찾기 ──
    @staticmethod
    def _has_both(p):
        return (os.path.isdir(os.path.join(p, "images"))
                and os.path.isdir(os.path.join(p, "labels")))

    def _find_roots(self, d):
        d = os.path.normpath(d)

        # 1. 선택한 폴더 자체가 프로젝트인 경우
        if self._has_both(d):
            return [(d, os.path.join(d, "images"))]

        # 2. 선택한 폴더 자체가 images 폴더인 경우
        if os.path.basename(d).lower() == "images":
            return [(os.path.dirname(d), d)]

        # 3. 선택한 폴더 바로 아래에 있는 프로젝트만 확인 (_labeled 폴더 제외)
        subs = []
        try:
            for name in sorted(os.listdir(d)):
                sub = os.path.join(d, name)
                if not os.path.isdir(sub) or name.endswith("_labeled"):
                    continue
                if self._has_both(sub):
                    subs.append((sub, os.path.join(sub, "images")))
        except OSError:
            pass
        if subs:
            return subs

        # 4. 아무 프로젝트도 없으면 선택한 폴더 자체를 이미지 폴더로 사용
        return [(d, d)]

    # ── 폴더 열기 ──
    def open_folder(self):
        self.save_current_note()

        picked = []
        while True:
            d = filedialog.askdirectory(title="최상위 폴더 선택 (images + labels 가 있는 폴더, 또는 그 상위 폴더)")
            if not d:
                break
            for item in self._find_roots(d):
                if item not in picked:
                    picked.append(item)
            names = "\n".join("  ./ " + os.path.basename(pr) for pr, _ in picked)
            if not messagebox.askyesno("폴더 추가",
                                       f"현재 {len(picked)}개 폴더가 선택되었습니다.\n{names}\n\n"
                                       f"다른 폴더도 추가하시겠습니까?"):
                break
        if not picked:
            return

        projects, proj_of, folders = [], {}, {}
        used = set()
        for proj, img_root in picked:
            name = os.path.basename(proj)
            if name in used:
                name += f"({len(used)})"
            used.add(name)
            pj = {"proj": proj, "img_root": img_root, "name": name,
                  "out_dir": None, "by_rel": {}, "by_name": {}}
            if img_root != proj:
                lbl_root = os.path.join(proj, "labels")
                for dp, _, files in os.walk(lbl_root):
                    for f in files:
                        if f.lower().endswith((".txt", ".csv")):   # txt / csv 모두 인식
                            q = os.path.join(dp, f)
                            rel = os.path.splitext(os.path.relpath(q, lbl_root))[0]
                            pj["by_rel"][rel] = q
                            pj["by_name"].setdefault(os.path.splitext(f)[0], q)
            cand = self.default_out_dir(pj)
            pj["out_dir"] = cand if os.path.isdir(cand) else None
            projects.append(pj)

            for cur, _, files in os.walk(img_root):
                imgs = sorted(f for f in files if f.lower().endswith(IMG_EXTS))
                if imgs:
                    rel = os.path.relpath(cur, img_root)
                    lst = [os.path.join(cur, f) for f in imgs]
                    folders[f"{name}|{rel}"] = lst
                    for q in lst:
                        proj_of[q] = pj

        if not folders:
            messagebox.showwarning("알림", "선택한 폴더에 이미지가 없습니다.")
            return

        self.projects, self.proj_of, self.folders = projects, proj_of, folders
        keys = sorted(self.folders)
        self.folder_keys = ["__all__"] + keys
        multi = len(projects) > 1
        names = ["(전체 이미지)"]
        for k in keys:
            pname, rel = k.split("|", 1)
            if rel == ".":
                names.append(pname)
            else:
                names.append(f"{pname}/{rel}" if multi else rel)
        self.folderSelect["values"] = names
        self.folderSelect.current(0)

        self.annotations.clear()
        self.notes.clear()
        self.review_status.clear()
        self.done.clear()
        self.passed.clear()
        self.auto_pred.clear()
        for k in keys:
            for p in self.folders[k]:
                if self.P(p)["out_dir"] and os.path.exists(self.out_paths(p)["label"]):
                    self.done.add(p)
        self.passed = set(self.done)

        self.idx = -1
        self.load_folder("__all__")

    def on_folder_select(self, _=None):
        i = self.folderSelect.current()
        if i >= 0:
            self.save_current_note()
            self.idx = -1
            self.load_folder(self.folder_keys[i])

    def load_folder(self, key):
        if key == "__all__":
            all_images = [p for k in sorted(self.folders) for p in self.folders[k]]
        else:
            all_images = self.folders[key]
        self.folder_images = list(dict.fromkeys(all_images))
        self.apply_filter()

    # ── 보기 필터 (전체 / 미라벨 / 라벨 완료) ──
    def _match_filter(self, p):
        if self.view_filter == "todo":
            return p not in self.done
        if self.view_filter == "done":
            return p in self.done
        return True

    def apply_filter(self, keep=None):
        """folder_images 에 보기 필터를 적용해 self.images(작업 목록)를 다시 만든다.
           keep: 새 목록에 남아 있으면 계속 보여줄 이미지"""
        # 목록이 바뀌기 전에 현재 이미지의 메모 / 미지정 박스 정리
        if self.cur_path():
            self.discard_pending(silent=True)
            self.save_current_note()
        self.idx = -1
        self.pending = None

        self.images = [p for p in self.folder_images if self._match_filter(p)]
        self.refresh_image_list()
        self.update_progress()
        self.update_filter_counts()
        if not self.images:
            self.clear_view()
            name = dict(VIEW_FILTERS)[self.view_filter]
            self.status(f"'{name}' 보기에 해당하는 이미지가 없습니다.")
            return
        self.show_image(self.images.index(keep) if keep in self.images else 0)

    def on_filter_select(self, _=None):
        i = self.filterSelect.current()
        if i < 0:
            return
        self.view_filter = VIEW_FILTERS[i][0]
        if self.folder_images:
            self.apply_filter(keep=self.cur_path())

    def update_filter_counts(self):
        """보기 콤보박스에 항목별 개수 표시 — 저장할 때마다 갱신"""
        n_all = len(self.folder_images)
        n_done = sum(1 for p in self.folder_images if p in self.done)
        counts = {"all": n_all, "todo": n_all - n_done, "done": n_done}
        self.filterSelect["values"] = [f"{name} ({counts[key]})" for key, name in VIEW_FILTERS]
        self.filterSelect.current([key for key, _ in VIEW_FILTERS].index(self.view_filter))

    # ── 목록 / 진행률 ──
    def refresh_image_list(self):
        self.imageList.delete(0, "end")
        for i, p in enumerate(self.images):
            self.imageList.insert("end", self.disp(p))
            if p in self.done:
                fg = DONE_LIST_COLOR
            elif self.auto_pred.get(p):      # 일괄 추론 결과가 있고 아직 확인 전
                fg = AUTO_LIST_COLOR
            else:
                fg = "black"
            self.imageList.itemconfig(i, fg=fg)

    def update_progress(self):
        # 진행률은 보기 필터와 상관없이 폴더 전체 기준
        total = len(self.folder_images)
        done = sum(1 for p in self.folder_images if p in self.passed)
        pct = done / total * 100 if total else 0
        self.progressBar["value"] = pct
        self.progressText.config(text=f"{done} / {total}  ({pct:.1f}%)")

    def on_image_list_select(self, _=None):
        sel = self.imageList.curselection()
        if sel and sel[0] != self.idx:
            self.show_image(sel[0])
