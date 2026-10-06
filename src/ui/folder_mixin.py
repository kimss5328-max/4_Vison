"""폴더 열기 / 프로젝트 구성 / 이미지 목록 / 진행률"""
import os
import json
from tkinter import filedialog, messagebox

from src.config import IMG_EXTS, AUTO_LIST_COLOR, DONE_LIST_COLOR, VIEW_FILTERS

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS_PATH = os.path.join(CURRENT_DIR, "labeling_tool_config.json")


class FolderMixin:
    def P(self, p):
        return self.proj_of[p]

    def rel_of(self, p):
        return os.path.relpath(p, self.P(p)["img_root"])

    def disp(self, p):
        rel = self.rel_of(p)
        return f"{self.P(p)['name']}/{rel}" if len(self.projects) > 1 else rel

    @staticmethod
    def _has_both(p):
        return (os.path.isdir(os.path.join(p, "images"))
                and os.path.isdir(os.path.join(p, "labels")))

    def _find_roots(self, d):
        d = os.path.normpath(d)
        if self._has_both(d):
            return [(d, os.path.join(d, "images"))]
        if os.path.basename(d).lower() == "images":
            return [(os.path.dirname(d), d)]
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
        return [(d, d)]

    # 💡 마지막 폴더뿐만 아니라 현재 보고 있던 마지막 이미지 경로까지 함께 저장
    def save_last_folder(self, picked, last_img=None):
        try:
            data = {
                "last_picked": picked,
                "last_img": last_img if last_img and os.path.exists(last_img) else None
            }
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DEBUG] 설정 저장 실패: {e}")

    def load_last_folder(self):
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    picked = data.get("last_picked", [])
                    last_img = data.get("last_img", None)
                    valid_picked = [(pr, ir) for pr, ir in picked if os.path.isdir(pr)]
                    if valid_picked:
                        return valid_picked, last_img
        except Exception as e:
            print(f"[DEBUG] 설정 읽기 실패: {e}")
        return None, None

    def open_folder(self, auto_picked=None, auto_last_img=None):
        self.save_current_note()

        picked = auto_picked
        if not picked:
            picked = []
            while True:
                d = filedialog.askdirectory(title="최상위 폴더 선택")
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
                        if f.lower().endswith((".txt", ".csv")):
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
            if not auto_picked:
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
                out_p = self.out_paths(p)
                if self.P(p)["out_dir"] and os.path.exists(out_p["label"]):
                    self.done.add(p)

        self.passed = set(self.done)

        self.idx = -1
        # 폴더 열릴 때 마지막 작업 이미지(auto_last_img)가 있으면 그 위치로 지정해서 로드
        self.load_folder("__all__", keep=auto_last_img)

    def on_folder_select(self, _=None):
        i = self.folderSelect.current()
        if i >= 0:
            self.save_current_note()
            self.idx = -1
            self.load_folder(self.folder_keys[i])

    def load_folder(self, key, keep=None):
        if key == "__all__":
            all_images = [p for k in sorted(self.folders) for p in self.folders[k]]
        else:
            all_images = self.folders[key]
        self.folder_images = list(dict.fromkeys(all_images))
        self.apply_filter(keep=keep)

    def _match_filter(self, p):
        if self.view_filter == "todo":
            return p not in self.done and p not in self.passed
        if self.view_filter == "done":
            return p in self.done or p in self.passed
        return True

    def apply_filter(self, keep=None):
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
        
        # 💡 이 부분이 핵심: 지정된 keep(마지막 작업 이미지)이 있으면 정확히 그 이미지부터 시작
        if keep and keep in self.images:
            resume_idx = self.images.index(keep)
        else:
            resume_idx = 0
            for i, p in enumerate(self.images):
                if p not in self.done and p not in self.passed:
                    resume_idx = i
                    break
        self.show_image(resume_idx)

    def on_filter_select(self, _=None):
        i = self.filterSelect.current()
        if i < 0:
            return
        self.view_filter = VIEW_FILTERS[i][0]
        if self.folder_images:
            self.apply_filter(keep=self.cur_path())

    def update_filter_counts(self):
        n_all = len(self.folder_images)
        n_done = sum(1 for p in self.folder_images if p in self.done or p in self.passed)
        counts = {"all": n_all, "todo": n_all - n_done, "done": n_done}
        self.filterSelect["values"] = [f"{name} ({counts[key]})" for key, name in VIEW_FILTERS]
        self.filterSelect.current([key for key, _ in VIEW_FILTERS].index(self.view_filter))

    def refresh_image_list(self):
        self.imageList.delete(0, "end")
        for i, p in enumerate(self.images):
            self.imageList.insert("end", self.disp(p))
            if p in self.done or p in self.passed:
                fg = DONE_LIST_COLOR
            elif self.auto_pred.get(p):
                fg = AUTO_LIST_COLOR
            else:
                fg = "black"
            self.imageList.itemconfig(i, fg=fg)

    def update_progress(self):
        total = len(self.folder_images)
        done = sum(1 for p in self.folder_images if p in self.done or p in self.passed)
        pct = done / total * 100 if total else 0
        self.progressBar["value"] = pct
        self.progressText.config(text=f"{done} / {total}  ({pct:.1f}%)")

    def on_image_list_select(self, _=None):
        sel = self.imageList.curselection()
        if sel and sel[0] != self.idx:
            self.show_image(sel[0])