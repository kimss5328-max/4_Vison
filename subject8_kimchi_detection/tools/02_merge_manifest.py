"""02_merge_manifest.py — 데이터 대장(manifest) 통합

tools/merge_manifest.py 를 위임 실행합니다.

[사용법]  (프로젝트 루트에서)
  python tools/02_merge_manifest.py 받은파일1.csv 받은파일2.csv     # 미리보기
  python tools/02_merge_manifest.py 받은파일1.csv ... --apply       # 적용
  python tools/02_merge_manifest.py --origin ~/exe_01 --apply       # 900장 채우기

[주의]
  --apply 는 기존 dataset_manifest.csv 를 manifests/backup/ 에 자동 복사 후 덮어씁니다.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    cmd = [sys.executable,
           str(PROJECT_ROOT / "tools" / "merge_manifest.py")]
    # 이 스크립트에 전달된 모든 인수를 그대로 넘김
    cmd.extend(sys.argv[1:])
    print(f"\n[실행] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
