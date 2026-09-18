#!/bin/bash
# 새 기기에서 한 번만 실행한다.
#   git clone https://github.com/dq-QQQ/COTE.git ~/COTE && ~/COTE/bootstrap.sh
set -e
R="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.claude/skills
if [ -e ~/.claude/skills/codetest ] && [ ! -L ~/.claude/skills/codetest ]; then
  echo "이미 실제 디렉터리가 있다. 백업 후 진행한다."
  mv ~/.claude/skills/codetest ~/.claude/skills/codetest.bak.$(date +%s)
fi
rm -f ~/.claude/skills/codetest
ln -s "$R/skill" ~/.claude/skills/codetest || {
  echo "심볼릭 링크 실패 — 복사로 대체한다"; cp -R "$R/skill" ~/.claude/skills/codetest; }
git -C "$R" config user.name  "dq-qqq"
git -C "$R" config user.email "kjsl4tw@naver.com"
echo "완료. Claude Code 를 새로 띄우면 codetest 스킬이 잡힌다."
echo "  CT_HOME=$R"
