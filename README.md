# COTE — 코딩테스트 훈련 저장소

집과 회사에서 이어서 하는 코테 학습 시스템. 커리큘럼·진도·복습 스케줄·풀이 기록이
전부 여기 들어 있고, Claude Code 스킬 본체(`skill/`)도 같이 들어 있어서
**clone 한 번이면 새 기기에서 그대로 이어진다.**

## 새 기기 설치

```bash
git clone https://github.com/dq-QQQ/COTE.git ~/COTE
~/COTE/bootstrap.sh
```

`bootstrap.sh` 가 `~/.claude/skills/codetest` → `~/COTE/skill` 심볼릭 링크를 걸고
커밋 작성자를 개인 계정으로 맞춘다. Claude Code 를 새로 띄우면 `codetest` 스킬이 잡힌다.

## 매일 쓰는 법

Claude Code 에서 그냥 말하면 된다 — "코테 하자", "이 문제 왜 틀렸지", "반례 찾아줘".
스킬이 알아서 붙는다. 직접 돌리려면:

```bash
export CT_HOME=~/COTE
CT=~/COTE/skill/scripts/ct.py

python3 $CT sync --direction pull        # 시작 전 반드시
python3 $CT status                       # 약점 순위 보고 뭘 풀지 결정
python3 $CT new 미로탐색 --tags bfs       # 세션 생성
python3 $CT watch &                      # 타임라인 기록 (백그라운드)
#   ... solution.py 를 직접 작성 ...
python3 $CT judge                        # 예제 채점
python3 $CT stress                       # 예제는 맞는데 틀릴 때 반례 탐색
python3 $CT timeline                     # 어디서 막혔는지 회고
python3 $CT done --result solved --minutes 38 --hints 1
python3 $CT sync -m "미로탐색"            # 끝나면 반드시
```

## 구조

```
curriculum.md   8주 커리큘럼 + 수준 진단 결과
progress.md     세션 한 줄 로그
state/          SM-2 복습 카드, 유형별 약점 통계
sessions/       세션별 지문·풀이·테스트·타임라인
skill/          Claude Code 스킬 본체 (SKILL.md, scripts, references)
```

## 주의

- **시작 전 pull, 끝나고 push.** 양쪽에서 동시에 작업하면 충돌난다
- `--hints` 와 `--minutes` 는 정직하게. 부풀리면 복습 간격이 실력보다 길어져
  시스템 전체가 망가진다

## 이력

2022년 42서울 시절 Swift 자료구조 구현(`DataStructure/`)이 있었고 2023-07-25 에 비워졌다.
`git log` 에 남아 있다.
