"""저장 / 불러오기 — 기본 저장 위치는 데이터 폴더 자체, 결과는 원본 하위 폴더의 '_done' 안에 모음
   데이터폴더/
   ├── images/train/            원본 이미지 (그대로)
   │   └── train_done/
   │       ├── yolo/            final 승인 이미지   → 학습용
   │       └── review/          review 판정 이미지
   └── labels/train/            원본 라벨 (그대로)
       └── train_done/
           ├── yolo/            final YOLO txt + classes.txt → 학습용
           ├── csv/             단계별 기록 (1_1차 / 2_2차 / 3_review / 4_final)
           └── issues/          이슈 노트 txt
   train_done 만 지우면 원본만 남은 처음 상태로 돌아감"""
import csv
import os
import shutil
from datetime import datetime
from tkinter import filedialog, messagebox

from src.config import (CLASS_NAMES, ISSUE_ID, UNUSED_CLASS, DONE_LIST_COLOR, STAGES,
                        DONE_SUFFIX, DEFAULT_DONE, DONE_IMG_FINAL, DONE_IMG_REVIEW,
                        DONE_LBL_YOLO, DONE_LBL_CSV, DONE_LBL_ISSUES, LEGACY_OUT)

CSV_HEADER = ["image", "class_id", "class_name", "x_center", "y_center", "width", "height",
              "stage", "worker_name", "worker_id", "reviewer_name", "reviewer_id", "saved_at"]


class StorageMixin:
    # ── 저장 위치 ──
    @staticmethod
    def default_out_dir(pj):
        """기본 저장 위치
           - images / labels 가 있는 데이터 폴더 → 그 데이터 폴더 자체 (images/·labels/ 아래 하위 폴더)
           - 이미지만 있는 일반 폴더 → 옆에 '폴더명_labeled' (안에 images/·labels/ 를 만들면
             다음에 열 때 데이터 폴더로 잘못 인식되므로 바깥에 만듦)"""
        if pj["img_root"] != pj["proj"]:
            return pj["proj"]
        return pj["proj"] + "_labeled"

    # ── _done 폴더 규칙 ──
    @staticmethod
    def split_rel(rel):
        """원본 상대경로 → (상위 폴더, 나머지)
           'train/a.jpg' → ('train', 'a.jpg') / 'a.jpg' → ('', 'a.jpg')"""
        parts = rel.split(os.sep)
        if len(parts) == 1:
            return "", parts[0]
        return parts[0], os.path.join(*parts[1:])

    @staticmethod
    def done_dir(base, kind, top):
        """base/images/train/train_done  (kind: images | labels, top: 원본 하위 폴더 이름)"""
        if top:
            return os.path.join(base, kind, top, top + DONE_SUFFIX)
        return os.path.join(base, kind, DEFAULT_DONE)

    @staticmethod
    def is_output_dir(parent, name, root):
        """원본 탐색(os.walk) 중 건너뛸 결과 폴더인지 — root: images 또는 labels 폴더"""
        if name == os.path.basename(parent) + DONE_SUFFIX:        # train/train_done
            return True
        if os.path.normpath(parent) == os.path.normpath(root):    # images/ 바로 아래
            kind = os.path.basename(os.path.normpath(root))
            return name == DEFAULT_DONE or name in LEGACY_OUT.get(kind, ())
        return False

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
        # 선택 창 시작 위치: 지금 저장 위치 → 기본 저장 폴더 → 원본의 상위 폴더 순
        start = pj["out_dir"] or os.path.dirname(src)
        while True:
            d = filedialog.askdirectory(
                title=f"[{pj['name']}] 저장 위치 선택 — images / labels / review / issues 폴더가 생성됩니다",
                initialdir=start)
            if not d:
                return None
            d = os.path.abspath(d)
            # 데이터 폴더 자체(기본값)나 바깥은 가능, 데이터 폴더 '안쪽'(images, labels 등)은 불가
            if d != src and self._is_inside(d, src):
                messagebox.showwarning("저장 위치 오류",
                                       f"데이터 폴더 안쪽(images, labels 등)은 고를 수 없습니다.\n"
                                       f"데이터 폴더 자체 또는 바깥의 위치를 선택하세요.\n\n데이터 폴더: {src}")
                continue
            return d

    def out_subdirs(self, d, top):
        """저장 위치 d 의 원본 하위 폴더 top 에 대해 만들 _done 폴더 목록"""
        img_done = self.done_dir(d, "images", top)
        lbl_done = self.done_dir(d, "labels", top)
        subs = [os.path.join(img_done, DONE_IMG_FINAL), os.path.join(img_done, DONE_IMG_REVIEW),
                os.path.join(lbl_done, DONE_LBL_YOLO), os.path.join(lbl_done, DONE_LBL_ISSUES)]
        subs += [os.path.join(lbl_done, DONE_LBL_CSV, folder) for _, folder in STAGES]
        return subs

    def set_out_dir(self, pj, d):
        """저장 위치 확정 → 폴더 생성 + 그 위치에 이미 저장된 이미지 표시. 반환: 기존 저장본 수"""
        pj["out_dir"] = d
        # 이 프로젝트 원본의 하위 폴더(train 등)마다 _done 폴더 생성
        tops = {self.split_rel(self.rel_of(p))[0] for p, owner in self.proj_of.items() if owner is pj}
        for top in tops:
            for sub in self.out_subdirs(d, top):
                os.makedirs(sub, exist_ok=True)
            # 줄 번호 = 클래스 번호 (사용 안 하는 4번도 번호를 맞추기 위해 남겨 둠)
            yolo_dir = os.path.join(self.done_dir(d, "labels", top), DONE_LBL_YOLO)
            with open(os.path.join(yolo_dir, "classes.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(CLASS_NAMES) + "\n")

        cur = self.cur_path()
        n_saved = 0
        for p, owner in self.proj_of.items():
            if owner is not pj:
                continue
            if not self.saved_stages(p):
                self.done.discard(p)     # 위치를 바꾼 경우: 새 위치에 없는 이미지는 저장 표시 해제
                continue
            n_saved += 1
            self.done.add(p)
            self.passed.add(p)
            if p != cur:                 # 다음에 열 때 저장본을 읽도록 기억해 둔 내용 비움
                self.annotations.pop(p, None)
                self.notes.pop(p, None)
                self.review_status.pop(p, None)

        self.refresh_image_list()
        if 0 <= self.idx < len(self.images):
            self.imageList.selection_set(self.idx)
        self.update_progress()
        self.update_stage_counts()
        self.update_out_dir_label()
        return n_saved

    def ensure_out_dir(self, pj, for_save=True):
        """저장 위치가 없으면 고르게 한다. 취소하면 False
           for_save=False: 단계 보기에서 호출 — 현재 이미지 저장본은 묻지 않고 불러옴"""
        if pj["out_dir"]:
            return True
        d = os.path.abspath(self.default_out_dir(pj))
        self.set_out_dir(pj, d)
        p = self.cur_path()
        if p and self.P(p) is pj and self.saved_stages(p) and not for_save:
            self.reload_current()
        elif p and self.P(p) is pj and self.saved_stages(p) and not messagebox.askyesno(
                "덮어쓰기 확인",
                "선택한 위치에 현재 이미지의 저장본이 이미 있습니다.\n"
                "지금 화면의 박스로 저장할까요?\n\n(아니오: 저장을 취소하고 저장본을 불러옵니다)"):
            self.reload_current()
            return False
        messagebox.showinfo("저장 위치 생성",
                            f"저장 위치를 만들었습니다.\n\n{d}\n\n"
                            f"images·labels 의 원본 폴더 아래 _done 폴더(예: train/train_done)가 생성되었고,\n"
                            f"이후 이 작업의 저장은 모두 이 위치에 됩니다.")
        return True

    def change_out_dir(self):
        """[변경] 버튼 — 기본 저장 위치 대신 다른 위치를 쓰고 싶을 때"""
        p = self.cur_path()
        if not p:
            messagebox.showinfo("알림", "먼저 폴더를 열어 주세요.")
            return
        pj = self.P(p)
        d = self.ask_out_dir(pj)
        if not d or d == pj["out_dir"]:
            return
        try:
            n = self.set_out_dir(pj, d)
        except OSError as e:
            messagebox.showerror("저장 위치 오류", str(e))
            return
        if self.saved_stages(p) and messagebox.askyesno(
                "저장본 불러오기",
                "새 위치에 현재 이미지의 저장본이 있습니다.\n"
                "저장본으로 화면을 바꿀까요?\n\n(아니오: 지금 화면 유지 — 저장하면 덮어씀)"):
            self.reload_current()
        self.apply_filter(keep=p)          # 단계 보기가 켜져 있으면 새 위치 기준으로 다시 분류
        self.status(f"저장 위치 변경: {d}   (기존 저장본 {n}장)")

    def reload_current(self):
        """현재 이미지를 저장본 기준으로 다시 읽어 화면 갱신"""
        p = self.cur_path()
        self.pending = None
        self.selected = []
        self.annotations[p], self.notes[p] = self.load_saved(p)
        self.issueNote.delete("1.0", "end")
        self.issueNote.insert("1.0", self.notes[p])
        self.reviewPanel.set_state(self.review_status.get(p, ""))
        self.redraw_boxes()
        self.refresh_info()

    def update_out_dir_label(self):
        p = self.cur_path()
        if not p:
            self.outDirLabel.config(text="저장 위치: -")
            return
        pj = self.P(p)
        top = self.split_rel(self.rel_of(p))[0]
        done = os.path.basename(self.done_dir("", "images", top))        # train_done
        sub = f"images·labels/{top}/{done}" if top else f"images·labels/{done}"
        if pj["out_dir"]:
            self.outDirLabel.config(text=f"저장 위치: {pj['out_dir']}\n→ {sub}")
        else:
            self.outDirLabel.config(text=f"저장 위치: {self.default_out_dir(pj)}\n→ {sub}  (첫 저장 때 생성)")

    # ── 경로 ──
    def out_paths(self, p):
        od = self.P(p)["out_dir"]
        top, inner = self.split_rel(self.rel_of(p))      # 'train', 'a.jpg'
        stem = os.path.splitext(inner)[0]
        img_done = self.done_dir(od, "images", top)       # .../images/train/train_done
        lbl_done = self.done_dir(od, "labels", top)       # .../labels/train/train_done
        return {"csv": {st: os.path.join(lbl_done, DONE_LBL_CSV, folder, stem + ".csv")
                        for st, folder in STAGES},
                "yolo": os.path.join(lbl_done, DONE_LBL_YOLO, stem + ".txt"),
                "image": os.path.join(img_done, DONE_IMG_FINAL, inner),
                "review_img": os.path.join(img_done, DONE_IMG_REVIEW, inner),
                "issue_txt": os.path.join(lbl_done, DONE_LBL_ISSUES, stem + "_issue.txt")}

    def saved_stages(self, p):
        """이 이미지가 저장된 단계 목록 (저장 위치가 없으면 빈 목록)"""
        if not self.P(p)["out_dir"]:
            return []
        csvs = self.out_paths(p)["csv"]
        return [st for st, _ in STAGES if os.path.exists(csvs[st])]

    def latest_stage(self, p):
        """가장 최근에 저장한 단계 (파일 수정 시각 기준)"""
        stages = self.saved_stages(p)
        if not stages:
            return ""
        csvs = self.out_paths(p)["csv"]
        return max(stages, key=lambda st: os.path.getmtime(csvs[st]))

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
        """원본 라벨 읽기 — YOLO txt(공백) / 쉼표 5칸 csv"""
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

    def read_stage_csv(self, path):
        """단계별 csv 읽기 (헤더 있음, 객체 없음 행은 건너뜀)"""
        boxes = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    boxes.append(self.yolo_to_box(int(row["class_id"]),
                                                  float(row["x_center"]), float(row["y_center"]),
                                                  float(row["width"]), float(row["height"])))
                except (KeyError, ValueError, TypeError):
                    pass
        return boxes

    def load_saved(self, p):
        """→ (박스 리스트, 이슈 노트). 최근 단계 저장본이 있으면 저장본, 없으면 원본 라벨"""
        raw = self.raw_label_path(p)
        if not self.P(p)["out_dir"]:
            return (self.read_label_file(raw) if raw else []), ""
        paths = self.out_paths(p)
        st = self.latest_stage(p)
        if st:
            boxes = self.read_stage_csv(paths["csv"][st])
            self.review_status.setdefault(p, st)
        elif raw:
            boxes = self.read_label_file(raw)
        else:
            boxes = []

        note = ""
        if os.path.exists(paths["issue_txt"]):
            in_note, lines = False, []
            with open(paths["issue_txt"], encoding="utf-8") as f:
                for line in f.read().splitlines():
                    if in_note:
                        lines.append(line)
                    elif line.startswith("[이슈 내용]"):
                        in_note = True
                    elif line.startswith("작성자:") and not self.workerVar.get():
                        self.workerVar.set(line.split(":", 1)[1].strip())
            note = "\n".join(lines).strip()
        return boxes, note

    # ── 쓰기 ──
    @staticmethod
    def copy_if_needed(src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            return
        shutil.copy2(src, dst)

    @staticmethod
    def remove_if_exists(path):
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def _label_boxes(boxes):
        """라벨로 저장할 박스 — 클래스 미지정·이슈 박스 제외"""
        return [b for b in boxes if b["cls"] is not None and b["cls"] != ISSUE_ID]

    def _meta(self, stage):
        w = self.workerInfo.get_data()
        r = self.reviewerInfo.get_data()
        return {"stage": stage,
                "worker_name": w["이름"], "worker_id": w["ID"],
                "reviewer_name": r["이름"], "reviewer_id": r["ID"],
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    def _write_stage_csv(self, path, p, boxes, meta):
        """단계별 csv — 박스 1개당 1행 + 작업 정보. 박스가 없으면 '객체 없음' 1행"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tail = [meta[k] for k in CSV_HEADER[7:]]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:   # utf-8-sig: 엑셀 한글 깨짐 방지
            wr = csv.writer(f)
            wr.writerow(CSV_HEADER)
            rows = self._label_boxes(boxes)
            for b in rows:
                xc, yc, w, h = self.box_to_yolo(b)
                wr.writerow([self.rel_of(p), b["cls"], CLASS_NAMES[b["cls"]],
                             f"{xc:.6f}", f"{yc:.6f}", f"{w:.6f}", f"{h:.6f}"] + tail)
            if not rows:
                wr.writerow([self.rel_of(p), "", "객체 없음", "", "", "", ""] + tail)

    def _write_yolo(self, path, boxes):
        """YOLO 학습용 txt — 'cls xc yc w h' (공백 구분)"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for b in self._label_boxes(boxes):
                f.write("{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(b["cls"], *self.box_to_yolo(b)))

    def _save_issue(self, p, path, meta):
        """이슈 노트가 있으면 issues/ 에 txt 저장, 비어 있으면 기존 txt 삭제"""
        note = self.notes.get(p, "").strip()
        if not note:
            self.remove_if_exists(path)
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"이미지: {self.disp(p)}\n")
            f.write(f"원본 경로: {p}\n")
            f.write(f"단계: {meta['stage']}\n")
            f.write(f"작성자: {self.workerVar.get().strip()}\n")
            f.write(f"작업자: {meta['worker_name']} ({meta['worker_id']})\n")
            f.write(f"검수자: {meta['reviewer_name']} ({meta['reviewer_id']})\n")
            f.write(f"저장시각: {meta['saved_at']}\n")
            f.write("[이슈 내용]\n")
            f.write(note + "\n")

    def save(self):
        p = self.cur_path()
        if not p or not self.img:
            return False
        self.discard_pending()
        self.save_current_note()

        # 1) 검수 상태 + 입력 정보 확인
        stage = self.reviewPanel.get_state()
        if not stage:
            messagebox.showwarning("검수 상태", "검수 상태(1차 / 2차 / review / final)를 선택한 뒤 저장하세요.")
            return False
        if not self.stage_allowed(stage):
            who = "작업자" if stage in ("1차", "2차") else "검수자"
            messagebox.showwarning("정보 입력", f"[{stage}] 저장은 {who} 정보(이름, ID)를 모두 입력해야 합니다.")
            return False

        try:
            if not self.ensure_out_dir(self.P(p)):      # 저장 위치가 없으면 여기서 선택
                return False

            # 2) 사용하지 않는 4번 클래스 박스 처리
            boxes = self.cur_boxes()
            n4 = sum(1 for b in boxes if b["cls"] == UNUSED_CLASS)
            if n4:
                if not messagebox.askyesno(
                        "사용 안 함 클래스",
                        f"사용하지 않는 4번 클래스 박스가 {n4}개 있습니다.\n"
                        f"이 박스를 지우고 저장할까요?\n\n"
                        f"(아니오: 저장 취소 — 박스를 선택해 다른 클래스로 바꿀 수 있습니다)"):
                    return False
                boxes[:] = [b for b in boxes if b["cls"] != UNUSED_CLASS]

            # 3) 단계별 기록 (csv)
            paths = self.out_paths(p)
            meta = self._meta(stage)
            self._write_stage_csv(paths["csv"][stage], p, boxes, meta)

            # 4) 단계별 결과물
            if stage == "final":            # 승인 → 학습용 라벨 + 이미지, review 대기에서 제외
                self._write_yolo(paths["yolo"], boxes)
                self.copy_if_needed(p, paths["image"])
                self.remove_if_exists(paths["review_img"])
            elif stage == "review":         # 재작업 필요 → review 폴더로, 이전 final 승인 취소
                self.copy_if_needed(p, paths["review_img"])
                self.remove_if_exists(paths["yolo"])
                self.remove_if_exists(paths["image"])
                self.remove_if_exists(paths["csv"]["final"])

            # 5) 이슈 노트
            self._save_issue(p, paths["issue_txt"], meta)
        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

        # 저장 = 사람이 확인한 라벨 → 자동 BBox 표시 해제
        for b in self.cur_boxes():
            b["auto"] = False
        self.auto_pred.pop(p, None)
        self.redraw_boxes()
        self.refresh_info()

        self.review_status[p] = stage
        self.done.add(p)
        self.imageList.itemconfig(self.idx, fg=DONE_LIST_COLOR)
        self.update_stage_counts()
        self.status(f"저장 완료 [{stage}]: {self.disp(p)}")
        return True

    def save_and_next(self):
        if not self.save():
            return
        self.next_image("마지막 이미지까지 저장했습니다.")