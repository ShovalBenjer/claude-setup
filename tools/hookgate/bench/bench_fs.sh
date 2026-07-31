#!/usr/bin/env bash
# Measure the WSL2 9p crossing penalty against native ext4, on the real claude-setup tree.
# Answers: for dev work, does the checkout belong on /mnt/c or inside the distro?

t() {
  local label="$1"; shift
  local s e
  s=$(date +%s%N)
  "$@" >/dev/null 2>&1
  e=$(date +%s%N)
  printf '%6dms  %s\n' $(( (e - s) / 1000000 )) "$label"
}

WIN=/mnt/c/Users/shova/claude-setup
EXT=/tmp/bench-cs

count_files() { find . -type f -not -path './.git/*' | wc -l; }

echo "=== A: real tree over /mnt/c (9p)"
cd "$WIN" || exit 1
t "git status --porcelain  [9p]" git status --porcelain
t "git status --porcelain  [9p] warm" git status --porcelain
t "git log --oneline -50   [9p]" git log --oneline -50
t "count files             [9p]" count_files
t "python3 -c pass         [wsl python, cwd 9p]" python3 -c pass

echo
echo "=== copy to ext4"
[ -d "$EXT" ] && find "$EXT" -mindepth 0 -maxdepth 0 -exec rm -rf {} +
t "cp -r  win -> ext4" cp -r "$WIN" "$EXT"

echo
echo "=== B: same tree on ext4"
cd "$EXT" || exit 1
t "git status --porcelain  [ext4]" git status --porcelain
t "git status --porcelain  [ext4] warm" git status --porcelain
t "git log --oneline -50   [ext4]" git log --oneline -50
t "count files             [ext4]" count_files
t "python3 -c pass         [wsl python, cwd ext4]" python3 -c pass

echo
echo "=== C: tree size"
du -sh "$EXT" "$EXT/.git" 2>/dev/null
