"""프로젝트 내 모든 경로를 PROJECT_ROOT 기준으로 정의 — 하드코딩 금지

사용 예:
    from src.common.paths import DATA_DIR, MANIFEST_DIR, REPORTS_DIR
    from src.common.paths import result_dir, split_csv

경로 기준:
    이 파일은 src/common/paths.py → parents[2] 가 PROJECT_ROOT (visol04/)
"""
from pathlib import Path

# ── 프로젝트 루트 ─────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# ── 최상위 디렉토리 ───────────────────────────────────────────────────────────
DATA_DIR     = PROJECT_ROOT / "data"
MANIFEST_DIR = PROJECT_ROOT / "manifests"
REPORTS_DIR  = PROJECT_ROOT / "reports"
CONFIGS_DIR  = PROJECT_ROOT / "configs"
RUNS_DIR     = PROJECT_ROOT / "runs"
TOOLS_DIR    = PROJECT_ROOT / "tools"

# ── data/ 하위 ───────────────────────────────────────────────────────────────
RAW_DIR      = DATA_DIR / "raw"
FINAL_DIR    = DATA_DIR / "final"

def result_dir(dataset_key: str) -> Path:
    """dataset1 → data/dataset1_result"""
    return DATA_DIR / f"{dataset_key}_result"

# ── manifests/ 하위 ──────────────────────────────────────────────────────────
MANIFEST_CSV         = MANIFEST_DIR / "dataset_manifest.csv"
SPLIT_MANIFEST_CSV   = MANIFEST_DIR / "split_manifest.csv"
TRAIN_CSV            = MANIFEST_DIR / "train.csv"
VAL_CSV              = MANIFEST_DIR / "val.csv"
TEST_CSV             = MANIFEST_DIR / "test.csv"

def split_csv(name: str) -> Path:
    """split_csv('train') → manifests/train.csv"""
    return MANIFEST_DIR / f"{name}.csv"

# ── reports/ 하위 ────────────────────────────────────────────────────────────
BASELINE_METRICS_CSV = REPORTS_DIR / "baseline_metrics.csv"
FAILURE_CSV          = REPORTS_DIR / "failure_candidates.csv"

def reports_log_dir(tool_name: str) -> Path:
    """reports_log_dir('build_split') → reports/logs/build_split/"""
    return REPORTS_DIR / "logs" / tool_name

# ── runs/ 하위 ───────────────────────────────────────────────────────────────
BASELINE_DIR         = RUNS_DIR / "baseline_v1"
BASELINE_WEIGHT      = BASELINE_DIR / "weights" / "baseline_best.pt"
BASELINE_ARGS_YAML   = BASELINE_DIR / "args.yaml"
BASELINE_RESULTS_CSV = BASELINE_DIR / "results.csv"

# ── configs/ ─────────────────────────────────────────────────────────────────
DATASET_YAML       = CONFIGS_DIR / "dataset.yaml"
SMOKE_DATASET_YAML = CONFIGS_DIR / "smoke_dataset.yaml"
