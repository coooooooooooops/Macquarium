# Macquarium: handoff

Status as of v1.0.0 (internal builds were numbered v2.0 to v2.3). Read this first if you're picking the project up.

## What it is

A macOS app plus CLI that puts a **live pixel-art coral reef behind every
Terminal.app window**. On each new Terminal window the shell asks *"Take care of
the aquarium? (y/n)"*. **y** opens care mode (feed / lure / tap glass, esc to
return) and **n** continues to the shell. It's permanent until
`macquarium uninstall`.

## Layout

```
bin/macquarium          bash 3.2 CLI: on/off/care/ask/status/swim/uninstall
shell/macquarium.zsh    prompt theme + startup question (bash version alongside)
install.sh              builds the Swift app with xcrun swiftc, installs to ~/Applications, adds rc block
app/main.swift          menu-bar helper: one borderless WKWebView window per Terminal window,
                        kept directly behind it (CGWindowList polling at 30 Hz + order(.below, relativeTo:)).
                        Care mode = raise the window to .floating, accept mouse, activate.
                        URL scheme macquarium://care. Writes ~/.macquarium/state/tank.json (stats).
app/Info.plist          LSUIElement app, bundle id com.coops.macquarium, URL scheme
app/tank/               index.html + tank.js engine, atlas.png/atlas.js (sprites), water.png, reef.png
art/                    Python generators: sprites.py (fish), creatures.py (turtle/ray/seahorse),
                        reef.py (water + reef), export_atlas.py (atlas + reef surface data)
scripts/build-themes.py Terminal profile "Macquarium Reef" (background alpha 0.12) + iTerm colours
docs/                   README images
```

## v2.1 detail pass
- Reef v2.2: small reef life fills the rock (zoanthids, feather dusters, clams, urchins, sea whips, worms, starfish), elkhorn + pillar corals, contact shadows, crevices and algae on the rock. fr = separate RNG stream in reef.py.
- Far reef backdrop baked into water.png, plus `caustics.png`, a tileable light ripple drawn only on reef and sand
  (masked with destination-in in an offscreen canvas).
- Seagrass and anemones are 8-frame swaying sprites ('Decor*' in the atlas, positions in REEF.decor).
- Garden eels, the crab, marine snow, surface shimmer and fish turn animations are drawn procedurally in tank.js.

## Fixed on a real Mac (macOS 27.2.1)
- v2.0 crashed in Tank.init: WKWebView.loadFileURL threw NSInvalidArgumentException for a file URL with a ?dim= query. Now loads plain index.html; dim is injected as window.__mqDim.
- Diagnostics: ~/.macquarium/state/app.log, `macquarium doctor`; crash reports in ~/Library/Logs/DiagnosticReports/Macquarium-*.ips.

## v2.2 (after first real-Mac run: it works)
- Tank window has rounded corners (layer mask; `macquarium corners N`, default 16) and `.transient`
  so it hides in Mission Control.
- Shake: sync() sees the Terminal window move without resizing and calls mq.shake(dx, dy). The engine
  springs the whole frame (slosh), flings fish, kicks up sand and bubbles, eels hide.
- The user's own prompt is untouched (underwater prompt is opt-in with MACQUARIUM_PROMPT=1); startup asks only
  "Take care of the aquarium? (y/n)".
- Care-mode HUD uses the Pixelify Sans pixel font + pixel icons in app/tank/icons.

## v2.3
- Fishing replaces the lure (tank.js: rod state machine idle -> sinking -> waiting -> fight -> landed). Tension and
  reel bars are in #fight, the catch card is a DOM #card with records in localStorage 'macquarium.best', and the fish is
  thrown back with a splash. Headless auto-play test: 4/4 landed, every fish returned to the tank.
- New blacktip reef shark: art/sprites.py toon_shark() (black outline, flat greys, black tips, flank flash).
- Tap-glass hand icon and cursor come from the user's pointing-hand image (icons/tap.png, tap_small.png).

## Verified

- `tank.js` was run in headless Chrome: no errors. Feeding raises fullness, and
  tap and lure work. The window resizes from wide to narrow, with the reef tiling
  and mirroring to fill the width.
- The CLI and installer pass syntax checks, and the CLI commands run.
- The zsh startup question was tested in a pty: **n** continues and **y** calls
  `macquarium care`.
- The art pipeline in `art/` reproduces the shipped PNGs exactly.

## Not yet verified (no Mac in the build environment)

1. **`app/main.swift` has never been compiled.** First job: run `./install.sh` on
   a Mac and fix any compiler errors.
2. Whether `NSWindow.order(.below, relativeTo:)` reliably slots our window
   directly under another app's window. If it doesn't, the fallback is to put the
   tank windows at `kCGDesktopWindowLevel + 1`.
3. Whether WebKit throttles `requestAnimationFrame` because it thinks the tank
   window is occluded (it sits under a translucent Terminal window). If fish
   freeze, look at `NSWindow.occlusionState`, or drive frames from Swift.
4. Whether `localStorage` persists for the file:// page in WKWebView. As a
   backup, the stats are injected from `tank.json` via `window.__mqSaved`.
5. Terminal's title bar and tab bar sit over the top of the tank, which is fine.

## Ideas for next stages

- Day/night cycle tied to the clock, with dimmer water at night and glowing jellies.
- Fish that recognise the user, gathering at the glass when care mode opens.
- Unlockable fish for keeping happiness high.
- Tail-wag frames are simple 1px bends. Proper hand-drawn frames would look nicer.
- A tank editor to rearrange the corals.

## What to tell the next AI

> "Continue Macquarium from HANDOFF.md. First compile app/main.swift on macOS
> with ./install.sh and fix any build errors, then test the live tank behind
> Terminal (items 2 to 4 under 'Not yet verified')."
