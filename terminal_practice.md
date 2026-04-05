# Terminal & Vim Practice Guide
> Tailored to your setup: zsh + tmux (Ctrl+A prefix) + Neovim (LazyVim) + Kitty + Claude Code

---

## Part 1: Core Concepts (The Mental Model)

### What is what?

```
┌─────────────────────────────────────────────┐
│  Kitty (Terminal Emulator)                  │  ← The app/window you see
│  ┌───────────────────────────────────────┐  │
│  │  tmux (Terminal Multiplexer)          │  │  ← Manages sessions/panes inside Kitty
│  │  ┌────────────────┬──────────────────┐│  │
│  │  │  Pane 1        │  Pane 2          ││  │
│  │  │  zsh shell     │  zsh shell       ││  │  ← Each pane runs a shell
│  │  │  (Claude Code) │  (nvim)          ││  │  ← Shell runs programs
│  │  └────────────────┴──────────────────┘│  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Kitty** = The terminal emulator application (like Chrome is a web browser)
**tmux** = A multiplexer that lets you have multiple panes/windows inside one terminal
**zsh** = Your shell — the program that interprets commands you type
**Neovim** = A text editor that runs inside the shell
**Claude Code** = An AI CLI that runs inside the shell

### The Shell Startup Chain

When you open Kitty:
1. Kitty launches → starts `zsh`
2. zsh reads `~/.zshrc` (your config file)
3. Your `.zshrc` auto-launches `tmux` (line 7-9)
4. Inside tmux, another zsh starts → reads `.zshrc` again
5. That `.zshrc` auto-launches `claude --dangerously-skip-permissions` (line 80-83)

**Key files:**
- `~/.zshrc` — shell config (aliases, PATH, env vars, startup commands)
- `~/.tmux.conf` — tmux config (keybindings, appearance)
- `~/.config/nvim/init.lua` — neovim config (loads LazyVim)
- `~/.config/kitty/kitty.conf` — kitty config (font, colors, keybindings)

### PATH and Environment Variables

```bash
# PATH is a list of directories where the shell looks for programs
echo $PATH            # see your PATH
which python          # which python binary is found first in PATH
which nvim            # where is neovim installed

# Environment variables are key-value pairs available to all programs
echo $EDITOR          # your default editor (nvim)
echo $SHELL           # your shell (/bin/zsh)
echo $HOME            # your home directory
echo $PWD             # current working directory (same as `pwd`)
env                   # list ALL environment variables
```

### What is `~`? What is `.`?

```
~           = /Users/sujai (your home directory)
.           = current directory
..          = parent directory
/           = root of the entire filesystem
~/.zshrc    = /Users/sujai/.zshrc
./foo.py    = foo.py in the current directory
```

---

## Part 2: Essential Shell Commands

### Navigation

```bash
pwd                     # print working directory (where am I?)
ls                      # list files in current directory
ls -la                  # list ALL files (including hidden) with details
ls -lah                 # same but human-readable file sizes

cd /Users/sujai/Desktop # go to an absolute path
cd ..                   # go up one directory
cd -                    # go back to previous directory
cd ~                    # go to home directory
cd                      # also goes to home directory

# You have zoxide installed — smarter than cd:
z Desktop               # jump to a frequently visited directory matching "Desktop"
z play                  # jump to most frequent dir matching "play"
zi                      # interactive zoxide selection with fzf
```

### Viewing Files & Directories

```bash
cat file.txt            # print entire file contents
head -20 file.txt       # first 20 lines
tail -20 file.txt       # last 20 lines
tail -f logfile.txt     # follow a file in real-time (great for logs)
less file.txt           # paginated viewer (q to quit, / to search)
wc -l file.txt          # count lines in a file
file somefile           # tell you what type of file it is
```

### Creating & Manipulating Files/Directories

```bash
touch newfile.txt       # create empty file (or update timestamp)
mkdir mydir             # create directory
mkdir -p a/b/c          # create nested directories (parents too)

cp file.txt copy.txt    # copy a file
cp -r dir1 dir2         # copy a directory recursively
mv old.txt new.txt      # rename/move a file
mv file.txt ../         # move file up one directory

rm file.txt             # delete a file (PERMANENT — no trash!)
rm -r mydir             # delete a directory and contents
rm -rf mydir            # force delete (no confirmation) — BE CAREFUL
```

### Searching & Finding

```bash
# Find files by name
find . -name "*.py"           # find all .py files under current dir
find . -name "*.py" -type f   # only files, not directories
find ~ -name ".zshrc"         # find .zshrc from home directory

# Search file contents
grep "def main" *.py          # search for "def main" in all .py files
grep -r "import torch" .      # recursive search in all files
grep -rn "TODO" .             # recursive with line numbers
grep -ri "error" logs/        # case-insensitive recursive search

# ripgrep (rg) — faster grep, respects .gitignore
rg "def train"                # search current dir recursively
rg "def train" --type py      # only in Python files
rg -l "import torch"          # just list matching filenames
```

### Pipes and Redirection

```bash
# | (pipe) sends output of one command as input to another
ls -la | grep ".py"           # list files, filter to .py only
cat file.txt | wc -l          # count lines in a file
history | grep "git"          # search your command history for git commands
ps aux | grep python          # find running python processes

# > and >> redirect output to a file
echo "hello" > file.txt       # write to file (overwrites!)
echo "world" >> file.txt      # append to file
ls -la > filelist.txt         # save directory listing to file

# 2>&1 redirects stderr to stdout (capture errors too)
python script.py > output.txt 2>&1   # capture both stdout and stderr
```

### Process Management

```bash
# Running processes
ps aux                  # list all running processes
ps aux | grep python    # find python processes
top                     # interactive process viewer (q to quit)
htop                    # better interactive viewer (if installed)

# Background jobs
python train.py &       # run in background (& at end)
jobs                    # list background jobs in this shell
fg                      # bring last background job to foreground
fg %1                   # bring job #1 to foreground
Ctrl+Z                  # suspend (pause) current foreground process
bg                      # resume suspended process in background

# Killing processes
kill 12345              # send SIGTERM to process ID 12345
kill -9 12345           # force kill (SIGKILL) — last resort
killall python          # kill all processes named "python"
```

### Permissions & Ownership

```bash
ls -la                  # shows permissions like: -rwxr-xr-- 
#                         -rwx r-x r--
#                         │    │   │
#                         │    │   └── others: read only
#                         │    └────── group: read + execute
#                         └─────────── owner: read + write + execute

chmod +x script.sh      # make a file executable
chmod 755 script.sh     # rwxr-xr-x (common for scripts)
chmod 644 file.txt      # rw-r--r-- (common for regular files)
```

### Disk & System Info

```bash
df -h                   # disk space usage (human-readable)
du -sh *                # size of each item in current directory
du -sh .                # total size of current directory
uname -a                # system info (OS, kernel version)
whoami                  # current username
hostname                # machine name
```

### Your Custom Aliases (from .zshrc)

```bash
rl                      # reload .zshrc (source ~/.zshrc)
vim file.py             # actually opens nvim (aliased)
vi file.py              # also opens nvim (aliased)
ccd                     # claude --dangerously-skip-permissions
ccdc                    # claude --dangerously-skip-permissions --continue
z <partial-name>        # zoxide smart cd
t                       # sesh session picker (fzf)
```

---

## Part 3: Git Essentials

```bash
# Status & inspection
git status              # what's changed?
git diff                # unstaged changes
git diff --staged       # staged changes (what will be committed)
git log --oneline -10   # last 10 commits, compact
git log --graph --oneline --all  # visual branch history
git blame file.py       # who changed each line and when

# Basic workflow
git add file.py         # stage a specific file
git add -A              # stage everything (careful with secrets!)
git commit -m "msg"     # commit staged changes
git push                # push to remote
git pull                # fetch + merge from remote

# Branches
git branch              # list local branches
git branch -a           # list all branches (including remote)
git checkout -b new-branch    # create and switch to new branch
git switch main         # switch to main (modern syntax)
git switch -c feature   # create and switch (modern syntax)
git merge feature       # merge feature into current branch

# Stash (temporarily save uncommitted changes)
git stash               # stash changes
git stash pop           # apply and remove most recent stash
git stash list          # list all stashes

# Undo things
git checkout -- file.py       # discard unstaged changes to file
git restore file.py           # same thing (modern syntax)
git reset HEAD file.py        # unstage a file
git reset --soft HEAD~1       # undo last commit, keep changes staged
```

---

## Part 4: tmux (Your Config)

Your prefix key is **Ctrl+A** (not the default Ctrl+B).

### Sessions, Windows, and Panes

```
Session (a named workspace — e.g., "project-x")
  └── Window (like a browser tab — e.g., "code", "server")
       └── Pane (a split within a window)
```

### Key Bindings (Your Config)

```
PREFIX = Ctrl+A

# Pane creation
Ctrl+N              → split pane below (no prefix needed!)
Ctrl+P              → split pane right (no prefix needed!)
PREFIX + |          → split right (alternative)
PREFIX + -          → split below (alternative)

# Pane navigation (no prefix needed!)
Ctrl+H              → move to left pane
Ctrl+J              → move to down pane
Ctrl+K              → move to up pane
Ctrl+L              → move to right pane

# Pane management
PREFIX + x          → close current pane (no confirmation)
PREFIX + z          → zoom pane (toggle fullscreen for one pane)

# Windows (tabs)
PREFIX + c          → new window
PREFIX + n          → next window
PREFIX + p          → previous window (NOTE: conflicts with Ctrl+P split!)
PREFIX + 1-9        → go to window by number

# Sessions
PREFIX + T          → sesh session picker (your custom binding)
PREFIX + d          → detach from tmux (session keeps running)
PREFIX + $          → rename current session

# Claude Code integration
PREFIX + g          → open editor with Claude context
PREFIX + v          → fork Claude session

# Copy mode (scroll back through output)
PREFIX + [          → enter copy mode (scroll with vim keys)
q                   → exit copy mode
```

### tmux Commands (from shell)

```bash
tmux ls                 # list sessions
tmux new -s myproject   # create named session
tmux attach -t myproj   # attach to session
tmux kill-session -t X  # kill session X
```

### Sesh (Your Session Manager)

```bash
t                       # fuzzy pick from sesh list (your alias)
# Inside the picker:
#   Ctrl+A → all sessions
#   Ctrl+T → tmux sessions only
#   Ctrl+X → zoxide directories
#   Ctrl+D → kill a tmux session
#   Ctrl+F → find directories
```

---

## Part 5: Neovim / LazyVim (Your Config)

Your setup: Neovim with LazyVim framework, custom keymaps.

### Modes

```
NORMAL mode     → default, for navigation and commands (press Esc to return here)
INSERT mode     → for typing text (press i, a, o, etc. to enter)
VISUAL mode     → for selecting text (press v, V, or Ctrl+V)
COMMAND mode    → for ex commands (press : to enter)
```

### Your Custom Keymaps

```
q               → quit (if no unsaved changes)
qq              → force quit (discard changes)
sq              → save and quit
```

### Essential Navigation (Normal Mode)

```
# Basic movement
h / j / k / l   → left / down / up / right
w               → jump forward one word
b               → jump backward one word
e               → jump to end of word
0               → go to beginning of line
$               → go to end of line
^               → go to first non-space character

# Big jumps
gg              → go to top of file
G               → go to bottom of file
42G             → go to line 42
Ctrl+D          → scroll down half page
Ctrl+U          → scroll up half page
{               → jump to previous blank line (paragraph up)
}               → jump to next blank line (paragraph down)
%               → jump to matching bracket/paren

# Search
/pattern        → search forward for "pattern"
?pattern        → search backward
n               → next match
N               → previous match
*               → search for word under cursor (forward)
#               → search for word under cursor (backward)
```

### Editing (Normal Mode)

```
# Enter insert mode
i               → insert before cursor
a               → insert after cursor
I               → insert at beginning of line
A               → insert at end of line
o               → open new line below and insert
O               → open new line above and insert

# Delete
x               → delete character under cursor
dd              → delete entire line
dw              → delete word
d$  or D        → delete to end of line
d0              → delete to beginning of line

# Change (delete + enter insert mode)
cw              → change word
cc              → change entire line
c$  or C        → change to end of line
ci"             → change inside quotes
ci(             → change inside parentheses
ciw             → change entire word (even if cursor is in middle)

# Copy (yank) and paste
yy              → yank (copy) entire line
yw              → yank word
y$              → yank to end of line
p               → paste after cursor
P               → paste before cursor

# Undo / redo
u               → undo
Ctrl+R          → redo

# Repeat
.               → repeat last change (VERY powerful)
```

### Visual Mode (Selecting Text)

```
v               → character-wise visual mode
V               → line-wise visual mode (select whole lines)
Ctrl+V          → block/column visual mode

# Once in visual mode:
d               → delete selection
y               → yank (copy) selection
c               → change selection (delete + insert mode)
>               → indent selection
<               → unindent selection
```

### Text Objects (The Power of Vim)

These work with d, c, y, v — the pattern is: `operator` + `i/a` + `object`
- `i` = "inside" (not including delimiters)
- `a` = "around" (including delimiters)

```
diw             → delete inner word
ciw             → change inner word
daw             → delete a word (including trailing space)
ci"             → change inside double quotes
ci'             → change inside single quotes
ci(  or ci)     → change inside parentheses
ci{  or ci}     → change inside curly braces
ci[  or ci]     → change inside square brackets
cit             → change inside HTML/XML tag
dip             → delete inner paragraph
vip             → select inner paragraph
ya"             → yank around double quotes (includes the quotes)
```

### Command Mode (`:` commands)

```
:w              → save file
:q              → quit
:wq             → save and quit
:q!             → quit without saving
:e filename     → open a file
:123            → go to line 123
:%s/old/new/g   → replace all "old" with "new" in entire file
:s/old/new/g    → replace in current line only
:%s/old/new/gc  → replace all with confirmation
:!command       → run a shell command (e.g., :!ls)
:r !command     → insert output of shell command into file
:set number     → show line numbers
:noh            → clear search highlighting
```

### LazyVim Specific (Space is the Leader Key)

```
Space           → opens which-key menu (shows available commands!)

# File navigation
Space + f + f   → find files (telescope fuzzy finder)
Space + f + r   → recent files
Space + f + g   → live grep (search in all files)
Space + /       → search in project (grep)
Space + ,       → switch between open buffers
Space + e       → file explorer (neo-tree)

# Buffers
Space + b + d   → close current buffer
Space + b + b   → switch buffers

# Code
Space + c + a   → code actions
Space + c + r   → rename symbol
gd              → go to definition
gr              → go to references
K               → hover documentation

# Windows
Space + w + ...  → window commands
Space + -        → split below
Space + |        → split right

# Git (if lazygit installed)
Space + g + g   → open lazygit
```

---

## Part 6: Practical Exercises

### Exercise 1: File System Navigation
```bash
# Do these in a shell pane (not in Claude Code):
cd ~/Desktop
mkdir -p practice/src practice/tests practice/data
cd practice
touch src/main.py src/utils.py tests/test_main.py
ls -la src/
tree .              # if you have tree installed, shows directory structure
find . -name "*.py"
cd ..
rm -rf practice     # clean up
```

### Exercise 2: tmux Pane Workflow
```
1. Press Ctrl+N to split a pane below
2. Press Ctrl+L to move to the right pane (or Ctrl+K to go up)
3. Press Ctrl+P to split right
4. Navigate between all 3 panes with Ctrl+H/J/K/L
5. In one pane, type: echo "I'm pane 1"
6. Ctrl+A then z to zoom one pane (toggle)
7. Ctrl+A then x to close a pane
```

### Exercise 3: Vim Editing Drill
Open a file in vim and practice:
```
1. vim ~/Desktop/shreshth_play/vim_practice.py
2. Navigate with h/j/k/l (no arrow keys!)
3. Press gg to go to top, G to go to bottom
4. Press /def to search for function definitions
5. Press n to cycle through matches
6. Go to a function name, press ciw to change the word
7. Type a new name, press Esc
8. Press u to undo
9. Press dd to delete a line, then p to paste it elsewhere
10. Press sq to save and quit (your custom binding)
```

### Exercise 4: Pipes and Text Processing
```bash
# Create a sample file
echo -e "apple\nbanana\ncherry\napricot\nblueberry" > fruits.txt

# Practice pipes
cat fruits.txt | grep "a"           # lines containing "a"
cat fruits.txt | sort               # alphabetical sort
cat fruits.txt | sort -r            # reverse sort
cat fruits.txt | wc -l              # count lines
cat fruits.txt | head -3            # first 3 lines
cat fruits.txt | grep "^a"          # lines starting with "a"
cat fruits.txt | sort | uniq        # sorted unique (already unique here)

# Cleanup
rm fruits.txt
```

### Exercise 5: Git Workflow
```bash
cd ~/Desktop
mkdir git-practice && cd git-practice
git init
echo "# Practice Repo" > README.md
git add README.md
git commit -m "Initial commit"
git checkout -b feature
echo "new feature" > feature.txt
git add feature.txt
git commit -m "Add feature"
git switch main
git merge feature
git log --oneline --graph
cd .. && rm -rf git-practice    # clean up
```

### Exercise 6: Process & System Commands
```bash
ps aux | grep -i python         # any python processes running?
which python                    # which python is active?
python --version                # python version
echo $PATH | tr ':' '\n'        # see PATH dirs, one per line
df -h                           # disk space
du -sh ~/Desktop/*              # size of each item on Desktop
```

### Exercise 7: The Claude Code + Vim Workflow
```
In a technical interview, the typical flow is:

1. You're in Claude Code in a tmux pane
2. Claude Code edits a file → you want to review it
3. Press Ctrl+A then g → opens vim with context in a side pane
4. Review/edit in vim, then sq to save+quit
5. Back in Claude Code, continue the conversation

Alternative flow:
1. Ctrl+N to make a new pane below
2. In the new pane, open the file: vim src/something.py
3. Make your edits
4. sq to save and quit
5. Ctrl+K to go back up to Claude Code pane
6. Tell Claude what you changed

Forking a Claude session:
1. Ctrl+A then v → forks Claude into a new pane
2. Now you have two Claude sessions with shared context
3. Use one for coding, one for research
```

---

## Part 7: Quick Reference Card

### Most-Used Commands (Print This)

```
SHELL                          TMUX (prefix = Ctrl+A)
──────────────────────         ──────────────────────────
ls -la     list all files      Ctrl+N     split below
cd <dir>   change dir          Ctrl+P     split right
z <name>   smart cd            Ctrl+HJKL  navigate panes
pwd        where am I          Prefix+x   close pane
mkdir -p   make dirs           Prefix+z   zoom pane
rm -r      delete dir          Prefix+c   new window
cp/mv      copy/move           Prefix+T   sesh picker
grep -rn   search content      Prefix+d   detach
find       search names        Prefix+g   vim+context
chmod +x   make executable     Prefix+v   fork claude

VIM (Normal Mode)              GIT
──────────────────────         ──────────────────────────
i/a/o      enter insert        git status    what changed?
Esc        back to normal      git add <f>   stage file
dd         delete line         git commit    commit
yy/p       copy/paste line     git push      push remote
ciw        change word         git pull      fetch+merge
/text      search              git log       history
u / Ctrl+R undo/redo           git diff      see changes
gg / G     top/bottom          git stash     save for later
q          quit (your map)     git branch    list branches
sq         save+quit (yours)   git checkout -b  new branch
Space+ff   find files (lazy)
Space+/    grep project (lazy)
```

---

## Part 8: Common Interview Scenarios

### "Open this file and change X"
→ In Claude Code: ask Claude to edit it, or `! vim file.py` to open it yourself

### "Run this script and debug the error"
→ `! python script.py` from Claude Code, or open a new pane (Ctrl+N) and run there

### "Find where function X is defined"
→ `! grep -rn "def function_x" .` or ask Claude to search

### "Set up a Python environment for this project"
→ Claude Code handles this via your .conda-env convention automatically

### "Show me the git history for this file"
→ `! git log --oneline file.py` or `! git log -p file.py` (with diffs)

### "Run tests"
→ `! python -m pytest tests/` or ask Claude to run them

### "I need to see two files side by side"
→ Ctrl+P to split right, open different files in each pane with vim

### Tip: The `!` prefix
In Claude Code, `! <command>` runs a shell command directly in the session.
This is how you run quick commands without leaving Claude Code.
