"""03_export_final.py — 승인 완료된 학습 데이터 추출

tools/export_final.py 를 위임 실행합니다.

[사용법]  (프로젝트 루트에서)
  python tools/03_export_final.py                          # 미리보기
  python tools/03_export_final.py --apply                  # 실제 복사
  python tools/03_export_final.py --all --flat --apply     # 모든 단계·flat 구조

[주의]
  --apply 는 data/final/ 에 실제 파일을 복사합니다.
  원본(data/<dataset>_result/) 은 건드리지 않습니다.
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    cmd = [sys.executable,
           str(PROJECT_ROOT / "tools" / "export_final.py")]
    cmd.extend(sys.argv[1:])
    print(f"\n[실행] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
