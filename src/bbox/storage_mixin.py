"""저장 / 불러오기 — 출력 폴더 구조, 라벨 csv, 이슈 txt, Class4 확인용 폴더"""
import os
import shutil
from datetime import datetime
from tkinter import messagebox

from src.config import CLASS_NAMES, ISSUE_ID, UNUSED_CLASS, DONE_LIST_COLOR


class StorageMixin:
    # ── 경로 ──
    def default_out_dir(self, pj):
        parent = os.path.dirname(pj["proj"])
        return os.path.join(parent, os.path.basename(pj["proj"]) + "_labeled")

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
    def ensure_out_dir(self, pj):
        if pj["out_dir"]:
            return
        pj["out_dir"] = self.default_out_dir(pj)
        for sub in ("images", "labels", "issues", "class4_check"):
            os.makedirs(os.path.join(pj["out_dir"], sub), exist_ok=True)
        with open(os.path.join(pj["out_dir"], "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(CLASS_NAMES) + "\n")
        messagebox.showinfo("저장 폴더 생성",
                            f"첫 저장이므로 저장 폴더를 생성했습니다.\n\n{pj['out_dir']}\n\n"
                            f"이후 저장되는 이미지와 라벨은 이 폴더에 저장됩니다.")

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
            self.ensure_out_dir(self.P(p))
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
