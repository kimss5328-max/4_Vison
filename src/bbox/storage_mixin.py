"""저장 / 불러오기 — 저장 위치 선택, 라벨 csv, 이슈 txt, Class4 확인용 폴더
   원본 폴더는 읽기만 하고, 모든 결과는 사용자가 고른 저장 위치에 만든다"""
import os
import shutil
from datetime import datetime
from tkinter import filedialog, messagebox

from src.config import CLASS_NAMES, ISSUE_ID, UNUSED_CLASS, DONE_LIST_COLOR


class StorageMixin:
    # ── 저장 위치 선택 ──
    @staticmethod
    def _is_inside(path, base):
        """path 가 base 와 같거나 그 안에 있는지"""
        try:
            return os.path.commonpath([path, base]) == base
        except ValueError:          # 서로 다른 드라이브 (Windows)
            return False

    def ask_out_dir(self, pj):
        """저장 위치를 사용자에게 고르게 한다. 원본 폴더 안은 거부. 취소하면 None"""
        src = os.path.abspath(pj["proj"])
        while True:
            d = filedialog.askdirectory(
                title=f"[{pj['name']}] 저장 위치 선택 — 여기에 images / labels / issues 폴더가 생성됩니다",
                initialdir=os.path.dirname(src))
            if not d:
                return None
            d = os.path.abspath(d)
            if self._is_inside(d, src):
                messagebox.showwarning("저장 위치 오류",
                                       f"원본 폴더 안에는 저장할 수 없습니다.\n"
                                       f"원본 폴더 바깥의 위치를 선택하세요.\n\n원본: {src}")
                continue
            return d

    def set_out_dir(self, pj, d):
        """저장 위치 확정 → 하위 폴더 생성 + 그 위치에 이미 저장된 이미지 표시. 반환: 기존 저장본 수"""
        pj["out_dir"] = d
        for sub in ("images", "labels", "issues", "class4_check"):
            os.makedirs(os.path.join(d, sub), exist_ok=True)
        with open(os.path.join(d, "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(CLASS_NAMES) + "\n")

        cur = self.cur_path()
        n_saved = 0
        for p, owner in self.proj_of.items():
            if owner is not pj or not os.path.exists(self.out_paths(p)["label"]):
                continue
            n_saved += 1
            self.done.add(p)
            self.passed.add(p)
            if p != cur:                 # 다음에 열 때 저장본을 읽도록 기억해 둔 내용 비움
                self.annotations.pop(p, None)
                self.notes.pop(p, None)

        self.refresh_image_list()
        if 0 <= self.idx < len(self.images):
            self.imageList.selection_set(self.idx)
        self.update_progress()
        self.update_filter_counts()
        self.update_out_dir_label()
        return n_saved

    def choose_out_dir(self):
        """[저장 위치 선택] 버튼 — 작업 전에 미리 지정하거나 이어서 작업할 때 사용"""
        p = self.cur_path()
        if not p:
            messagebox.showinfo("알림", "먼저 폴더를 열어 주세요.")
            return
        pj = self.P(p)
        d = self.ask_out_dir(pj)
        if not d:
            return
        try:
            n = self.set_out_dir(pj, d)
        except OSError as e:
            messagebox.showerror("저장 위치 오류", str(e))
            return
        if os.path.exists(self.out_paths(p)["label"]) and messagebox.askyesno(
                "저장본 불러오기",
                "선택한 위치에 현재 이미지의 저장본이 있습니다.\n"
                "저장본으로 화면을 바꿀까요?\n\n(아니오: 지금 화면 유지 — 저장하면 덮어씀)"):
            self.reload_current()
        self.status(f"저장 위치: {d}   (기존 저장본 {n}장)")

    def ensure_out_dir(self, pj):
        """저장 직전에 호출. 저장 위치가 없으면 고르게 한다. 취소하면 False"""
        if pj["out_dir"]:
            return True
        d = self.ask_out_dir(pj)
        if not d:
            self.status("저장 위치를 선택하지 않아 저장을 취소했습니다.")
            return False
        self.set_out_dir(pj, d)
        if os.path.exists(self.out_paths(self.cur_path())["label"]) and not messagebox.askyesno(
                "덮어쓰기 확인",
                "선택한 위치에 현재 이미지의 저장본이 이미 있습니다.\n"
                "지금 화면의 박스로 덮어쓸까요?\n\n(아니오: 저장을 취소하고 저장본을 불러옵니다)"):
            self.reload_current()
            return False
        messagebox.showinfo("저장 위치 지정",
                            f"저장 위치를 지정했습니다.\n\n{d}\n\n"
                            f"images / labels / issues / class4_check 폴더가 생성되었고,\n"
                            f"이후 이 작업의 저장은 모두 이 위치에 됩니다.")
        return True

    def reload_current(self):
        """현재 이미지를 저장본 기준으로 다시 읽어 화면 갱신"""
        p = self.cur_path()
        self.pending = None
        self.selected = []
        self.annotations[p], self.notes[p] = self.load_saved(p)
        self.issueNote.delete("1.0", "end")
        self.issueNote.insert("1.0", self.notes[p])
        self.redraw_boxes()
        self.refresh_info()

    def update_out_dir_label(self):
        p = self.cur_path()
        od = self.P(p)["out_dir"] if p else None
        self.outDirLabel.config(text=f"저장 위치: {od}" if od else "저장 위치: (미지정 — 첫 저장 때 선택)")

    # ── 경로 ──

    def out_paths(self, p):
        od = self.P(p)["out_dir"]
        rel = self.rel_of(p)
        stem = os.path.splitext(rel)[0]
        name = os.path.basename(stem)
        issue_dir = os.path.join(od, "issues", stem)
        c4_dir = os.path.join(od, "class4_check", stem)
        return {"label": os.path.join(od, "labels", stem + ".csv"),
                "image": os.path.join(od, "images", rel),
                "issue_dir": issue_dir,
                "issue_img": os.path.join(issue_dir, os.path.basename(p)),
                "issue_txt": os.path.join(issue_dir, name + "_issue.txt"),
                "c4_dir": c4_dir,
                "c4_img": os.path.join(c4_dir, os.path.basename(p)),
                "c4_txt": os.path.join(c4_dir, name + ".csv")}

    def raw_label_path(self, p):
        """원본(입력) 라벨 파일 찾기 — labels 폴더 색인 → 같은 위치의 csv/txt 순"""
        pj = self.P(p)
        rel = os.path.splitext(self.rel_of(p))[0]
        q = pj["by_rel"].get(rel) or pj["by_name"].get(os.path.basename(rel))
        if q:
            return q
        base_csv = os.path.splitext(p)[0] + ".csv"
        base_txt = os.path.splitext(p)[0] + ".txt"
        alt_csv = base_csv.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        alt_txt = base_txt.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
        for q in (alt_csv, base_csv, alt_txt, base_txt):
            if os.path.exists(q):
                return q
        return None

    # ── 읽기 ──
    def read_label_file(self, path):
        """csv(쉼표) / txt(공백) 라벨 모두 읽기"""
        boxes = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                v = line.replace(",", " ").split()
                if len(v) == 5:
                    try:
                        boxes.append(self.yolo_to_box(int(v[0]), *map(float, v[1:])))
                    except ValueError:
                        pass
        return boxes

    def load_saved(self, p):
        """→ (박스 리스트, 이슈 노트). 저장본이 있으면 저장본, 없으면 원본 라벨"""
        raw = self.raw_label_path(p)
        if not self.P(p)["out_dir"]:
            return (self.read_label_file(raw) if raw else []), ""
        paths = self.out_paths(p)
        if os.path.exists(paths["label"]):
            boxes = self.read_label_file(paths["label"])
        elif raw:
            boxes = self.read_label_file(raw)
        else:
            boxes = []

        note = ""
        if os.path.exists(paths["issue_txt"]):
            section, lines = None, []
            with open(paths["issue_txt"], encoding="utf-8") as f:
                for line in f.read().splitlines():
                    if line.startswith("[이슈 박스]"):
                        section = "box"
                    elif line.startswith("[이슈 내용]"):
                        section = "note"
                    elif line.startswith("작성자:") and not self.workerVar.get():
                        self.workerVar.set(line.split(":", 1)[1].strip())
                    elif section == "box":
                        v = line.replace(",", " ").split()
                        if len(v) == 4:
                            boxes.append(self.yolo_to_box(ISSUE_ID, *map(float, v)))
                    elif section == "note":
                        lines.append(line)
            note = "\n".join(lines).strip()
        return boxes, note

    # ── 쓰기 ──
    @staticmethod
    def copy_if_needed(src, dst):
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            return
        shutil.copy2(src, dst)

    def _write_label_csv(self, path, boxes):
        """클래스 미지정·이슈 박스를 뺀 나머지를 'cls,xc,yc,w,h' 로 저장"""
        with open(path, "w", encoding="utf-8") as f:
            for b in boxes:
                if b["cls"] is None or b["cls"] == ISSUE_ID:
                    continue
                xc, yc, w, h = self.box_to_yolo(b)
                f.write(f"{b['cls']},{xc:.6f},{yc:.6f},{w:.6f},{h:.6f}\n")

    def _write_issue_txt(self, p, path, issue_boxes, note):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"작성자: {self.workerVar.get().strip()}\n")
            f.write(f"이미지: {self.disp(p)}\n")
            f.write(f"저장시각: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("[이슈 박스] (x_center y_center width height)\n")
            for b in issue_boxes:
                f.write("{:.6f} {:.6f} {:.6f} {:.6f}\n".format(*self.box_to_yolo(b)))
            f.write("[이슈 내용]\n")
            f.write(note + "\n")

    def save(self):
        p = self.cur_path()
        if not p or not self.img:
            return False
        self.discard_pending()
        self.save_current_note()
        try:
            if not self.ensure_out_dir(self.P(p)):      # 저장 위치가 없으면 여기서 선택
                return False
            paths = self.out_paths(p)
            boxes = self.cur_boxes()

            # 1) 라벨(csv) + 이미지
            os.makedirs(os.path.dirname(paths["label"]), exist_ok=True)
            os.makedirs(os.path.dirname(paths["image"]), exist_ok=True)
            self._write_label_csv(paths["label"], boxes)
            self.copy_if_needed(p, paths["image"])

            # 2) Class 4 박스가 있으면 삭제하지 않고 별도 폴더에도 저장 (확인용)
            if any(b["cls"] == UNUSED_CLASS for b in boxes):
                os.makedirs(paths["c4_dir"], exist_ok=True)
                self.copy_if_needed(p, paths["c4_img"])
                self._write_label_csv(paths["c4_txt"], boxes)
            elif os.path.isdir(paths["c4_dir"]):
                shutil.rmtree(paths["c4_dir"], ignore_errors=True)

            # 3) 이슈: 이미지 + txt 를 하나의 폴더로
            issue_boxes = [b for b in boxes if b["cls"] == ISSUE_ID]
            note = self.notes.get(p, "").strip()
            if issue_boxes or note:
                os.makedirs(paths["issue_dir"], exist_ok=True)
                self.copy_if_needed(p, paths["issue_img"])
                self._write_issue_txt(p, paths["issue_txt"], issue_boxes, note)
        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

        # 저장 = 사람이 확인한 최종 라벨 → 자동 BBox 표시 해제
        for b in self.cur_boxes():
            b["auto"] = False
        self.auto_pred.pop(p, None)
        self.redraw_boxes()
        self.refresh_info()

        self.done.add(p)
        self.imageList.itemconfig(self.idx, fg=DONE_LIST_COLOR)
        self.update_filter_counts()
        self.status(f"저장 완료: {self.disp(p)}")
        return True

    def save_and_next(self):
        if not self.save():
            return
        self.next_image("마지막 이미지까지 저장했습니다.")
