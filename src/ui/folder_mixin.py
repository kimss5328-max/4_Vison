"""폴더 열기 / 프로젝트 구성 / 이미지 목록 / 단계 보기 / 진행률 / 마지막 폴더 기억"""
import json
import os
import queue
import threading
from tkinter import filedialog, messagebox

from src.config import (IMG_EXTS, AUTO_LIST_COLOR, DONE_LIST_COLOR, STAGE_FILTERS,
                        PICK_START_DIR, SETTINGS_PATH, BASE_DIR, DATASET_NAMES)
from src.validation.auto_validator import run_validation, summarize, print_console
from src.bbox.manifest import split_of

# 프로그램 폴더(visol04) 전체 — 원본으로 열 수 없고, 상위 폴더를 열어도 탐색에서 통째로 제외
#   (안에 data 결과, backup 사본, venv 등이 있어 원본처럼 읽히면 안 됨)
PROGRAM_ROOT = os.path.normpath(BASE_DIR)


class FolderMixin:
    # ── 프로젝트 / 경로 도우미 ──
    def P(self, p):
        """이미지 경로 → 소속 프로젝트(dict)"""
        return self.proj_of[p]

    def rel_of(self, p):
        """기록·저장에 쓰는 이미지 경로 — 항상 images 폴더 기준 (예: 'train/a.jpg')
           데이터셋 폴더를 열든 images/train 을 직접 열든 같은 값 → 이력·단계 폴더가 나뉘지 않음"""
        return os.path.relpath(p, self.P(p)["img_base"])

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

    @staticmethod
    def is_result_path(path):
        """프로그램 폴더(visol04) 자체이거나 그 안쪽인지"""
        path = os.path.normpath(os.path.abspath(path))
        try:
            return os.path.commonpath([path, PROGRAM_ROOT]) == PROGRAM_ROOT
        except ValueError:              # 서로 다른 드라이브 (Windows)
            return False

    def _skip_dir(self, parent, name, root):
        """원본 탐색 중 건너뛸 폴더 — 이전 버전 결과 폴더 + 프로그램 폴더(visol04) 전체"""
        return (self.is_output_dir(parent, name, root)
                or self.is_result_path(os.path.join(parent, name)))

    @staticmethod
    def bases_of(proj, img_root):
        """연 폴더 → (데이터셋 폴더, images 기준 폴더, 읽을 labels 폴더, labels 기준 폴더)
           - 데이터셋 폴더를 연 경우      : 데이터셋/images, 데이터셋/labels
           - images/train 을 직접 연 경우 : 기준은 위쪽 images·labels, 읽는 곳은 labels/train
           - images 구조가 없는 폴더      : 연 폴더 자체 (라벨 폴더 없음)"""
        if img_root != proj:                                     # 데이터셋 폴더(또는 images 폴더)를 연 경우
            lbl = os.path.join(proj, "labels")
            lbl = lbl if os.path.isdir(lbl) else None
            return proj, img_root, lbl, lbl
        parts = os.path.normpath(img_root).split(os.sep)
        for i in range(len(parts) - 1, -1, -1):
            if parts[i].lower() == "images":                     # .../데이터셋/images/train
                dataset = os.sep.join(parts[:i]) or os.sep
                img_base = os.sep.join(parts[:i + 1])
                lbl_base = os.path.join(dataset, "labels")
                lbl_root = os.sep.join(parts[:i] + ["labels"] + parts[i + 1:])
                if not os.path.isdir(lbl_root):
                    lbl_root = lbl_base = None
                return dataset, img_base, lbl_root, lbl_base
        return img_root, img_root, None, None

    # ── 마지막 폴더 기억 (프로그램 폴더 밖 ~/.labeling_tool_config.json) ──
    @staticmethod
    def save_last_folder(picked, last_img=None):
        try:
            data = {"last_picked": picked,
                    "last_img": last_img if last_img and os.path.exists(last_img) else None}
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def load_last_folder():
        """→ (picked, last_img). 없거나 폴더가 사라졌으면 (None, None)"""
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            picked = [(pr, ir) for pr, ir in data.get("last_picked", []) if os.path.isdir(pr)]
            if picked:
                return picked, data.get("last_img")
        except (OSError, ValueError, TypeError):
            pass
        return None, None

    def remember_folder(self):
        """지금 열린 폴더와 보던 이미지를 기억 (저장·종료 때 호출)"""
        if self.projects:
            picked = [(pj["proj"], pj["img_root"]) for pj in self.projects]
            self.save_last_folder(picked, last_img=self.cur_path())

    # ── 폴더 열기 ──
    def open_folder(self, auto_picked=None, auto_last_img=None):
        """auto_picked: 프로그램 시작 시 마지막 폴더를 자동으로 열 때 (선택 창 없이)"""
        self.save_current_note()

        picked = auto_picked
        if not picked:
            picked = []
            start = PICK_START_DIR if os.path.isdir(PICK_START_DIR) else os.path.expanduser("~")
            while True:
                d = filedialog.askdirectory(
                    title="이미지 폴더 선택 (images + labels 가 있는 폴더, 또는 그 상위 폴더)",
                    initialdir=start)
                if not d:
                    break
                if self.is_result_path(d):
                    messagebox.showwarning(
                        "원본 폴더 아님",
                        "프로그램 폴더(visol04)와 그 안쪽(data, backup 등)은 원본으로 열 수 없습니다.\n"
                        "원본 이미지 폴더(images + labels)를 선택하세요.\n\n"
                        "작업한 이미지는 원본 폴더를 열면 단계 보기에서 확인할 수 있습니다.")
                    continue
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
        picked = [item for item in picked if not self.is_result_path(item[0])]
        if not picked:                   # 예) 마지막으로 연 폴더가 프로그램 폴더였던 경우
            self.status("프로그램 폴더(visol04)는 원본으로 열 수 없습니다. [폴더 열기]로 원본 이미지 폴더를 선택하세요.")
            return

        projects, proj_of, folders = [], {}, {}
        used = set()
        for proj, img_root in picked:
            name = os.path.basename(proj)
            if name in used:
                name += f"({len(used)})"
            used.add(name)
            dataset_dir, img_base, lbl_root, lbl_base = self.bases_of(proj, img_root)
            folder = os.path.basename(os.path.normpath(dataset_dir))
            pj = {"proj": proj, "img_root": img_root, "name": name, "lbl_root": lbl_root,
                  "img_base": img_base, "lbl_base": lbl_base,
                  "dataset_folder": folder, "dataset": DATASET_NAMES.get(folder, folder),
                  "out_dir": None, "by_rel": {}, "by_name": {}}
            if lbl_root:
                for dp, dirs, files in os.walk(lbl_root):
                    # 프로그램이 만든 결과 폴더(train_done 등)는 원본 라벨로 읽지 않음
                    dirs[:] = [x for x in dirs if not self._skip_dir(dp, x, lbl_root)]
                    for f in files:
                        if f.lower().endswith((".txt", ".csv")):   # txt / csv 모두 인식
                            q = os.path.join(dp, f)
                            rel = os.path.splitext(os.path.relpath(q, lbl_base))[0]   # 'train/a' 
                            pj["by_rel"][rel] = q
                            pj["by_name"].setdefault(os.path.splitext(f)[0], q)
            projects.append(pj)      # out_dir(저장 위치)는 아래에서 기존 저장본이 있으면 연결, 없으면 첫 저장 때 정함

            for cur, dirs, files in os.walk(img_root):
                dirs[:] = [x for x in dirs if not self._skip_dir(cur, x, img_root)]
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
        self.note_base.clear()
        self.baseline.clear()
        self.done.clear()
        self.passed.clear()
        self.auto_pred.clear()
        # 결과 구조(visol04/data, reviews, manifests)를 바로 준비 →
        # 결과 폴더 구조만 준비 (원본은 복사하지 않고 읽기만). 저장했던 이미지는 초록색 + 단계 보기 바로 사용
        for pj in projects:
            self.prepare_out_dir(pj)
        for p in proj_of:
            if self.saved_stages(p):
                self.done.add(p)
        self.passed = set(self.done)
        self.view_filter = "all"           # 새로 열면 단계 보기는 전체부터
        self.idx = -1
        self.load_folder("__all__", keep=auto_last_img)
        self.remember_folder()
        self.check_splits()
        self.start_validation()

    def check_splits(self):
        """폴더를 열 때 한 번 — 이름 표에 없는 데이터셋 / train·validation 밖의 이미지 알림"""
        unmapped = sorted({pj["dataset_folder"] for pj in self.projects
                           if pj["dataset_folder"] not in DATASET_NAMES})
        if unmapped:
            messagebox.showwarning(
                "source_dataset 확인 필요",
                "데이터셋 이름 표(config.DATASET_NAMES)에 없는 폴더입니다.\n"
                "manifest 의 source_dataset 에 폴더 이름이 그대로 기록됩니다.\n\n"
                + "\n".join(f"  {f}" for f in unmapped))
        unknown = sorted(self.disp(p) for p in self.proj_of if not split_of(p))
        if not unknown:
            return
        dirs = sorted({os.path.dirname(p) for p in self.proj_of if not split_of(p)})
        messagebox.showwarning(
            "original_split 확인 필요",
            f"이미지 {len(unknown)}장이 train / validation 폴더 안에 있지 않습니다.\n"
            f"이 이미지들은 manifest 의 original_split 이 빈칸으로 기록됩니다.\n\n"
            f"폴더 (최대 5개):\n" + "\n".join(f"  {d}" for d in dirs[:5]))

    # ── 자동 validation (원본 검사) ──
    def _validation_jobs(self):
        """프로젝트별 검사 목록 — 쌍은 프로그램이 원본 라벨을 찾는 방식(raw_label_path) 그대로"""
        jobs = []
        for pj in self.projects:
            pairs, used = [], set()
            for p in sorted(q for q, owner in self.proj_of.items() if owner is pj):
                lbl = self.raw_label_path(p)
                if lbl:
                    used.add(os.path.normpath(lbl))
                pairs.append((self.disp(p), p, lbl))
            lbl_root = pj["lbl_root"]
            orphans = [(os.path.relpath(q, lbl_root), q) for q in sorted(pj["by_rel"].values())
                       if os.path.normpath(q) not in used] if lbl_root else []
            jobs.append({"project": pj["name"], "pairs": pairs, "orphans": orphans})
        return jobs

    def start_validation(self):
        """폴더를 열 때 호출 — 검사는 백그라운드, 결과 표시는 메인 스레드(root.after)에서"""
        jobs = self._validation_jobs()
        total = sum(len(j["pairs"]) for j in jobs)
        token = object()                 # 검사 중 다른 폴더를 열면 이전 결과는 무시
        self._validation_token = token
        out = queue.Queue()

        def work():                      # ※ 여기서는 tkinter 를 건드리지 않음
            results = {}
            try:
                for job in jobs:
                    results[job["project"]] = run_validation(job)
                out.put(("ok", results))
            except Exception as e:       # 검사 오류가 프로그램을 멈추지 않게
                out.put(("fail", e))

        def poll():
            if self._validation_token is not token:
                return
            try:
                kind, value = out.get_nowait()
            except queue.Empty:
                self.root.after(200, poll)
                return
            if kind == "fail":
                print(f"자동 검사 오류: {value}")
                self.status(f"자동 검사 중 오류가 발생했습니다: {value}")
                return
            print_console(value)
            popup, line, clean = summarize(value, total)
            self.status(line)
            if clean:
                messagebox.showinfo("자동 검사 결과", popup, parent=self.root)
            else:
                messagebox.showwarning("자동 검사 결과", popup, parent=self.root)

        self.status(f"자동 검사 중... (이미지 {total}장, 작업은 계속 가능)")
        threading.Thread(target=work, daemon=True).start()
        self.root.after(200, poll)

    def on_folder_select(self, _=None):
        i = self.folderSelect.current()
        if i >= 0:
            self.save_current_note()
            self.idx = -1
            self.load_folder(self.folder_keys[i])

    def load_folder(self, key, keep=None):
        if key == "__all__":
            all_images = [p for k in sorted(self.folders) for p in self.folders[k]]
            self.stageRow.pack(fill="x", padx=4, pady=(0, 6))   # (전체 이미지) → 단계 선택 보이기
        else:
            all_images = self.folders[key]
            self.stageRow.pack_forget()                          # 개별 폴더 → 숨기고 전체로
            self.view_filter = "all"
        self.folder_images = list(dict.fromkeys(all_images))
        self.apply_filter(keep=keep)

    # ── 단계 보기 ((전체 이미지) 선택 시: 전체 / working / pass … final / 이슈) ──
    def _filter_keys(self, p):
        """이 이미지가 해당하는 단계 보기 키들"""
        keys = []
        st = self.latest_stage(p)              # 지금 있는 단계 폴더
        if st:
            keys.append(st)
        if self.is_in_progress(p):             # 편집했지만 저장 전
            keys.append("working")
        if self.has_issue(p):                  # 이슈 기록이 있음
            keys.append("issue")
        return keys

    def _match_filter(self, p):
        return self.view_filter == "all" or self.view_filter in self._filter_keys(p)

    def apply_filter(self, keep=None):
        """folder_images 에 단계 보기를 적용해 self.images(작업 목록)를 다시 만든다.
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
        self.update_stage_counts()
        if not self.images:
            self.clear_view()
            name = dict(STAGE_FILTERS)[self.view_filter]
            self.status(f"'{name}' 단계에 해당하는 이미지가 없습니다.")
            return
        if keep in self.images:            # 보던 이미지 계속
            i = self.images.index(keep)
        else:                              # 없으면 아직 저장 안 한 첫 이미지부터
            i = next((k for k, p in enumerate(self.images) if p not in self.done), 0)
        self.show_image(i)

    def on_stage_filter_select(self, _=None):
        i = self.stageSelect.current()
        if i < 0 or not self.folder_images:
            return
        key = STAGE_FILTERS[i][0]
        # 저장 위치를 아직 안 정했으면 단계 폴더를 볼 수 없으니 먼저 고르게 함 (이어서 작업할 때)
        p = self.cur_path() or self.folder_images[0]
        if key != "all" and not self.ensure_out_dir(self.P(p), for_save=False):
            self.update_stage_counts()
            return
        self.view_filter = key
        self.apply_filter(keep=self.cur_path())

    def update_stage_counts(self):
        """단계 선택 상자에 단계별 개수 표시 — 저장할 때마다 갱신"""
        counts = {"all": len(self.folder_images)}
        for key, _ in STAGE_FILTERS[1:]:
            counts[key] = 0
        for p in self.folder_images:
            for key in self._filter_keys(p):
                counts[key] += 1
        self.stageSelect["values"] = [f"{name} ({counts[key]})" for key, name in STAGE_FILTERS]
        self.stageSelect.current([key for key, _ in STAGE_FILTERS].index(self.view_filter))

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
