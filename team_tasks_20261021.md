# 교과8 마무리 작업 — 2026-10-21까지

- 기준 브랜치: `feature/7_8._final` (최신 `4fc5fa8`)
- 순서는 의존 관계 기준입니다. 앞 단계가 끝나야 뒤 단계 내용이 확정됩니다.
- 끝난 항목은 `[ ]`를 `[x]`로 바꿔 주세요. 모두 끝나면 이 파일은 삭제합니다.

---

## 0. 먼저 할 것 (모두)

- [ ] 1. pull 전에 각자 PC의 `subject8_kimchi_detection/demo/auto_label/`, `runs/baseline_v1/results.csv` 백업 — pull하면 지워짐 (원본: 드라이브 `demo.tar` · `runs.tar`)
- [ ] 2. `git pull`
- [ ] 3. 환경 맞추기: torch를 cu130 빌드로 먼저 설치 → `pip install -r subject8_kimchi_detection/requirements.txt` → `8.4.175 2.14.1+cu130 2.2.6 True` 확인 (명령은 README 5-2)
- [ ] 4. `demo/` · `runs/` · `data/` · `models/` 아래 파일은 `git add -f` 금지. `git add .` 대신 파일 이름 지정

## 1. 결정 (오전)

- [ ] 5. handoff 파일 이름: `docs/handoff_subject14.md` → `docs/handoff_subject14.md`로 바꿀지 결정 (바꾸면 README 5-3절 · 16절도 수정)
- [ ] 6. 저장소 공개 여부 확인. Public이면 예전 커밋의 라벨 txt · 루트 README 유튜브 링크 처리 결정
- [x] 7. 루트 `README.md`의 없는 명령(`scripts/06_evaluate.py`) 수정
- [ ] 7-1. `feature/split_7_8` 최신 커밋(`4541415`)은 작업 폴더를 final과 같은 내용으로 맞춘 것 (README · requirements · reports 4개).
  이 브랜치를 계속 둘지 결정. 이전 버전 보기: `git fetch origin && git switch -c split_old 7df5d2c`

## 2. 산출물 (오전~오후)

- [ ] 8. `subject8_kimchi_detection/presentation/qna_guide.md` — 예상 질문 · 답변 · 근거 파일 경로
- [ ] 9. `subject8_kimchi_detection/presentation/final_presentation.pdf` 완성
- [ ] 10. (선택) `subject8_kimchi_detection/demo/README.md` — 폴더 구조와 드라이브 위치만

## 3. 확인 (오후)

- [ ] 11. 드라이브 `visol_drive_20261016` 공유 범위가 "제한됨"(팀원 계정만)인지 확인
- [ ] 12. Final Gate 자가점검 (수행가이드 22.8)

## 4. 마지막

- [ ] 13. 발표 리허설 — 시연 1: 터미널 Detection / 시연 2: 라벨링 프로그램 Auto Label → 검수

---

- EXP002 · EXP003은 사용하지 않음 (`experiment_log.csv`에 추가하지 않음)
