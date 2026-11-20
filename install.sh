#!/bin/bash
# Macquarium installer: builds the tank app on your Mac and sets up the command.
#   From a clone:   ./install.sh
#   One-liner:      curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/macquarium/main/install.sh | bash
set -e

REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/macquarium.git"
MQ_HOME="${MACQUARIUM_HOME:-$HOME/.macquarium}"
APP="$HOME/Applications/Macquarium.app"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"

say()  { printf '\033[38;5;45m~>\033[0m %s\n' "$*"; }
die()  { printf '\033[38;5;203mx\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || die "Macquarium is for macOS."

# get the source
if [ ! -f "$SRC/bin/macquarium" ]; then
  command -v git >/dev/null || die "git is needed for the one-line install (xcode-select --install)"
  TMP="$(mktemp -d)"; git clone --depth 1 "$REPO_URL" "$TMP/macquarium"; SRC="$TMP/macquarium"
fi

# the Swift compiler comes with the Xcode Command Line Tools
if ! xcrun --find swiftc >/dev/null 2>&1; then
  say "Macquarium needs Apple's Command Line Tools to build the tank app."
  say "A window will pop up: click Install, wait for it to finish, then run ./install.sh again."
  xcode-select --install 2>/dev/null || true
  exit 1
fi

say "Building the tank app..."
BUILD="$(mktemp -d)"
xcrun swiftc -O "$SRC/app/main.swift" -framework AppKit -framework WebKit -o "$BUILD/Macquarium" \
  || die "Build failed. Copy the error above into a GitHub issue."
pkill -x Macquarium 2>/dev/null || true
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BUILD/Macquarium" "$APP/Contents/MacOS/Macquarium"
cp "$SRC/app/Info.plist" "$APP/Contents/Info.plist"
cp -R "$SRC/app/tank" "$APP/Contents/Resources/tank"
cp "$SRC/app/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns" 2>/dev/null || true
cp "$SRC/app/MenuIcon.png" "$SRC/app/MenuIcon@2x.png" "$APP/Contents/Resources/" 2>/dev/null || true
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" >/dev/null 2>&1 || true
rm -rf "$BUILD"
say "Tank app installed at $APP"

say "Installing the macquarium command into $MQ_HOME"
mkdir -p "$MQ_HOME/state"
rm -rf "$MQ_HOME/bin" "$MQ_HOME/shell" "$MQ_HOME/themes"
cp -R "$SRC/bin" "$SRC/shell" "$SRC/themes" "$MQ_HOME/"
chmod +x "$MQ_HOME/bin/macquarium"

add_block() { # $1 = rc file, $2 = shell flavour
  touch "$1"
  grep -q '# >>> macquarium >>>' "$1" && return 0
  {
    echo ''
    echo '# >>> macquarium >>>'
    echo 'export PATH="$HOME/.macquarium/bin:$PATH"'
    echo "[ -f \"\$HOME/.macquarium/shell/macquarium.$2\" ] && source \"\$HOME/.macquarium/shell/macquarium.$2\""
    echo '# <<< macquarium <<<'
  } >> "$1"
  say "Added Macquarium to $1"
}
add_block "$HOME/.zshrc" zsh
case "$SHELL" in */bash) add_block "$HOME/.bash_profile" bash ;; esac

cat <<'EOF'

   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     ><>        o        ><(((`>
          Macquarium is installed!      O
     <><     .        >-{{'>
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EOF

if [ -t 0 ] || [ -r /dev/tty ]; then
  printf '\n   Release the fish now? [Y/n] '
  read -r ans < /dev/tty || ans=y
  case "$ans" in n|N|no) ;; *) "$MQ_HOME/bin/macquarium" on ;; esac
fi

cat <<'EOF'

   macquarium care     feed and play with the fish
   macquarium off      drain the tank (fish wait for you)
   macquarium help     everything else

EOF
