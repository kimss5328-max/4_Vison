"""저장 / 불러오기 — 출력 폴더 구조, 라벨 csv, 이슈 txt, 리뷰 평면 폴더, Class4 확인용 폴더"""
import os
import shutil
import csv
from datetime import datetime
from tkinter import messagebox
from PIL import Image, ImageDraw

from src.config import CLASS_NAMES, ISSUE_ID, UNUSED_CLASS, DONE_LIST_COLOR


class StorageMixin:
    # ── 경로 관리 ──
    def default_out_dir(self, pj):
        parent = os.path.dirname(pj["proj"])
        return os.path.join(parent, os.path.basename(pj["proj"]) + "_labeled")

    def out_paths(self, p):
        pj = self.P(p)
        od = pj.get("out_dir")
        if not od:
            od = self.default_out_dir(pj)
            pj["out_dir"] = od
        rel = self.rel_of(p)
        stem = os.path.splitext(rel)[0]
        
        flat_prefix = f"{pj['name']}_" + rel.replace(os.sep, "_").rsplit(".", 1)[0]
        orig_ext = os.path.splitext(p)[1]

        issue_dir = os.path.join(od, "issues", stem)
        review_dir = os.path.join(od, "reviews")
        c4_dir = os.path.join(od, "class4_check", stem)
        
        return {
            "label": os.path.join(od, "labels", stem + ".csv"),
            "image": os.path.join(od, "images", rel),
            "image_dir": os.path.join(od, "images", os.path.dirname(rel)),
            "label_in_image_dir": os.path.join(od, "images", stem + ".csv"),
            
            "issue_dir": issue_dir,
            "issue_img": os.path.join(issue_dir, os.path.basename(p)),
            "issue_txt": os.path.join(issue_dir, os.path.basename(stem) + "_issue.txt"),
            "issue_csv": os.path.join(issue_dir, os.path.basename(stem) + ".csv"),
            
            "review_dir": review_dir,
            "review_img": os.path.join(review_dir, flat_prefix + orig_ext),
            "review_txt": os.path.join(review_dir, flat_prefix + "_review.txt"),
            "review_csv": os.path.join(review_dir, flat_prefix + ".csv"),
            
            "c4_dir": c4_dir,
            "c4_img": os.path.join(c4_dir, os.path.basename(p)),
            "c4_txt": os.path.join(c4_dir, os.path.basename(stem) + ".csv")
        }

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

    # ── 읽기 로직 ──
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
        pj = self.P(p)
        if not pj.get("out_dir"):
            pj["out_dir"] = self.default_out_dir(pj)
            
        paths = self.out_paths(p)
        if os.path.exists(paths["label"]):
            boxes = self.read_label_file(paths["label"])
        elif raw:
            boxes = self.read_label_file(raw)
        else:
            boxes = []

        note = ""
        target_txt = paths["issue_txt"] if os.path.exists(paths["issue_txt"]) else paths["review_txt"]
        if os.path.exists(target_txt):
            section, lines = None, []
            with open(target_txt, encoding="utf-8") as f:
                for line in f.read().splitlines():
                    if line.startswith("[이슈 박스]"):
                        section = "box"
                    elif line.startswith("[이슈 내용]") or line.startswith("[리뷰 내용]"):
                        section = "note"
                    elif line.startswith("작성자:") and hasattr(self, "workerVar") and not self.workerVar.get():
                        self.workerVar.set(line.split(":", 1)[1].strip())
                    elif section == "box":
                        v = line.replace(",", " ").split()
                        if len(v) == 4:
                            boxes.append(self.yolo_to_box(ISSUE_ID, *map(float, v)))
                    elif section == "note":
                        lines.append(line)
            note = "\n".join(lines).strip()
        return boxes, note

    # ── 쓰기 및 저장 로직 ──
    def ensure_out_dir(self, pj):
        if not pj.get("out_dir"):
            pj["out_dir"] = self.default_out_dir(pj)
        
        for sub in ("images", "labels", "issues", "reviews", "class4_check"):
            os.makedirs(os.path.join(pj["out_dir"], sub), exist_ok=True)
            
        classes_path = os.path.join(pj["out_dir"], "classes.txt")
        if not os.path.exists(classes_path):
            with open(classes_path, "w", encoding="utf-8") as f:
                f.write("\n".join(CLASS_NAMES) + "\n")

    @staticmethod
    def copy_if_needed(src, dst):
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            return
        shutil.copy2(src, dst)

    def draw_and_save_image(self, p, dest_img_path, boxes):
        """이미지를 열어 박스와 텍스트를 그린 후 저장합니다."""
        try:
            img_to_draw = Image.open(p).convert("RGB")
            draw = ImageDraw.Draw(img_to_draw)
            for b in boxes:
                x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
                color = self.color_of(b["cls"])
                tag = "ISSUE" if b["cls"] == ISSUE_ID else ("?" if b["cls"] is None else str(b["cls"]))
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                draw.text((x1 + 4, y1 + 4), tag, fill=color)
            img_to_draw.save(dest_img_path)
        except Exception:
            self.copy_if_needed(p, dest_img_path)

    def _write_label_csv(self, path, boxes):
        """클래스 미지정·이슈 박스를 뺀 나머지를 'cls,xc,yc,w,h' (쉼표 구분 CSV)로 저장"""
        with open(path, "w", encoding="utf-8") as f:
            for b in boxes:
                if b["cls"] is None or b["cls"] == ISSUE_ID:
                    continue
                xc, yc, w, h = self.box_to_yolo(b)
                f.write(f"{b['cls']},{xc:.6f},{yc:.6f},{w:.6f},{h:.6f}\n")

    def _write_issue_txt(self, p, path, issue_boxes, note):
        worker_name = self.workerVar.get().strip() if hasattr(self, "workerVar") and self.workerVar.get() else "작업자"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"작성자: {worker_name}\n")
            f.write(f"이미지: {self.disp(p)}\n")
            f.write(f"저장시각: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("[이슈 박스] (x_center y_center width height)\n")
            for b in issue_boxes:
                f.write("{:.6f} {:.6f} {:.6f} {:.6f}\n".format(*self.box_to_yolo(b)))
            f.write("[이슈 내용]\n")
            f.write(note + "\n")

    def _write_review_txt(self, p, path, note):
        worker_name = self.workerVar.get().strip() if hasattr(self, "workerVar") and self.workerVar.get() else "작업자"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"작성자: {worker_name}\n")
            f.write(f"이미지: {self.disp(p)}\n")
            f.write(f"저장시각: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("[리뷰 내용]\n")
            f.write(note + "\n")

    def update_dataset_manifest(self, p):
        """
        manifests/dataset_manifest.csv 파일에 이미지별 상세 스펙 기록
        - file_name, source_dataset, original_split, scene_type, worker, status, qa_status, review_reason
        """
        pj = self.P(p)
        parent_dir = os.path.dirname(pj["proj"])
        manifest_dir = os.path.join(parent_dir, "manifests")
        os.makedirs(manifest_dir, exist_ok=True)
        manifest_path = os.path.join(manifest_dir, "dataset_manifest.csv")

        file_name = os.path.basename(p)
        source_dataset = pj["name"]  # 예: dataset2
        
        # 경로 파싱을 통한 original_split 및 scene_type 추출
        # 예: train/kimchi_with_target/sub/img.jpg 구조인 경우
        rel = self.rel_of(p)
        path_parts = rel.split(os.sep)
        
        original_split = path_parts[0] if len(path_parts) > 1 else "train"
        scene_type = path_parts[1] if len(path_parts) > 2 else (path_parts[0] if len(path_parts) > 1 else "kimchi_with_target")

        worker = self.workerVar.get().strip() if hasattr(self, "workerVar") and self.workerVar.get() else "홍길동"

        boxes = self.cur_boxes()
        note = self.notes.get(p, "").strip()
        has_issue_box = any(b["cls"] == ISSUE_ID for b in boxes)
        has_c4 = any(b["cls"] == UNUSED_CLASS for b in boxes)
        is_review = self.review_status.get(p) == "review" or has_c4

        if has_issue_box:
            status = "ISSUE"
            qa_status = "WAIT"
            review_reason = "issue_box_exist"
        elif is_review or note:
            status = "REVIEW"
            qa_status = "WAIT"
            review_reason = "class_ambiguous" if has_c4 else ("review_checked" if is_review else "note_exist")
        else:
            status = "EDITED" if getattr(self, "is_modified", False) else "DONE"
            qa_status = "PASS"
            review_reason = ""

        row_data = {
            "file_name": file_name,
            "source_dataset": source_dataset,
            "original_split": original_split,
            "scene_type": scene_type,
            "worker": worker,
            "status": status,
            "qa_status": qa_status,
            "review_reason": review_reason,
        }

        manifest_columns = [
            "file_name", "source_dataset", "original_split", 
            "scene_type", "worker", "status", "qa_status", "review_reason"
        ]
        
        rows = []
        updated = False
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("file_name") == file_name:
                        r.update(row_data)
                        updated = True
                    rows.append(r)

        if not updated:
            rows.append(row_data)

        with open(manifest_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=manifest_columns)
            writer.writeheader()
            for r in rows:
                clean_row = {col: r.get(col, "") for col in manifest_columns}
                writer.writerow(clean_row)

    def save(self):
        p = self.cur_path()
        if not p or not self.img:
            return False
        self.discard_pending()
        self.save_current_note()
        try:
            pj = self.P(p)
            self.ensure_out_dir(pj)
            paths = self.out_paths(p)
            boxes = self.cur_boxes()

            # 1) 기본 라벨(CSV) 및 원본 이미지 저장
            os.makedirs(os.path.dirname(paths["label"]), exist_ok=True)
            os.makedirs(paths["image_dir"], exist_ok=True)
            self._write_label_csv(paths["label"], boxes)
            self.copy_if_needed(p, paths["image"])
            self._write_label_csv(paths["label_in_image_dir"], boxes)

            # 2) Class 4 박스가 포함된 경우 확인용 폴더에 이미지 + CSV 세트 저장
            if any(b["cls"] == UNUSED_CLASS for b in boxes):
                os.makedirs(paths["c4_dir"], exist_ok=True)
                self.draw_and_save_image(p, paths["c4_img"], boxes)
                self._write_label_csv(paths["c4_txt"], boxes)
            elif os.path.isdir(paths["c4_dir"]):
                shutil.rmtree(paths["c4_dir"], ignore_errors=True)

            # 3) 이슈 박스가 있는 경우 이슈 폴더에 이미지 + 텍스트 + CSV 세트 저장
            issue_boxes = [b for b in boxes if b["cls"] == ISSUE_ID]
            if issue_boxes:
                os.makedirs(paths["issue_dir"], exist_ok=True)
                self.draw_and_save_image(p, paths["issue_img"], boxes)
                self._write_issue_txt(p, paths["issue_txt"], issue_boxes, self.notes.get(p, "").strip())
                self._write_label_csv(paths["issue_csv"], boxes)
            elif os.path.isdir(paths["issue_dir"]):
                shutil.rmtree(paths["issue_dir"], ignore_errors=True)

            # 4) 리뷰 체크되거나 노트가 있는 경우 reviews/ 평면 폴더에 이미지 + 텍스트 + CSV 세트 저장
            is_review = self.review_status.get(p) == "review" or any(b["cls"] == UNUSED_CLASS for b in boxes)
            note = self.notes.get(p, "").strip()
            if is_review or note:
                os.makedirs(paths["review_dir"], exist_ok=True)
                self.draw_and_save_image(p, paths["review_img"], boxes)
                self._write_review_txt(p, paths["review_txt"], note)
                self._write_label_csv(paths["review_csv"], boxes)
            else:
                if os.path.exists(paths["review_img"]):
                    os.remove(paths["review_img"])
                if os.path.exists(paths["review_txt"]):
                    os.remove(paths["review_txt"])
                if os.path.exists(paths["review_csv"]):
                    os.remove(paths["review_csv"])

            # 5) manifests/dataset_manifest.csv 상태 기록
            self.update_dataset_manifest(p)

        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

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