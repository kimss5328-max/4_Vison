"""저장 / 불러오기 — 단계별 폴더 이동 + 기록(csv·manifest)은 추가만
   visol04/                       (프로그램 폴더 = 결과 기준 위치)
   ├── data/
   │   ├── raw/      img, txt     원본 사본 (작업 전)
   │   ├── work/1차/ img, txt     작업 중 + 1차 저장 (이력 csv 에 1차 기록이 있으면 저장됨)
   │   ├── work/2차/ img, txt     2차 저장
   │   ├── final/    img, txt     최종 승인 → 학습용
   │   ├── issues/   img, txt     이슈 노트가 있는 이미지 사본 + 이슈 기록 (추가만)
   │   ├── csv/                   이미지별 이력 csv (추가만 — 1차 검수자 기록도 끝까지 유지)
   │   └── classes.txt
   ├── reviews/      img, txt     검수 대상 (박스를 그려 넣은 확인용 이미지)
   └── manifests/dataset_manifest.csv   전체 진행 대장 (추가만)

   - 작업 시작(첫 편집) → raw 의 img·txt 를 work/1차 로 이동, 이후 편집할 때마다 txt 자동 저장
     (꺼져도 다시 켜면 그 이미지·박스부터 이어서 작업)
   - [저장] → 이력 csv·manifest 에 기록 추가 + 선택한 단계 폴더로 이동
   - 기록은 기존 줄을 고치거나 지우지 않고 덧붙이기만 한다. 원본 폴더는 읽기만 한다."""
import csv
import os
import shutil
from datetime import datetime
from functools import lru_cache
from tkinter import filedialog, messagebox

from PIL import ImageDraw, ImageFont

from src.config import (CLASS_NAMES, ISSUE_ID, UNUSED_CLASS, DONE_LIST_COLOR, COLORS,
                        BASE_DIR, IMG_SUB, TXT_SUB, RAW_DIR, ISSUES_DIR, CSV_DIR, STAGE_DIRS,
                        WORK_START, MANIFEST_DIR, MANIFEST_FILE, DONE_SUFFIX, DEFAULT_DONE,
                        LEGACY_OUT, PREVIEW_FONTS)

# 이미지별 이력 csv — 저장할 때마다 박스 1개당 1행씩 아래에 추가
CSV_HEADER = ["image", "stage", "from", "class_id", "class_name",
              "x_center", "y_center", "width", "height",
              "worker_name", "worker_id", "reviewer_name", "reviewer_id",
              "issue_note", "saved_at"]
# 전체 진행 대장 — 저장할 때마다 이미지 1장당 1행씩 아래에 추가
MANIFEST_HEADER = ["file_name", "source_dataset", "original_split", "scene_type",
                   "stage", "from", "boxes", "worker_name", "worker_id",
                   "reviewer_name", "reviewer_id", "issue", "saved_at"]
# 현재 위치를 찾는 순서 (뒤 단계부터)
LOCATION_ORDER = ("final", "review", "2차", "1차")


@lru_cache(maxsize=8)
def preview_font(size):
    """한글이 되는 글꼴을 찾아 돌려줌 (같은 크기는 한 번만 읽음). 없으면 (기본 글꼴, False)"""
    for path in PREVIEW_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size), True
            except OSError:
                continue
    return ImageFont.load_default(), False


class StorageMixin:
    # ── 결과 폴더 위치 ──
    @staticmethod
    def default_out_dir(pj):
        """기본 결과 기준 위치: 프로그램 폴더(visol04) — 그 안의 data/, reviews/, manifests/ 사용"""
        return BASE_DIR

    @staticmethod
    def manifest_path(pj):
        """manifest 위치: 결과 기준 위치 아래 manifests/"""
        return os.path.join(pj["out_dir"], MANIFEST_DIR, MANIFEST_FILE)

    @staticmethod
    def is_output_dir(parent, name, root):
        """원본 탐색(os.walk) 중 건너뛸 이전 버전 결과 폴더인지 — root: images 또는 labels 폴더"""
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
        """[변경] 버튼용 — 결과 폴더를 고르게 한다. 데이터 폴더 안쪽은 거부, 취소하면 None"""
        src = os.path.abspath(pj["proj"])
        start = pj["out_dir"] or os.path.dirname(src)
        while True:
            d = filedialog.askdirectory(
                title=f"[{pj['name']}] 결과 폴더 선택 — 이 안에 data/, reviews/ 가 생성됩니다",
                initialdir=start)
            if not d:
                return None
            d = os.path.abspath(d)
            if self._is_inside(d, src):
                messagebox.showwarning("결과 폴더 오류",
                                       f"원본 데이터 폴더 안에는 만들 수 없습니다.\n"
                                       f"바깥의 위치를 선택하세요.\n\n원본: {src}")
                continue
            return d

    @staticmethod
    def out_subdirs(d):
        """결과 폴더 d 아래에 만들 폴더 목록"""
        locs = [RAW_DIR, ISSUES_DIR] + list(STAGE_DIRS.values())
        subs = [os.path.join(d, *loc, sub) for loc in locs for sub in (IMG_SUB, TXT_SUB)]
        subs.append(os.path.join(d, *CSV_DIR))
        subs.append(os.path.join(d, MANIFEST_DIR))
        return subs

    def prepare_out_dir(self, pj, d=None):
        """폴더를 열 때 호출 — 결과 폴더 구조를 채우고 원본을 raw 로 가져온다 (이미 있는 것은 그대로)"""
        d = d or os.path.abspath(self.default_out_dir(pj))
        pj["out_dir"] = d
        for sub in self.out_subdirs(d):
            os.makedirs(sub, exist_ok=True)
        with open(os.path.join(d, "data", "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(CLASS_NAMES) + "\n")   # 줄 번호 = 클래스 번호 (4번도 번호 맞춤용으로 유지)
        return self.import_raw(pj)

    def set_out_dir(self, pj, d):
        """결과 폴더 확정 → 폴더 생성 + 원본을 raw 로 가져오기 + 저장된 이미지 표시. 반환: 기존 저장본 수"""
        self.prepare_out_dir(pj, d)

        cur = self.cur_path()
        n_saved = 0
        for p, owner in self.proj_of.items():
            if owner is not pj:
                continue
            if not self.saved_stages(p):
                self.done.discard(p)
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

    def import_raw(self, pj):
        """아직 어느 단계에도 없는 원본 이미지를 data/raw 로 복사 (원본 라벨이 있으면 txt 도). 반환: 가져온 수"""
        targets = [p for p, owner in self.proj_of.items() if owner is pj and self.location(p) is None]
        for n, p in enumerate(targets, 1):
            paths = self.out_paths(p)
            img, txt = paths["raw"]
            self.copy_if_needed(p, img)
            raw = self.raw_label_path(p)
            if raw:
                os.makedirs(os.path.dirname(txt), exist_ok=True)
                with open(raw, encoding="utf-8") as fi, open(txt, "w", encoding="utf-8") as fo:
                    for line in fi:                       # 쉼표 csv → 공백 YOLO txt 로 통일
                        v = line.replace(",", " ").split()
                        if len(v) == 5:
                            fo.write(" ".join(v) + "\n")
            if n % 20 == 0 or n == len(targets):
                self.status(f"원본을 raw 로 가져오는 중... {n} / {len(targets)}")
                self.root.update_idletasks()
        return len(targets)

    def ensure_out_dir(self, pj, for_save=True):
        """결과 폴더가 없으면 기본 위치(<데이터 폴더>_labeled)에 만든다
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
                "결과 폴더에 현재 이미지의 저장본이 이미 있습니다.\n"
                "지금 화면의 박스로 저장할까요?\n\n(아니오: 저장을 취소하고 저장본을 불러옵니다)"):
            self.reload_current()
            return False
        messagebox.showinfo("결과 폴더 생성",
                            f"결과 폴더를 만들었습니다.\n\n{d}\n\n"
                            f"data/(raw, work/1차·2차, final, issues, csv), reviews/, manifests/ 를 준비했고\n"
                            f"원본 이미지를 data/raw 로 가져왔습니다.\n"
                            f"manifest: {self.manifest_path(pj)}")
        return True

    def change_out_dir(self):
        """[변경] 버튼 — 기본 결과 폴더 대신 다른 위치를 쓰고 싶을 때"""
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
            messagebox.showerror("결과 폴더 오류", str(e))
            return
        if self.saved_stages(p) and messagebox.askyesno(
                "저장본 불러오기",
                "새 위치에 현재 이미지의 저장본이 있습니다.\n"
                "저장본으로 화면을 바꿀까요?\n\n(아니오: 지금 화면 유지 — 저장하면 그 내용으로 기록)"):
            self.reload_current()
        self.apply_filter(keep=p)
        self.status(f"결과 폴더 변경: {d}   (기존 저장본 {n}장)")

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
        if pj["out_dir"]:
            self.outDirLabel.config(text=f"저장 위치: {pj['out_dir']}\n→ data/, reviews/, manifests/")
        else:
            self.outDirLabel.config(text=f"저장 위치: {self.default_out_dir(pj)}\n(첫 저장 때 생성)")

    # ── 경로 / 현재 위치 ──
    def out_paths(self, p):
        od = self.P(p)["out_dir"]
        rel = self.rel_of(p)                          # 'train/a.jpg'
        stem = os.path.splitext(rel)[0]

        def pair(loc):                                # (이미지 경로, YOLO txt 경로)
            return (os.path.join(od, *loc, IMG_SUB, rel),
                    os.path.join(od, *loc, TXT_SUB, stem + ".txt"))

        return {"raw": pair(RAW_DIR),
                "stage": {st: pair(loc) for st, loc in STAGE_DIRS.items()},
                "issues": pair(ISSUES_DIR),
                "issue_note": os.path.join(od, *ISSUES_DIR, TXT_SUB, stem + "_issue.txt"),
                "csv": os.path.join(od, *CSV_DIR, stem + ".csv")}

    def location(self, p):
        """이 이미지가 지금 있는 단계: final / review / 2차 / 1차 / raw / None(아직 없음)"""
        if not self.P(p)["out_dir"]:
            return None
        paths = self.out_paths(p)
        for st in LOCATION_ORDER:
            if os.path.exists(paths["stage"][st][0]):
                return st
        if os.path.exists(paths["raw"][0]):
            return "raw"
        return None

    def latest_stage(self, p):
        """현재 검수 단계 (raw 이거나 아직 없으면 빈 문자열)"""
        loc = self.location(p)
        return loc if loc in STAGE_DIRS else ""

    def recorded_stage(self, p):
        """이력 csv 에 마지막으로 기록된 단계 (기록이 없으면 빈 문자열)"""
        if not self.P(p)["out_dir"]:
            return ""
        path = self.out_paths(p)["csv"]
        if not os.path.exists(path):
            return ""
        last = ""
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                last = row.get("stage", "") or ""
        return last

    def is_in_progress(self, p):
        """작업 중(저장 전) — 지금 있는 단계 폴더와 마지막 기록 단계가 다르면 작업 중"""
        loc = self.latest_stage(p)
        return bool(loc) and self.recorded_stage(p) != loc

    def saved_stages(self, p):
        """저장된 단계 목록 — 현재 단계가 기록(csv)과 일치할 때만 (작업 중이면 빈 목록)"""
        st = self.latest_stage(p)
        return [st] if st and not self.is_in_progress(p) else []

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
        """라벨 읽기 — YOLO txt(공백) / 쉼표 5칸 csv"""
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

    @staticmethod
    def last_issue_note(csv_path):
        """이력 csv 의 마지막 저장분에 기록된 이슈 노트"""
        if not os.path.exists(csv_path):
            return ""
        last = ""
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                last = row.get("issue_note", "") or ""
        return last

    def load_saved(self, p):
        """→ (박스 리스트, 이슈 노트). 현재 단계 폴더의 txt → raw txt → 원본 라벨 순"""
        if not self.P(p)["out_dir"]:
            raw = self.raw_label_path(p)
            return (self.read_label_file(raw) if raw else []), ""
        paths = self.out_paths(p)
        loc = self.location(p)
        if loc in STAGE_DIRS:
            txt = paths["stage"][loc][1]
            self.review_status.setdefault(p, loc)
        elif loc == "raw":
            txt = paths["raw"][1]
        else:
            txt = self.raw_label_path(p)
        boxes = self.read_label_file(txt) if txt and os.path.exists(txt) else []
        return boxes, self.last_issue_note(paths["csv"])

    # ── 쓰기 도우미 ──
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

    def _meta(self, stage, prev):
        w = self.workerInfo.get_data()
        r = self.reviewerInfo.get_data()
        return {"stage": stage, "from": prev,
                "worker_name": w["이름"], "worker_id": w["ID"],
                "reviewer_name": r["이름"], "reviewer_id": r["ID"],
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    @staticmethod
    def _append_rows(path, header, rows):
        """csv 에 행 추가 (파일이 없으면 헤더부터). 기존 줄은 건드리지 않음"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
            wr = csv.writer(f)
            if new:
                wr.writerow(header)
            wr.writerows(rows)

    def _append_history(self, path, p, boxes, meta, note):
        """이미지별 이력 csv — 박스 1개당 1행, 박스가 없으면 '객체 없음' 1행"""
        who = [meta["worker_name"], meta["worker_id"], meta["reviewer_name"], meta["reviewer_id"]]
        head = [self.rel_of(p), meta["stage"], meta["from"]]
        rows = []
        for b in self._label_boxes(boxes):
            xc, yc, w, h = self.box_to_yolo(b)
            rows.append(head + [b["cls"], CLASS_NAMES[b["cls"]],
                                f"{xc:.6f}", f"{yc:.6f}", f"{w:.6f}", f"{h:.6f}"]
                        + who + [note, meta["saved_at"]])
        if not rows:
            rows.append(head + ["", "객체 없음", "", "", "", ""] + who + [note, meta["saved_at"]])
        self._append_rows(path, CSV_HEADER, rows)

    def _append_manifest(self, p, boxes, meta, note):
        """전체 진행 대장 — 이미지 1장당 1행 추가"""
        pj = self.P(p)
        parts = self.rel_of(p).split(os.sep)
        split = parts[0] if len(parts) > 1 else ""
        scene = parts[1] if len(parts) > 2 else ""
        row = [os.path.basename(p), pj["name"], split, scene, meta["stage"], meta["from"],
               len(self._label_boxes(boxes)), meta["worker_name"], meta["worker_id"],
               meta["reviewer_name"], meta["reviewer_id"], "Y" if note else "", meta["saved_at"]]
        self._append_rows(self.manifest_path(pj), MANIFEST_HEADER, [row])

    def _write_yolo(self, path, boxes):
        """YOLO 학습용 txt — 'cls xc yc w h' (공백 구분)"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for b in self._label_boxes(boxes):
                f.write("{} {:.6f} {:.6f} {:.6f} {:.6f}\n".format(b["cls"], *self.box_to_yolo(b)))

    def _write_preview(self, path, boxes):
        """현재 이미지에 박스와 '번호: 클래스 이름'을 그려 넣은 확인용 이미지 저장"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = self.img.copy()                       # 화면용 원본(RGB) 사본에 그림 — 원본 파일은 그대로
        draw = ImageDraw.Draw(im)
        short = min(im.size)
        lw = max(2, round(short / 300))
        font, korean = preview_font(max(14, round(short / 35)))
        pad = max(2, lw)
        for b in self._label_boxes(boxes):
            color = COLORS[b["cls"] % len(COLORS)]
            x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
            draw.rectangle((x1, y1, x2, y2), outline=color, width=lw)
            text = f"{b['cls']}: {CLASS_NAMES[b['cls']]}" if korean else str(b["cls"])
            l, t, r, btm = draw.textbbox((0, 0), text, font=font)
            tw, th = r - l, btm - t
            ty = y1 - th - 2 * pad                 # 기본: 박스 위쪽에 이름표
            if ty < 0:                             # 위에 자리가 없으면 박스 아래쪽에
                ty = min(y2, im.size[1] - th - 2 * pad)
            draw.rectangle((x1, ty, x1 + tw + 2 * pad, ty + th + 2 * pad), fill=color)
            draw.text((x1 + pad - l, ty + pad - t), text, fill="white", font=font)
        im.save(path)

    def _append_issue(self, p, paths, boxes, meta, note):
        """이슈: 이미지·라벨 사본을 issues 에 두고, 이슈 기록 txt 에는 내용을 덧붙이기만 함"""
        img, txt = paths["issues"]
        self.copy_if_needed(p, img)
        self._write_yolo(txt, boxes)
        with open(paths["issue_note"], "a", encoding="utf-8") as f:
            f.write(f"===== {meta['saved_at']}  단계: {meta['stage']}  (이전: {meta['from']})\n")
            f.write(f"작성자: {self.workerVar.get().strip()}\n")
            f.write(f"작업자: {meta['worker_name']} ({meta['worker_id']})\n")
            f.write(f"검수자: {meta['reviewer_name']} ({meta['reviewer_id']})\n")
            f.write(f"이미지: {self.disp(p)}\n")
            f.write("[이슈 내용]\n" + note + "\n\n")

    # ── 작업 중 자동 저장 (기록 없이 work 의 txt 만 갱신) ──
    def autosave_work(self):
        """편집할 때마다 호출 — raw(또는 미반입) 이미지는 work/1차 로 옮기고 txt 에 현재 박스를 바로 씀.
           review·final 에 있는 이미지는 승인 기록을 건드리지 않도록 자동 저장하지 않음([저장] 때 반영)"""
        p = self.cur_path()
        if not p or not self.img or not self.P(p)["out_dir"]:
            return
        loc = self.location(p)
        if loc in ("review", "final"):
            return
        paths = self.out_paths(p)
        try:
            if loc in (None, "raw"):                 # 작업 시작 → raw 에서 work/1차 로 이동
                img, txt = paths["stage"][WORK_START]
                self.copy_if_needed(p, img)
                self.remove_if_exists(paths["raw"][0])
                self.remove_if_exists(paths["raw"][1])
                loc = WORK_START
                self.status(f"작업 시작: {self.disp(p)} → work/{WORK_START} (편집 내용 자동 저장)")
            self._write_yolo(paths["stage"][loc][1], self.cur_boxes())
        except OSError as e:
            self.status(f"자동 저장 실패: {e}")

    # ── 저장 ──
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
            if not self.ensure_out_dir(self.P(p)):      # 결과 폴더가 없으면 여기서 생성
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

            paths = self.out_paths(p)
            prev = self.recorded_stage(p) or "raw"      # 작업 중(work/1차)이어도 기록상 이전 단계
            meta = self._meta(stage, prev)
            note = self.notes.get(p, "").strip()

            # 3) 기록 — 이미지별 이력 csv 에 추가 (1차 검수자 기록 등 이전 줄은 그대로)
            self._append_history(paths["csv"], p, boxes, meta, note)

            # 4) 이동 — 이전 위치(raw 포함)의 img·txt 를 치우고 이번 단계 폴더에 둠
            for st, (img, txt) in paths["stage"].items():
                if st != stage:
                    self.remove_if_exists(img)
                    self.remove_if_exists(txt)
            self.remove_if_exists(paths["raw"][0])
            self.remove_if_exists(paths["raw"][1])
            img, txt = paths["stage"][stage]
            if stage == "review":
                self._write_preview(img, boxes)          # 검수용: 박스를 그려 넣은 이미지
            else:
                self.copy_if_needed(p, img)              # 그 외: 원본 그대로 (학습용)
            self._write_yolo(txt, boxes)

            # 5) 이슈 노트가 있으면 issues 에 추가
            if note:
                self._append_issue(p, paths, boxes, meta, note)

            # 6) 전체 진행 대장에 추가
            self._append_manifest(p, boxes, meta, note)
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
        self.status(f"저장 완료 [{prev} → {stage}]: {self.disp(p)}")
        return True

    def save_and_next(self):
        if not self.save():
            return
        self.next_image("마지막 이미지까지 저장했습니다.")
