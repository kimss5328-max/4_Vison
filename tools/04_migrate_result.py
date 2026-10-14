"""04_migrate_result.py — 결과 데이터 마이그레이션

tools/migrate_result.py 를 위임 실행합니다.

[사용법]  (프로젝트 루트에서)
  python tools/04_migrate_result.py --src raw --origin ~/exe_01/원본폴더   # 미리보기
  python tools/04_migrate_result.py --src raw --origin ~/exe_01/원본폴더 --apply

[주의]
  원본(images·labels) 은 복사만 하며 수정하지 않습니다.
  --apply 전 반드시 미리보기로 대상 파일을 확인하세요.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    cmd = [sys.executable,
           str(PROJECT_ROOT / "tools" / "migrate_result.py")]
    cmd.extend(sys.argv[1:])
    print(f"\n[실행] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
