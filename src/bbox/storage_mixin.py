"""저장 / 불러오기 — 단계 폴더 이동 + 기록(csv·manifest)은 추가만
   visol04/
   ├── data/                      (원본은 고른 경로의 images·labels 에서 읽기만)
   │   ├── DONE/                  작업자가 보낸 결과
   │   │   ├── pass/     img, txt   문제없음
   │   │   ├── edited/   img, txt   추가·수정함
   │   │   └── review/   img, txt   검수자 판단 요청 (+ preview/ 확인용 이미지)
   │   ├── view/     img, txt     검수자 → 작업자 재작업 요청
   │   ├── final/    img, txt     검수자 최종 승인 → 학습용
   │   ├── working/  txt          편집했지만 [저장] 전인 박스 (임시)
   │   ├── issues/   img, txt     이슈 노트가 있는 이미지 사본 + 이슈 기록 (추가만)
   │   ├── csv/                   이미지별 이력 csv (추가만)
   │   └── classes.txt
   └── manifests/dataset_manifest.csv   전체 진행 대장 (추가만)

   - 아직 저장 안 한 이미지는 원본 경로에서 바로 읽음 (복사하지 않음)
   - 편집할 때마다 박스를 working/txt 에 임시 저장 (이미지는 원래 위치에 그대로)
     → 꺼져도 다시 켜면 그 박스부터 이어서 작업. 단계 보기 'working' 에 표시
   - [저장] → 이력 csv·manifest 에 기록 추가 + 검수 상태(단계) 폴더로 이동 + 임시 저장 삭제
     누가 어디로 보낼 수 있는지는 src/bbox/workflow.py
   - 이슈 노트: 이미지를 열면 지금까지의 이슈 기록(<이미지>_issue.txt)에서 [이슈 내용] 부분만 칸에 불러옴.
     그 뒤에 덧붙여 적은 글자만 이번 저장의 이슈로 기록 (공백·줄바꿈만 있으면 이슈 아님)
     누가·언제·어느 단계였는지는 기록 파일에 머리줄과 함께 그대로 남음
   - 기록은 기존 줄을 고치거나 지우지 않고 덧붙이기만 한다. 원본 폴더는 읽기만 한다."""
import csv
import os
import shutil
from datetime import datetime
from functools import lru_cache
from tkinter import filedialog, messagebox

from PIL import ImageDraw, ImageFont

from src.config import (CLASS_NAMES, ISSUE_ID, DONE_LIST_COLOR, COLORS, INFO_FIELDS,
                        BASE_DIR, IMG_SUB, TXT_SUB, PREVIEW_SUB, WORKING_DIR, ISSUES_DIR,
                        CSV_DIR, STAGE_DIRS, PREVIEW_STAGES, MANIFEST_DIR, MANIFEST_FILE,
                        DONE_SUFFIX, DEFAULT_DONE, LEGACY_OUT, PREVIEW_FONTS, ROLE_NAMES, SOURCE_LABEL)
from src.validation.rules import class_name, describe_locked, apply_locked, locked_boxes
from src.bbox.workflow import Flow, read_events, WORKER, REVIEWER

# 작업자·검수자 열 — config.INFO_FIELDS 로 만듦 (worker_name, worker_id, reviewer_name, reviewer_id)
#   저장한 사람의 역할 열만 채움
WHO_COLS = [f"{role}_{key}" for role in (WORKER, REVIEWER) for _, key in INFO_FIELDS]
# 이미지별 이력 csv — 저장할 때마다 박스 1개당 1행씩 아래에 추가
#   review_action : 검수자 저장 때 박스별 처리 — 유지 / 클래스 변경(a→b) / 크기·위치 수정 / 추가 / 삭제
#                   (고치기 전 좌표는 바로 앞 저장 기록의 줄에 남아 있음)
CSV_HEADER = (["image", "stage", "from", "class_id", "class_name",
               "x_center", "y_center", "width", "height", "review_action"]
              + WHO_COLS + ["issue_note", "saved_at"])
# 전체 진행 대장 — 저장할 때마다 이미지 1장당 1행씩 아래에 추가
MANIFEST_HEADER = (["file_name", "source_dataset", "original_split", "scene_type",
                    "stage", "from", "boxes"] + WHO_COLS + ["issue", "saved_at"])
# 현재 위치를 찾는 순서
LOCATION_ORDER = ("final", "view", "review", "edited", "pass")


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
        """기본 결과 기준 위치: 프로그램 폴더(visol04) — 그 안의 data/, manifests/ 사용"""
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
                title=f"[{pj['name']}] 결과 폴더 선택 — 이 안에 data/, manifests/ 가 생성됩니다",
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
        locs = [ISSUES_DIR] + list(STAGE_DIRS.values())
        subs = [os.path.join(d, *loc, sub) for loc in locs for sub in (IMG_SUB, TXT_SUB)]
        subs += [os.path.join(d, *STAGE_DIRS[st], PREVIEW_SUB) for st in PREVIEW_STAGES]
        subs.append(os.path.join(d, *WORKING_DIR, TXT_SUB))
        subs.append(os.path.join(d, *CSV_DIR))
        subs.append(os.path.join(d, MANIFEST_DIR))
        return subs

    def prepare_out_dir(self, pj, d=None):
        """폴더를 열 때 호출 — 결과 폴더 구조만 채운다 (원본은 복사하지 않음)"""
        d = d or os.path.abspath(self.default_out_dir(pj))
        pj["out_dir"] = d
        for sub in self.out_subdirs(d):
            os.makedirs(sub, exist_ok=True)
            keep = os.path.join(sub, ".gitkeep")      # Git 에 빈 폴더 구조를 올리기 위한 표시 파일
            if not os.path.exists(keep):
                open(keep, "w").close()
        with open(os.path.join(d, "data", "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(CLASS_NAMES) + "\n")   # 줄 번호 = 클래스 번호 (4번도 번호 맞춤용으로 유지)

    def set_out_dir(self, pj, d):
        """결과 폴더 확정 → 폴더 생성 + 저장된 이미지 표시. 반환: 기존 저장본 수"""
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

        self.refresh_image_list()
        if 0 <= self.idx < len(self.images):
            self.imageList.selection_set(self.idx)
        self.update_progress()
        self.update_stage_counts()
        self.update_out_dir_label()
        return n_saved

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
                            f"data/(work/pass·edited·review, view, final, working, issues, csv), manifests/ 를 준비했습니다.\n"
                            f"원본은 복사하지 않고 읽기만 합니다.\n"
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
        self.refresh_workflow()
        self.redraw_boxes()
        self.refresh_info()

    def update_out_dir_label(self):
        p = self.cur_path()
        if not p:
            self.outDirLabel.config(text="저장 위치: -")
            return
        pj = self.P(p)
        if pj["out_dir"]:
            self.outDirLabel.config(text=f"저장 위치: {pj['out_dir']}\n→ data/, manifests/")
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

        return {"stage": {st: pair(loc) for st, loc in STAGE_DIRS.items()},
                "preview": {st: os.path.join(od, *STAGE_DIRS[st], PREVIEW_SUB, rel) for st in PREVIEW_STAGES},
                "working": os.path.join(od, *WORKING_DIR, TXT_SUB, stem + ".txt"),
                "issues": pair(ISSUES_DIR),
                "issue_note": os.path.join(od, *ISSUES_DIR, TXT_SUB, stem + "_issue.txt"),
                "csv": os.path.join(od, *CSV_DIR, stem + ".csv")}

    def location(self, p):
        """이 이미지가 지금 있는 폴더: final / view / review / edited / pass / None(아직 저장 안 함 = 원본)"""
        if not self.P(p)["out_dir"]:
            return None
        paths = self.out_paths(p)
        for st in LOCATION_ORDER:
            if os.path.exists(paths["stage"][st][0]):
                return st
        return None

    def latest_stage(self, p):
        """현재 단계 (아직 저장 안 했으면 빈 문자열)"""
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
        """작업 중 — 편집했지만 아직 [저장] 안 함 (working/txt 에 임시 저장본이 있음)"""
        return bool(self.P(p)["out_dir"]) and os.path.exists(self.out_paths(p)["working"])

    def has_issue(self, p):
        """이슈 기록이 있는지 (단계 보기 '이슈') — 한 번이라도 이슈 노트를 적어 저장한 이미지"""
        return bool(self.P(p)["out_dir"]) and os.path.exists(self.out_paths(p)["issue_note"])

    def saved_stages(self, p):
        """저장된 단계 목록 (아직 저장 전이면 빈 목록)"""
        st = self.latest_stage(p)
        return [st] if st else []

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
    def issue_log(path):
        """이슈 기록 파일 → 각 기록의 [이슈 내용] 부분만 차례대로 이은 글 (없으면 빈 문자열)
           기록 형식: '===== 시각 …' 머리줄 … '[이슈 내용]' 다음 줄부터 다음 '=====' 전까지가 내용"""
        if not os.path.exists(path):
            return ""
        contents, cur = [], None
        with open(path, encoding="utf-8") as f:
            for line in f.read().splitlines():
                if line.startswith("===== "):          # 새 기록 시작
                    if cur is not None:
                        contents.append("\n".join(cur).strip())
                    cur = None
                elif line.strip() == "[이슈 내용]":
                    cur = []
                elif cur is not None:
                    cur.append(line)
        if cur is not None:
            contents.append("\n".join(cur).strip())
        text = "\n".join(c for c in contents if c)
        return text + "\n" if text else ""

    def new_issue_text(self, p):
        """이슈 노트 칸에서 이번에 새로 적은 부분 — 불러온 기록 뒤에 덧붙인 글자
           (불러온 기록을 고쳤으면 칸 전체를 새 내용으로 봄). 공백·줄바꿈만 있으면 빈 문자열"""
        text = self.notes.get(p, "")
        base = self.note_base.get(p, "")
        if base and text.startswith(base):
            text = text[len(base):]
        return text.strip()

    def _saved_label(self, p):
        """저장본 라벨 경로 — 현재 단계 폴더, 아직 저장 안 했으면 원본 labels"""
        loc = self.location(p)
        if loc in STAGE_DIRS:
            return self.out_paths(p)["stage"][loc][1]
        return self.raw_label_path(p)

    def load_saved(self, p):
        """→ (박스 리스트, 이슈 노트)
           박스: 임시 저장본(working)이 있으면 그것, 없으면 저장본
           검수자 수정 비교 기준(baseline)은 항상 '저장본' 기준"""
        if not self.P(p)["out_dir"]:
            raw = self.raw_label_path(p)
            boxes = self.read_label_file(raw) if raw else []
            self.mark_baseline(p, boxes)
            self.note_base[p] = ""
            return boxes, ""
        paths = self.out_paths(p)
        saved = self._saved_label(p)
        base = self.read_label_file(saved) if saved and os.path.exists(saved) else []
        self.mark_baseline(p, base)
        if os.path.exists(paths["working"]):
            boxes = self.read_label_file(paths["working"])
            self._tag_like_baseline(p, boxes)
        else:
            boxes = base
        log = self.issue_log(paths["issue_note"])     # 지금까지의 이슈 기록 → 이슈 노트 칸에 그대로
        self.note_base[p] = log
        return boxes, log

    # ── 검수자 수정 내용 비교용 기준 ──
    def _yolo6(self, b):
        return tuple(round(v, 6) for v in self.box_to_yolo(b))

    def mark_baseline(self, p, boxes):
        """저장본 박스를 기준으로 기억 — 박스마다 번호(oid)를 붙여 둠"""
        base = {}
        for i, b in enumerate(self._label_boxes(boxes)):
            b["oid"] = i
            base[i] = (b["cls"], self._yolo6(b))
        self.baseline[p] = base

    def _tag_like_baseline(self, p, boxes):
        """임시 저장본에서 불러온 박스 — 기준과 좌표가 같은 박스에 같은 번호를 붙임
           (좌표가 바뀐 박스는 '추가', 사라진 기준 박스는 '삭제'로 기록됨)"""
        free = {xy: oid for oid, (_, xy) in self.baseline.get(p, {}).items()}
        for b in self._label_boxes(boxes):
            oid = free.pop(self._yolo6(b), None)
            if oid is not None:
                b["oid"] = oid

    def review_changes(self, p, boxes):
        """기준과 비교 → ({id(박스): 처리}, [(삭제된 박스의 클래스, 좌표)])"""
        base = self.baseline.get(p, {})
        acts, alive = {}, set()
        for b in self._label_boxes(boxes):
            oid = b.get("oid")
            if oid not in base:
                acts[id(b)] = "추가"
                continue
            alive.add(oid)
            ocls, oxy = base[oid]
            if b["cls"] != ocls:
                acts[id(b)] = f"클래스 변경({ocls}→{b['cls']})"
            elif self._yolo6(b) != oxy:
                acts[id(b)] = "크기·위치 수정"
            else:
                acts[id(b)] = "유지"
        deleted = [base[o] for o in sorted(base) if o not in alive]
        return acts, deleted

    def boxes_changed(self, p, boxes):
        """저장본과 비교해 바뀐 박스가 있는지 (pass 로 저장할 때 확인용)"""
        acts, deleted = self.review_changes(p, boxes)
        return bool(deleted) or any(a != "유지" for a in acts.values())

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

    def _meta(self, stage, prev, person):
        """이번 기록의 단계·시각 + 저장한 사람 (그 사람 역할의 열만 채움)"""
        meta = {"stage": stage, "from": prev,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        for role in (WORKER, REVIEWER):
            for _, key in INFO_FIELDS:
                meta[f"{role}_{key}"] = person.get(key, "") if person["role"] == role else ""
        return meta

    @staticmethod
    def _who_text(meta, role):
        """이슈 기록용 — 예) '이동윤 (2020219054)' : 첫 항목 + 나머지는 괄호"""
        vals = [meta.get(f"{role}_{key}", "") for _, key in INFO_FIELDS]
        return vals[0] + (f" ({', '.join(vals[1:])})" if len(vals) > 1 else "")

    def _append_rows(self, path, header, rows):
        """csv 에 행 추가 (파일이 없으면 헤더부터). 기존 줄은 건드리지 않음
           rows: dict 목록. 이미 있는 파일의 헤더가 다르면(입력 항목을 바꾼 경우 등)
           기존 헤더 순서에 맞춰 쓰고, 기존 헤더에 없는 열은 쓰지 않음 (기존 기록을 고치지 않기 위해)"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        cols = header
        if not new:
            with open(path, encoding="utf-8-sig", newline="") as f:
                cols = next(csv.reader(f), None) or header
            dropped = [c for c in header if c not in cols]
            if dropped:                      # 저장 완료 메시지 뒤에 붙여서 보여줌
                self._save_warnings.append(f"{os.path.basename(path)} 기존 열에 없는 항목 미기록: "
                                           f"{', '.join(dropped)}")
        with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
            wr = csv.writer(f)
            if new:
                wr.writerow(cols)
            wr.writerows([[row.get(c, "") for c in cols] for row in rows])

    def _append_history(self, path, p, boxes, meta, note, review=None):
        """이미지별 이력 csv — 박스 1개당 1행, 박스가 없으면 '객체 없음' 1행
           review=(처리, 삭제 목록): 검수자 저장이면 박스별 review_action + 삭제된 박스도 1행씩"""
        base = dict(meta, image=self.rel_of(p), issue_note=note)
        acts, deleted = review if review else ({}, [])

        def row(cls, xywh, act):
            xc, yc, w, h = xywh
            return dict(base, class_id=cls, class_name=class_name(cls),
                        x_center=f"{xc:.6f}", y_center=f"{yc:.6f}",
                        width=f"{w:.6f}", height=f"{h:.6f}", review_action=act)

        rows = [row(b["cls"], self.box_to_yolo(b), acts.get(id(b), "")) for b in self._label_boxes(boxes)]
        if not rows:
            rows.append(dict(base, class_name="객체 없음"))
        rows += [row(cls, xywh, "삭제") for cls, xywh in deleted]
        self._append_rows(path, CSV_HEADER, rows)

    def _append_manifest(self, p, boxes, meta, note):
        """전체 진행 대장 — 이미지 1장당 1행 추가"""
        pj = self.P(p)
        parts = self.rel_of(p).split(os.sep)
        row = dict(meta, file_name=os.path.basename(p), source_dataset=pj["name"],
                   original_split=parts[0] if len(parts) > 1 else "",
                   scene_type=parts[1] if len(parts) > 2 else "",
                   boxes=len(self._label_boxes(boxes)), issue="Y" if note else "")
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
            text = f"{b['cls']}: {class_name(b['cls'])}" if korean else str(b["cls"])
            l, t, r, btm = draw.textbbox((0, 0), text, font=font)
            tw, th = r - l, btm - t
            ty = y1 - th - 2 * pad                 # 기본: 박스 위쪽에 이름표
            if ty < 0:                             # 위에 자리가 없으면 박스 아래쪽에
                ty = min(y2, im.size[1] - th - 2 * pad)
            draw.rectangle((x1, ty, x1 + tw + 2 * pad, ty + th + 2 * pad), fill=color)
            draw.text((x1 + pad - l, ty + pad - t), text, fill="white", font=font)
        im.save(path)

    def _append_issue(self, p, paths, boxes, meta, note, person):
        """이슈: 이미지·라벨 사본을 issues 에 두고, 이슈 기록 txt 에는 내용을 덧붙이기만 함"""
        img, txt = paths["issues"]
        self.copy_if_needed(p, img)
        self._write_yolo(txt, boxes)
        with open(paths["issue_note"], "a", encoding="utf-8") as f:
            f.write(f"===== {meta['saved_at']}  {meta['from']} → {meta['stage']}\n")
            f.write(f"{ROLE_NAMES[person['role']]}: {self._who_text(meta, person['role'])}\n")
            f.write(f"이미지: {self.disp(p)}\n")
            f.write("[이슈 내용]\n" + note + "\n\n")

    # ── 작업 중 임시 저장 (기록 없이 working/txt 만 갱신) ──
    def autosave_work(self):
        """편집할 때마다 호출 — 현재 박스를 working/txt 에 바로 씀. 이미지는 원래 폴더에 그대로
           (저장 전에 꺼져도 다시 켜면 이 박스부터 이어서 작업)"""
        p = self.cur_path()
        if not p or not self.img or not self.P(p)["out_dir"]:
            return
        try:
            first = not self.is_in_progress(p)
            self._write_yolo(self.out_paths(p)["working"], self.cur_boxes())
            if first:
                self.status(f"작업 중: {self.disp(p)} (편집 내용 임시 저장 — [저장] 전)")
                self.update_stage_counts()
        except OSError as e:
            self.status(f"임시 저장 실패: {e}")

    # ── 저장 ──
    def current_flow(self, p):
        """이 이미지의 단계 흐름 (현재 위치 + 이력 csv)"""
        if not self.P(p)["out_dir"]:
            return Flow("", [])
        return Flow(self.latest_stage(p), read_events(self.out_paths(p)["csv"]))

    def _ready_boxes(self):
        """저장 직전 박스 정리 — 지정 불가 클래스 박스가 있으면 확인 후 규칙대로 처리. 취소하면 None"""
        boxes = self.cur_boxes()
        if locked_boxes(boxes):
            lines = "\n".join("  · " + s for s in describe_locked(boxes))
            if not messagebox.askyesno(
                    "지정 불가 클래스",
                    f"지정할 수 없는 클래스 박스가 있습니다.\n\n{lines}\n\n"
                    f"위와 같이 처리하고 저장할까요?\n"
                    f"(아니오: 저장 취소 — 박스를 선택해 직접 다른 클래스로 바꿀 수 있습니다)"):
                return None
            apply_locked(boxes)
        return boxes

    def save(self):
        p = self.cur_path()
        if not p or not self.img:
            return False
        self.discard_pending()
        self.save_current_note()

        # 1) 누가 / 어디로 — 규칙은 workflow.py
        person = self.current_person()
        flow = self.current_flow(p)
        ok, why = flow.can_act(person)
        if not ok:
            messagebox.showwarning("저장 불가", why)
            return False
        stage = self.reviewPanel.get_state()
        if stage not in flow.targets(person):
            messagebox.showwarning("검수 상태", f"저장할 수 있는 단계: {' / '.join(flow.targets(person))}\n"
                                             f"검수 상태에서 선택한 뒤 저장하세요.")
            return False
        try:
            if not self.ensure_out_dir(self.P(p)):      # 결과 폴더가 없으면 여기서 생성
                return False
        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

        # 2) 지정 불가 클래스 박스 처리 (규칙: config.CLASSES — 대체 번호가 있으면 변경, 없으면 삭제)
        boxes = self._ready_boxes()
        if boxes is None:
            return False

        # 3) pass 인데 박스를 고쳤으면 확인 (pass = 딥러닝 결과 그대로, 고쳤으면 edited)
        if stage == "pass" and self.boxes_changed(p, boxes):
            ans = messagebox.askyesnocancel(
                "검수 상태 확인",
                "박스를 추가·수정했는데 'pass'로 저장하려고 합니다.\n\n"
                "[예] edited 로 저장\n[아니요] 그대로 pass 로 저장\n[취소] 돌아가기")
            if ans is None:
                return False
            if ans:
                stage = "edited"
                self.reviewPanel.set_state(stage)

        review = self.review_changes(p, boxes) if flow.records_review(person) else None
        return self._commit(p, stage, person, boxes, review)

    def _commit(self, p, stage, person, boxes, review=None):
        """기록 추가 + 단계 폴더 이동"""
        try:
            self._save_warnings = []                     # 저장 중 생긴 경고 (마지막에 상태 표시줄로)
            paths = self.out_paths(p)
            prev = self.latest_stage(p) or SOURCE_LABEL
            meta = self._meta(stage, prev, person)
            note = self.new_issue_text(p)                # 이번에 새로 적은 이슈 (없으면 '')

            # 1) 기록 — 이미지별 이력 csv 에 추가 (이전 줄은 그대로)
            self._append_history(paths["csv"], p, boxes, meta, note, review)

            # 2) 이동 — 다른 단계의 img·txt·preview 를 치우고 이번 단계 폴더에 둠 (이미지는 원본에서 복사)
            for st, (img, txt) in paths["stage"].items():
                if st != stage:
                    self.remove_if_exists(img)
                    self.remove_if_exists(txt)
            for st, prv in paths["preview"].items():
                if st != stage:
                    self.remove_if_exists(prv)
            img, txt = paths["stage"][stage]
            self.copy_if_needed(p, img)                  # 원본 이미지 그대로 (학습용)
            self._write_yolo(txt, boxes)
            if stage in paths["preview"]:
                self._write_preview(paths["preview"][stage], boxes)   # 확인용: 박스를 그려 넣은 이미지
            self.remove_if_exists(paths["working"])      # 임시 저장본 정리

            # 3) 이슈 노트가 있으면 issues 에 추가
            if note:
                self._append_issue(p, paths, boxes, meta, note, person)

            # 4) 전체 진행 대장에 추가
            self._append_manifest(p, boxes, meta, note)
        except OSError as e:
            messagebox.showerror("저장 오류", str(e))
            return False

        # 저장 = 사람이 확인한 라벨 → 자동 BBox 표시 해제, 다음 비교 기준 갱신
        for b in self.cur_boxes():
            b["auto"] = False
        self.auto_pred.pop(p, None)
        self.mark_baseline(p, self.cur_boxes())
        self.redraw_boxes()
        self.refresh_info()
        # 이슈 노트 칸 = 방금 덧붙인 것까지 포함한 이슈 기록 전체
        self.notes[p] = self.note_base[p] = self.issue_log(paths["issue_note"])
        self.issueNote.delete("1.0", "end")
        self.issueNote.insert("1.0", self.notes[p])
        self.issueNote.see("end")

        self.done.add(p)
        self.imageList.itemconfig(self.idx, fg=DONE_LIST_COLOR)
        self.update_stage_counts()
        self.refresh_workflow()
        msg = f"저장 완료 [{prev} → {stage}] {ROLE_NAMES[person['role']]} {person['name']}: {self.disp(p)}"
        if self._save_warnings:
            msg += "   ⚠ " + " / ".join(self._save_warnings)
        self.status(msg)
        return True

    def save_and_next(self):
        if not self.save():
            return
        self.next_image("마지막 이미지까지 저장했습니다.")
