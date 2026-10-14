"""Split Freeze 검증 — manifests/ 내 분할 파일의 SHA-256 동결 상태 확인

Split Freeze 란?
    split_manifest.csv 가 이미 존재할 때, 새 분할 결과의 파일 해시가
    기존 파일과 일치해야 한다는 규칙 (progress_20261014.md § 11.5).

    Baseline 확정 기준 (progress_20261014.md § 3):
        split_manifest.csv  @ 1b074fa
        train.csv   sha256 앞 12자리: 8b9e6b7c4644
        val.csv     sha256 앞 12자리: eabbaa9b8f3a

제공 함수:
    freeze_status(path)   → "PASS" / "MISSING" / "FAIL:<현재해시>"
    verify_all(targets)   → {파일명: status} dict + 전체 PASS 여부
    print_report(results) → 터미널 출력 헬퍼
"""
from pathlib import Path
from typing import Dict, Iterable, NamedTuple, Tuple

from src.common.manifest import sha256_file
from src.common.paths import MANIFEST_DIR, SPLIT_MANIFEST_CSV, TRAIN_CSV, VAL_CSV, TEST_CSV


# ── Baseline 확정 해시 (앞 12자리) ───────────────────────────────────────────
# 주의: split_manifest.csv 의 "1b074fa" 는 git commit hash 이지 파일 SHA-256 이 아님.
#        → 빈 문자열 = 파일 존재 확인만 (해시 비교 없음)
FREEZE_HASHES: Dict[str, str] = {
    "split_manifest.csv": "",             # 존재 확인만 (git commit ref: 1b074fa)
    "train.csv":          "8b9e6b7c4644",
    "val.csv":            "eabbaa9b8f3a",
    # test.csv 는 가이드에 명시된 freeze hash 없음 → 존재 여부만 확인
}

# freeze hash 길이 (앞 12자리 비교)
_HASH_PREFIX = 12


class FreezeResult(NamedTuple):
    path: Path
    expected: str   # 빈 문자열이면 "존재 확인만"
    actual: str     # 파일 없으면 ""
    status: str     # "PASS" | "MISSING" | "FAIL:<hash>"


def freeze_status(path: str | Path, expected_hash: str = "") -> FreezeResult:
    """단일 파일 검증.
    expected_hash 가 비어 있으면 파일 존재 여부만 확인(PASS/MISSING).
    """
    path = Path(path)
    if not path.exists():
        return FreezeResult(path, expected_hash, "", "MISSING")
    actual = sha256_file(path, prefix=_HASH_PREFIX)
    if not expected_hash:
        return FreezeResult(path, "", actual, "PASS")
    if actual == expected_hash[:_HASH_PREFIX]:
        return FreezeResult(path, expected_hash, actual, "PASS")
    return FreezeResult(path, expected_hash, actual, f"FAIL:{actual}")


def verify_all(
    targets: Iterable[Tuple[str | Path, str]] | None = None
) -> Tuple[Dict[str, FreezeResult], bool]:
    """여러 파일을 한꺼번에 검증.

    targets: [(path, expected_hash), ...]  미지정 시 기본 Baseline 4종 검증.
    반환: (결과 dict, 전체 PASS 여부)
    """
    if targets is None:
        targets = [
            (SPLIT_MANIFEST_CSV, FREEZE_HASHES.get("split_manifest.csv", "")),
            (TRAIN_CSV,          FREEZE_HASHES.get("train.csv", "")),
            (VAL_CSV,            FREEZE_HASHES.get("val.csv", "")),
            (TEST_CSV,           ""),   # 존재 확인만
        ]
    results: Dict[str, FreezeResult] = {}
    all_pass = True
    for path, expected in targets:
        r = freeze_status(path, expected)
        results[Path(path).name] = r
        if r.status != "PASS":
            all_pass = False
    return results, all_pass


def print_report(results: Dict[str, FreezeResult]) -> None:
    """결과를 터미널에 출력."""
    print("\n[Split Freeze 검증]")
    print(f"  {'파일':<30} {'기대(앞12)':<14} {'실제(앞12)':<14} {'결과'}")
    print("  " + "-" * 70)
    for name, r in results.items():
        exp = r.expected[:_HASH_PREFIX] if r.expected else "(존재확인)"
        print(f"  {name:<30} {exp:<14} {r.actual or 'N/A':<14} {r.status}")
    print()
