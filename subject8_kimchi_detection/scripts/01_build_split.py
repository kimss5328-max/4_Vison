"""01_build_split.py — 데이터 분할 실행 + Split Freeze SHA-256 검증

[순서]
  1) tools/build_split.py 의 분할 로직을 그대로 실행 (기존 스크립트 위임)
  2) 실행 후 Split Freeze 검증 (src/common/split.py)

[사용법]  (프로젝트 루트에서)
  python tools/01_build_split.py                         # 미리보기 + Freeze 검증
  python tools/01_build_split.py --apply                 # 실제 분할 적용 + Freeze 검증
  python tools/01_build_split.py --freeze-only           # 검증만 (분할 실행 안 함)

[주의]
  --apply 는 반드시 복사본(가짜) 데이터에서 먼저 테스트 (주의 사항 7번)
"""
import argparse
import subprocess
import sys
from pathlib import Path

# PROJECT_ROOT 설정 (tools/ → parents[1])
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.split import verify_all, print_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="데이터 분할 실행 + Split Freeze 검증",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply",       action="store_true", help="실제 분할 적용")
    parser.add_argument("--freeze-only", action="store_true", help="분할 실행 없이 검증만")
    # build_split.py 에 그대로 전달할 추가 인수
    parser.add_argument("extra", nargs=argparse.REMAINDER,
                        help="tools/build_split.py 에 전달할 추가 인수")
    args = parser.parse_args()

    # ── 1) 분할 실행 ─────────────────────────────────────────────────────────
    if not args.freeze_only:
        cmd = [sys.executable,
               str(PROJECT_ROOT / "tools" / "build_split.py")]
        if args.apply:
            cmd.append("--apply")
        cmd.extend(args.extra)
        print(f"\n[실행] {' '.join(cmd)}\n")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            print(f"\n[ERROR] build_split.py 실패 (코드 {result.returncode})")
            sys.exit(result.returncode)

    # ── 2) Split Freeze 검증 ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    results, all_pass = verify_all()
    print_report(results)

    if all_pass:
        print("[PASS] Split Freeze 검증 완료 - 모든 파일 일치\n")
    else:
        fail = [n for n, r in results.items() if r.status != "PASS"]
        print(f"[FAIL] 불일치 파일: {', '.join(fail)}")
        print("       기존 split_manifest.csv 와 다릅니다.")
        print("       의도적 재분할이라면 --force 옵션을 build_split.py 에 직접 전달하세요.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
