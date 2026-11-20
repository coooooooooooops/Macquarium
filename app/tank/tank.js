/* Macquarium tank engine.
 * Logical tank is 210px tall; width follows the window. Everything is drawn
 * at 1 logical px and scaled up with nearest-neighbour for crisp pixel art.
 * Modes: "ambient" (behind your terminal text, dimmed) and "care" (play).
 */
(() => {
  'use strict';
  const A = window.ATLAS, REEF = window.REEF;
  const LH = 210, FPS = 30, STEP = 1000 / FPS;
  const cv = document.getElementById('c'), ctx = cv.getContext('2d');
  const params = new URLSearchParams(location.search);
  let LW = 420, scale = 3, ox = 0;
  let mode = params.get('mode') || 'ambient';
  let dim = clamp(parseFloat(params.get('dim') || (window.__mqDim != null ? window.__mqDim : 0.35)), 0, 0.9);
  let tool = 'feed', paused = false;
  const mouse = { x: -99, y: -99, inside: false };

  // ---------------------------------------------------------------- persistence
  const KEY = 'macquarium.v1';
  const state = (() => {
    let s; try { s = JSON.parse(localStorage.getItem(KEY)); } catch (e) { }
    if (!s && window.__mqSaved && window.__mqSaved.t) s = Object.assign({}, window.__mqSaved);
    s = s || { full: 80, joy: 75, t: Date.now() };
    decay(s, Date.now() - s.t); return s;
  })();
  function decay(s, ms) {
    const h = Math.max(0, ms) / 3.6e6;
    s.full = clamp(s.full - 6 * h, 0, 100);
    s.joy = clamp(s.joy - 3 * h - (s.full < 30 ? 3 * h : 0), 0, 100);
    s.t = Date.now();
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { } }

  // ---------------------------------------------------------------- utils
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
  function reefTop(x) { const rx = ((Math.round(x - ox) % REEF.w) + REEF.w) % REEF.w; return REEF.top[rx]; }

  // ---------------------------------------------------------------- population
  // name, behaviour, count, depth (0 near .. 2 far), speed (px/frame)
  const POP = [
    ['Sardine', 'school', 55, 2, 0.85], ['Eagle Ray', 'glide', 1, 2, 0.32],
    ['Fusilier', 'school', 14, 1, 0.75], ['Trevally', 'cruise', 2, 1, 0.65], ['Sea Turtle', 'glide', 1, 1, 0.28],
    ['Green Chromis', 'hover', 6, 1, 0.25], ['Anthias', 'hover', 6, 1, 0.28],
    ['Blue Tang', 'cruise', 2, 0, 0.42], ['Yellow Tang', 'cruise', 3, 0, 0.38], ['Moorish Idol', 'cruise', 1, 0, 0.34],
    ['Parrotfish', 'cruise', 1, 0, 0.36], ['Copperband', 'reef', 1, 0, 0.28], ['Royal Gramma', 'reef', 2, 0, 0.24],
    ['Cleaner Wrasse', 'reef', 1, 0, 0.34], ['Lionfish', 'reef', 1, 0, 0.14], ['Grouper', 'bottom', 1, 0, 0.18],
    ['Puffer', 'bottom', 1, 0, 0.2], ['Clownfish', 'anemone', 2, 0, 0.3], ['Seahorse', 'seahorse', 1, 0, 0.04],
    ['Reef Shark', 'patrol', 1, 0, 0.45],
  ];
  const BIG = new Set(['Reef Shark', 'Sea Turtle', 'Eagle Ray']);
  let fish = [], schools = {}, flakes = [], bubbles = [], fx = [], snow = [], eels = [], crab = null;
  const off = document.createElement('canvas'), octx = off.getContext('2d');
  const shot = document.createElement('canvas'), sctx = shot.getContext('2d');
  const slosh = { x: 0, y: 0, vx: 0, vy: 0 };      // the whole tank lags behind a shaken window
  let shakeEnergy = 0;
  // fishing: idle -> sinking (hook drops) -> waiting -> fight -> landed (catch card) -> back in the tank
  const CM = { 'Clownfish': 9, 'Royal Gramma': 7, 'Green Chromis': 8, 'Anthias': 10, 'Cleaner Wrasse': 10, 'Sardine': 15,
    'Fusilier': 20, 'Puffer': 25, 'Copperband': 18, 'Yellow Tang': 18, 'Blue Tang': 28, 'Moorish Idol': 20, 'Lionfish': 30,
    'Parrotfish': 45, 'Trevally': 70, 'Grouper': 80, 'Barracuda': 120, 'Reef Shark': 160 };
  const rod = { st: 'idle', x: 0, y: 0, ty: 0, f: null, tension: 0, prog: 0, run: 0, hold: false, card: 0, cm: 0, wait: 0, best: {} };
  try { rod.best = JSON.parse(localStorage.getItem('macquarium.best') || '{}'); } catch (e) { }
  const catchable = f => f.depth < 2 && CM[f.sp] && !f.out;

  function spawn() {
    fish = []; schools = {};
    for (const [sp, beh, n, depth, speed] of POP) {
      if (!A[sp]) continue;
      if (beh === 'school') schools[sp] = { tx: rnd(0, LW), ty: depth === 2 ? rnd(30, 90) : rnd(60, 130), timer: 0 };
      for (let i = 0; i < n; i++) {
        const f = { sp, beh, depth, speed: speed * rnd(0.85, 1.15), w: A[sp].w, h: A[sp].h,
          x: rnd(0, LW), y: rnd(30, 170), vx: rnd(-.3, .3), vy: 0, face: Math.random() < .5 ? 1 : -1,
          anim: Math.random() * 4, tx: 0, ty: 0, home: null, fear: 0, chomp: 0, goal: null };
        if (beh === 'hover') { const rx = Math.floor(rnd(30, REEF.w - 30)); f.home = { rx, y: REEF.top[rx] - rnd(6, 14) }; }
        if (beh === 'anemone') { const a = REEF.anemones[i % REEF.anemones.length]; f.home = { rx: a[0], y: a[1] - 6 }; }
        if (beh === 'seahorse') f.home = { rx: 14, y: 182 };
        if (beh === 'school' && depth === 2) f.y = rnd(30, 90);
        newTarget(f); f.x = f.tx + rnd(-20, 20); f.y = clamp(f.ty + rnd(-8, 8), 20, 195);
        fish.push(f);
      }
    }
    // marine snow: tiny drifting particles at three depths
    snow = [];
    for (let i = 0; i < 70; i++) snow.push({ x: rnd(0, LW), y: rnd(0, LH), z: Math.random(), p: rnd(0, 99) });
    // spotted garden eels poke out of the sand in front of the reef
    eels = [];
    for (let i = 0; i < 7; i++) eels.push({ rx: 150 + i * 6 + rnd(-2, 2), h: rnd(4, 12), want: 12, max: rnd(11, 16), p: rnd(0, 9), shy: 0 });
    crab = { x: rnd(40, LW - 40), dir: 1, wait: 0, step: 0 };
    // far things first, then by size so big animals sit in front
    fish.sort((a, b) => (b.depth - a.depth) || (a.w * a.h - b.w * b.h));
  }

  function newTarget(f) {
    const hungry = state.full < 25;
    switch (f.beh) {
      case 'cruise': f.tx = rnd(-30, LW + 30); f.ty = rnd(hungry ? 25 : 35, 165); break;
      case 'patrol': f.tx = (f.tx > LW / 2 ? -140 : LW + 140); f.ty = rnd(22, 90); break;
      case 'glide': f.tx = (f.tx > LW / 2 ? -80 : LW + 80); f.ty = rnd(20, f.depth === 2 ? 80 : 120); break;
      case 'reef': { const x = rnd(10, LW - 10); f.tx = x; f.ty = clamp(reefTop(x) + rnd(-6, 20), 110, 192); break; }
      case 'bottom': f.tx = rnd(10, LW - 10); f.ty = rnd(178, 192); break;
      case 'hover': case 'anemone': case 'seahorse': {
        const r = f.beh === 'hover' ? 14 : f.beh === 'anemone' ? 6 : 2;
        f.tx = ox + f.home.rx + rnd(-r, r); f.ty = f.home.y + rnd(-r * 0.6, r * 0.6); break;
      }
      default: f.tx = rnd(0, LW); f.ty = rnd(30, 170);
    }
  }

  // ---------------------------------------------------------------- simulation
  let t = 0;
  function update() {
    t++;
    const shark = fish.find(f => f.sp === 'Reef Shark');
    // schools: move their shared goal around
    for (const sp in schools) {
      const s = schools[sp];
      if (--s.timer <= 0) { s.tx = rnd(-20, LW + 20); s.ty = sp === 'Sardine' ? rnd(25, 95) : rnd(50, 135); s.timer = rnd(240, 520); }
    }
    for (const f of fish) {
      if (f.out) continue;
      let spd = f.speed * (state.full < 25 ? 0.75 : 1) * (f.fear > 0 ? 2.6 : 1);
      let gx = f.tx, gy = f.ty, eating = null;
      // food beats everything except fear
      if (flakes.length && f.depth < 2 && !BIG.has(f.sp) && f.beh !== 'seahorse') {
        let best = null, bd = 95 * 95;
        for (const k of flakes) { const d = (k.x - f.x) ** 2 + (k.y - f.y) ** 2; if (d < bd) { bd = d; best = k; } }
        if (best) { gx = best.x; gy = best.y; spd *= 1.7; eating = best; }
      }
      // a baited hook draws in whoever is closest
      if (!eating && rod.st === 'waiting' && rod.f === null && f === rod.curious) { gx = rod.x - f.face * f.w * 0.4; gy = rod.y; spd *= 1.2; }
      if (f === rod.f) {
        // hooked: it fights for open water, harder during a run; reeling drags it up to the rod
        const away = f.x < rod.x ? -1 : 1;
        gx = clamp(f.x + away * 40, 10, LW - 10); gy = 196;
        spd = f.speed * (rod.run > 0 ? 3.2 : 1.6);
      }
      let ax = 0, ay = 0;
      if (f.beh === 'school' && !eating) {
        // boids: cohesion, alignment, separation + the school's shared goal
        let cx = 0, cy = 0, vx = 0, vy = 0, n = 0, sx = 0, sy = 0;
        for (const o of fish) {
          if (o === f || o.sp !== f.sp) continue;
          const dx = o.x - f.x, dy = o.y - f.y, d2 = dx * dx + dy * dy;
          if (d2 < 900) { cx += o.x; cy += o.y; vx += o.vx; vy += o.vy; n++; }
          if (d2 < 30) { sx -= dx; sy -= dy * 1.6; }
        }
        const s = schools[f.sp];
        ax += (s.tx - f.x) * 0.0008; ay += (s.ty - f.y) * 0.0012;
        if (n) { ax += (cx / n - f.x) * 0.004 + (vx / n - f.vx) * 0.05; ay += (cy / n - f.y) * 0.004 + (vy / n - f.vy) * 0.05; }
        ax += sx * 0.02; ay += sy * 0.02;
      } else {
        const dx = gx - f.x, dy = gy - f.y, d = Math.hypot(dx, dy) || 1;
        ax += (dx / d * spd - f.vx) * 0.04; ay += (dy / d * spd * 0.6 - f.vy) * 0.04;
        if (d < 4 && !eating) newTarget(f);
      }
      // small fish keep clear of the shark
      if (shark && f !== shark && f.depth === shark.depth && !BIG.has(f.sp)) {
        const dx = f.x - shark.x, dy = f.y - shark.y, d = Math.hypot(dx, dy);
        if (d < 40) { ax += dx / d * 0.06; ay += dy / d * 0.06; }
      }
      f.vx += ax; f.vy += ay;
      const v = Math.hypot(f.vx, f.vy), max = spd * 1.4;
      if (v > max) { f.vx *= max / v; f.vy *= max / v; }
      f.x += f.vx; f.y += f.vy;
      f.y = clamp(f.y, f === rod.f ? 4 : 14, 196);
      if (f.fear > 0) f.fear--;
      if (f.chomp > 0) f.chomp--;
      const nf = f.vx > 0.06 ? 1 : f.vx < -0.06 ? -1 : f.face;
      if (nf !== f.face) { f.face = nf; f.turn = 8; }
      if (f.turn > 0) f.turn--;
      f.anim += 0.06 + v * 0.22;
      if (eating && Math.hypot(eating.x - f.x - f.face * f.w * 0.35, eating.y - f.y) < 4) {
        flakes.splice(flakes.indexOf(eating), 1);
        f.chomp = 18; state.full = clamp(state.full + 2.2, 0, 100); state.joy = clamp(state.joy + 0.7, 0, 100);
        fx.push({ k: 'heart', x: f.x + f.face * f.w * 0.4, y: f.y - 4, life: 30 });
      }
      // wrap schools / patrollers that leave the screen far away
      if (f.beh === 'school' && (f.x < -80 || f.x > LW + 80)) { f.x = f.x < 0 ? LW + 20 : -20; }
      if (Math.random() < 0.0015 && f.depth < 2) bubbles.push({ x: f.x + f.face * f.w * 0.45, y: f.y - 2, r: 0 });
    }
    // garden eels duck when anything swims close (or the glass is tapped)
    for (const e of eels) {
      const ex = ox + e.rx, ey = 206 - e.h;
      let threat = crab && Math.abs(crab.x + 5 - ex) < 9;
      if (!threat) for (const f of fish) {
        if (f.depth < 2 && Math.abs(f.x - ex) < 8 + f.w / 2 && Math.abs(f.y - ey) < 8 + f.h / 2) { threat = true; break; }
      }
      if (threat) e.shy = Math.max(e.shy, rnd(50, 110));
      if (e.shy > 0) { e.shy--; e.h = Math.max(0, e.h - 1.0); }
      else e.h = Math.min(e.max, e.h + 0.12);
    }
    // the crab potters along the sand, stopping now and then
    if (crab) {
      if (crab.wait > 0) crab.wait--;
      else {
        crab.x += crab.dir * 0.25; crab.step++;
        if (Math.random() < 0.004) crab.wait = rnd(60, 240);
        if (Math.random() < 0.003 || crab.x < 6 || crab.x > LW - 16) crab.dir *= -1;
      }
    }
    for (const m of snow) { m.y += 0.04 + m.z * 0.08; m.x += Math.sin((t + m.p * 40) * 0.01) * 0.05; if (m.y > LH) { m.y = -2; m.x = rnd(0, LW); } }
    // flakes sink, then rot on the sand
    for (const k of flakes) {
      if (k.y < 196) { k.y += k.vy; k.x += Math.sin((t + k.p) * 0.08) * 0.15; } else k.life--;
    }
    flakes = flakes.filter(k => k.life > 0);
    // bubbles from the reef
    if (Math.random() < 0.06) { const x = rnd(0, LW); bubbles.push({ x, y: reefTop(x) - 1, r: 0 }); }
    for (const b of bubbles) { b.y -= 0.35 + b.r * 0.1; b.x += Math.sin((b.y + b.x) * 0.2) * 0.12; if (b.y < 90 && b.r === 0 && Math.random() < 0.01) b.r = 1; }
    bubbles = bubbles.filter(b => b.y > 6);
    slosh.vx += -slosh.x * 0.09; slosh.vy += -slosh.y * 0.09; slosh.vx *= 0.86; slosh.vy *= 0.86;
    slosh.x = clamp(slosh.x + slosh.vx, -10, 10); slosh.y = clamp(slosh.y + slosh.vy, -8, 8);
    shakeEnergy *= 0.97;
    for (const e of fx) if (e.k === 'grain') { e.x += e.vx; e.y += e.vy; e.vy += e.water ? 0.08 : 0.03; if (e.y > 208) e.life = 0; }
    for (const e of fx) e.life--;
    fx = fx.filter(e => e.life > 0);
    updateRod();
    if (t % FPS === 0) { decay(state, Date.now() - state.t); hud(); }
    if (t % (FPS * 5) === 0) save();
    if (t % (FPS * 10) === 0 && window.webkit && webkit.messageHandlers && webkit.messageHandlers.mq)
      webkit.messageHandlers.mq.postMessage({ type: 'stats', full: Math.round(state.full), joy: Math.round(state.joy), t: Date.now() });
  }


  // ---------------------------------------------------------------- shaking the window
  // dx, dy: how far the Terminal window moved since the last tick, in screen points (y down)
  function shake(dx, dy) {
    const k = 1 / scale, mag = Math.hypot(dx, dy);
    if (mag < 0.5) return;
    slosh.vx -= dx * k * 0.35; slosh.vy -= dy * k * 0.35;
    shakeEnergy = Math.min(120, shakeEnergy + mag * 0.5);
    for (const f of fish) {
      if (f.depth === 2) continue;
      const m = BIG.has(f.sp) ? 0.04 : 0.14;
      f.vx -= dx * k * m * rnd(0.6, 1.4); f.vy -= dy * k * m * rnd(0.6, 1.4);
      if (mag > 10) f.fear = Math.max(f.fear, 30);
    }
    if (mag > 6) {
      for (const e of eels) e.shy = Math.max(e.shy, rnd(90, 200));
      for (let i = 0; i < Math.min(10, mag / 3); i++) bubbles.push({ x: rnd(0, LW), y: rnd(150, 200), r: Math.random() < 0.4 ? 1 : 0 });
    }
    if (mag > 14) for (let i = 0; i < mag; i++) fx.push({ k: 'grain', x: rnd(0, LW), y: rnd(198, 208), vx: rnd(-0.6, 0.6) - dx * k * 0.05, vy: rnd(-1.4, -0.3), life: rnd(50, 110) });
    if (shakeEnergy > 90 && mode === 'care' && !shake.warned) { shake.warned = true; toast('Easy! The fish are getting seasick.'); setTimeout(() => shake.warned = false, 6000); }
    if (mag > 20) state.joy = clamp(state.joy - 0.15, 0, 100);
  }


  // ---------------------------------------------------------------- fishing
  function fightHud(show) {
    const el = $('#fight'); el.style.display = show ? 'flex' : 'none';
    if (show) { $('#tension i').style.width = rod.tension.toFixed(0) + '%'; $('#reel i').style.width = rod.prog.toFixed(0) + '%';
      $('#tension').classList.toggle('hot', rod.tension > 70); $('#fight b').textContent = rod.run > 0 ? 'It\'s running! Let go!' : rod.hold ? 'Reeling...' : 'Hold to reel'; }
  }
  function cast(x, y) {
    Object.assign(rod, { st: 'sinking', x, y: 4, ty: clamp(y, 30, 190), f: null, curious: null, tension: 0, prog: 0, run: 0, wait: 0 });
    fx.push({ k: 'ripple', x, y: 2, life: 30 });
  }
  function reset(msg) { if (msg) toast(msg); rod.st = 'idle'; rod.f = null; rod.curious = null; rod.hold = false; fightHud(false); }
  function updateRod() {
    // the hook follows the mouse, just like the old lure
    const aiming = mode === 'care' && tool === 'fish' && mouse.inside;
    if (aiming && rod.st === 'idle') Object.assign(rod, { st: 'waiting', x: mouse.x, y: Math.max(8, mouse.y), f: null, curious: null, wait: 0, tension: 0, prog: 0, run: 0 });
    if (rod.st === 'waiting') {
      if (!aiming) { reset(); return; }
      const nx = rod.x + (mouse.x - rod.x) * 0.25, ny = rod.y + (Math.max(8, mouse.y) - rod.y) * 0.25;
      if (Math.hypot(nx - rod.x, ny - rod.y) > 2.5) rod.wait = Math.max(0, rod.wait - 2);   // fish wait for it to settle
      rod.x = nx; rod.y = ny;
    }
    if (rod.st === 'idle') return;
    if (mode !== 'care' || tool !== 'fish') { if (rod.st !== 'landed') { if (rod.f) rod.f.fear = 60; reset(); } }
    if (rod.st === 'sinking') { rod.y += 0.9; if (rod.y >= rod.ty) { rod.y = rod.ty; rod.st = 'waiting'; } }
    if (rod.st === 'waiting') {
      rod.wait++;
      if (!rod.curious || rod.curious.fear > 0) {
        let best = null, bd = 130;
        for (const f of fish) if (catchable(f) && f.fear <= 0 && f.beh !== 'school' && f.beh !== 'seahorse') { const d = Math.hypot(f.x - rod.x, f.y - rod.y); if (d < bd) { bd = d; best = f; } }
        rod.curious = best;
      }
      const f = rod.curious;
      if (f && Math.hypot(f.x + f.face * f.w * 0.4 - rod.x, f.y - rod.y) < 6 && rod.wait > 25) {
        rod.f = f; rod.st = 'fight'; rod.depth0 = f.y; toast('Fish on! Hold the mouse button to reel it in.');
        fx.push({ k: 'ripple', x: rod.x, y: rod.y, life: 20 });
      }
    }
    if (rod.st === 'fight') {
      const f = rod.f, size = CM[f.sp] || 20, strength = 0.6 + Math.min(2.4, size / 45);
      if (rod.run > 0) rod.run--; else if (Math.random() < 0.006 * strength + 0.004) rod.run = Math.round(rnd(18, 40) * Math.min(1.8, strength));
      if (rod.hold) {
        rod.tension += rod.run > 0 ? 2.6 * strength : 0.55 + strength * 0.15;
        f.vy -= 0.18 / Math.sqrt(strength); f.vx += (rod.x - f.x) * 0.002;          // drag it up toward the rod
      } else rod.tension -= 1.8;
      rod.tension = clamp(rod.tension, 0, 100);
      rod.x += (f.x - rod.x) * 0.05;                                                // the line follows the fish
      if (mouse.inside) rod.x += (mouse.x - rod.x) * 0.03;                           // you can steer the rod a little
      rod.y = f.y;
      rod.prog = clamp(100 * (1 - (f.y - 12) / Math.max(20, rod.depth0 - 12)), 0, 100);
      f.fear = 20;
      if (rod.tension >= 100) { f.fear = 90; f.vx *= 2; reset('Snap! The line broke and it got away.'); state.joy = clamp(state.joy - 0.5, 0, 100); return; }
      if (f.y <= 12) {
        rod.st = 'landed'; rod.card = 30 * 3.2; f.out = true; rod.hold = false; rod.cardShown = false;
        rod.cm = Math.round(size * rnd(0.8, 1.25));
        const best = rod.best[f.sp] || 0; rod.record = rod.cm > best;
        if (rod.record) { rod.best[f.sp] = rod.cm; try { localStorage.setItem('macquarium.best', JSON.stringify(rod.best)); } catch (e) { } }
        state.joy = clamp(state.joy + 1.5, 0, 100);
        for (let i = 0; i < 14; i++) fx.push({ k: 'grain', x: f.x + rnd(-6, 6), y: 4, vx: rnd(-.8, .8), vy: rnd(-1.6, -.4), life: 40, water: 1 });
      }
      fightHud(true);
    }
    if (rod.st === 'landed') {
      fightHud(false);
      if (!rod.cardShown) { rod.cardShown = true; showCard(true); }
      if (--rod.card <= 0) {             // throw it back in
        const f = rod.f; f.out = false; f.x = rnd(LW * 0.25, LW * 0.75); f.y = 10; f.vx = rnd(-1, 1); f.vy = 1.6; f.fear = 90;
        for (let i = 0; i < 10; i++) bubbles.push({ x: f.x + rnd(-6, 6), y: rnd(8, 30), r: Math.random() < 0.5 ? 1 : 0 });
        fx.push({ k: 'ripple', x: f.x, y: 2, life: 30 });
        showCard(false); reset('Back in the water it goes!');
      }
    }
  }
  function drawRod() {
    if (rod.st === 'idle') return;
    const rx = Math.round(rod.st === 'fight' ? rod.x + (rod.f.x - rod.x) * 0.3 : rod.x);
    if (rod.st !== 'landed') {
      // line from the top of the tank to the hook (taut and reddening under tension)
      const hot = rod.st === 'fight' ? rod.tension / 100 : 0;
      ctx.strokeStyle = `rgba(${230},${Math.round(240 - 150 * hot)},${Math.round(250 - 170 * hot)},${0.55 + 0.4 * hot})`;
      ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(rx + 0.5, 0);
      const hx_ = rod.st === 'fight' ? rod.f.x + rod.f.face * rod.f.w * 0.45 : rod.x, hy = rod.st === 'fight' ? rod.f.y : rod.y;
      if (rod.st === 'fight') ctx.lineTo(hx_ + 0.5, hy + 0.5);
      else ctx.quadraticCurveTo(rx + Math.sin(t * 0.05) * 3, hy * 0.5, hx_ + 0.5, hy + 0.5);
      ctx.stroke();
      if (rod.st !== 'fight') {           // the hook + a bit of bait
        px(rod.x, rod.y, '#c8d2dc'); px(rod.x, rod.y + 1, '#c8d2dc'); px(rod.x + 1, rod.y + 2, '#c8d2dc'); px(rod.x + 2, rod.y + 1, '#c8d2dc');
        px(rod.x - 1, rod.y + 1, '#ff8a5a'); px(rod.x - 1, rod.y + 2, '#ff6a3a');
      }
    }
    if (rod.st === 'landed') drawCard();
  }
  function showCard(on) {
    const el = $('#card');
    if (!on) { el.classList.remove('show'); return; }
    const f = rod.f, m = A[f.sp], fr = m.f['0_0'], c = $('#cardfish');
    c.width = m.w; c.height = m.h;
    const k = Math.max(2, Math.min(6, Math.floor(Math.min(320 / m.w, 120 / m.h))));
    c.style.width = m.w * k + 'px'; c.style.height = m.h * k + 'px';
    const g = c.getContext('2d'); g.imageSmoothingEnabled = false; g.clearRect(0, 0, m.w, m.h);
    g.drawImage(img.atlas, fr[0], fr[1], m.w, m.h, 0, 0, m.w, m.h);
    $('#cardname').textContent = 'You caught a ' + f.sp + '!';
    const sz = $('#cardsize'); sz.textContent = rod.cm + ' cm' + (rod.record ? '  ·  new record!' : '');
    sz.classList.toggle('record', !!rod.record);
    el.classList.add('show');
  }
  function drawCard() {}
  function roundRect(x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }

  // ---------------------------------------------------------------- drawing
  const img = {};
  function drawSprite(f) {
    if (f.out) return;
    const m = A[f.sp], fr = m.f[f.depth + '_' + (Math.floor(f.anim) % 4)];
    const x = Math.round(f.x - m.w / 2), y = Math.round(f.y - m.h / 2);
    if (x > LW || x + m.w < 0) return;
    let face = f.face, sx = 1;
    if (f.turn > 0) { sx = Math.max(0.15, Math.abs(Math.cos(Math.PI * f.turn / 8))); if (f.turn > 4) face = -face; }
    if (face > 0 && sx === 1) { ctx.drawImage(img.atlas, fr[0], fr[1], m.w, m.h, x, y, m.w, m.h); return; }
    ctx.save(); ctx.translate(x + m.w / 2, y); ctx.scale(face * sx, 1);
    ctx.drawImage(img.atlas, fr[0], fr[1], m.w, m.h, -m.w / 2, 0, m.w, m.h); ctx.restore();
  }
  function drawReef(c) {
    c = c || ctx;
    const n = Math.ceil(LW / REEF.w) + 2;
    for (let i = -n; i <= n; i++) {
      const x = ox + i * REEF.w;
      if (x > LW || x + REEF.w < 0) continue;
      if (i % 2 === 0) c.drawImage(img.reef, x, 0);
      else { c.save(); c.translate(x + REEF.w, 0); c.scale(-1, 1); c.drawImage(img.reef, 0, 0); c.restore(); }
    }
  }
  // rippling sunlight on the reef and sand only
  function drawCaustics() {
    if (off.width !== LW || off.height !== LH) { off.width = LW; off.height = LH; }
    if (!img.cpat) img.cpat = octx.createPattern(img.caustics, 'repeat');
    octx.globalCompositeOperation = 'source-over'; octx.clearRect(0, 0, LW, LH);
    for (const [sx, sy, a] of [[t * 0.12, t * 0.05, 0.9], [-t * 0.09, t * 0.07 + 31, 0.7]]) {
      octx.save(); octx.globalAlpha = a; octx.translate(sx % 128, sy % 64); octx.fillStyle = img.cpat;
      octx.fillRect(-128, -64, LW + 256, LH + 128); octx.restore();
    }
    octx.globalCompositeOperation = 'destination-in'; drawReef(octx);
    const g = octx.createLinearGradient(0, 90, 0, LH);
    g.addColorStop(0, 'rgba(0,0,0,0.9)'); g.addColorStop(1, 'rgba(0,0,0,0.35)');
    octx.fillStyle = g; octx.fillRect(0, 0, LW, LH);
    octx.globalCompositeOperation = 'source-over';
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.24; ctx.drawImage(off, 0, 0); ctx.restore();
  }
  function drawDecor() {
    const n = Math.ceil(LW / REEF.w) + 2;
    REEF.decor.forEach((d, k) => {
      const m = A[d.k], fr = m.f['0_' + (Math.floor(t / 6 + k * 1.7) % 8)];
      for (let i = -n; i <= n; i++) {
        const base = ox + i * REEF.w; if (base > LW || base + REEF.w < 0) continue;
        if (i % 2 === 0) ctx.drawImage(img.atlas, fr[0], fr[1], m.w, m.h, base + d.x, d.y, m.w, m.h);
        else { ctx.save(); ctx.translate(base + REEF.w - d.x, d.y); ctx.scale(-1, 1); ctx.drawImage(img.atlas, fr[0], fr[1], m.w, m.h, 0, 0, m.w, m.h); ctx.restore(); }
      }
    });
  }
  function px(x, y, c) { ctx.fillStyle = c; ctx.fillRect(Math.round(x), Math.round(y), 1, 1); }
  function drawEels() {
    for (const e of eels) {
      const bx = ox + e.rx;
      px(bx - 1, 206, '#6b5434'); px(bx, 206, '#4a3a22'); px(bx + 1, 206, '#6b5434');      // burrow
      const h = Math.floor(e.h);
      for (let k = 0; k < h; k++) {
        const sway = Math.sin(t * 0.03 + e.p + k * 0.22) * 1.2 * (k / 14);
        const x = bx + sway, y = 205 - k;
        const spot = ((k * 7 + Math.floor(e.rx)) % 5) === 0;
        px(x, y, spot ? '#2b2b2b' : '#ece6cf'); px(x + 1, y, spot ? '#1c1c1c' : '#bdb59a');
      }
      if (h > 2) { // head bends into the current with an eye
        const sway = Math.sin(t * 0.03 + e.p + h * 0.22) * 1.2 * (h / 14);
        px(bx + sway + 2, 206 - h, '#ece6cf'); px(bx + sway + 1, 206 - h, '#0b0d12');
      }
    }
  }
  const CRAB = ['r.........r', 'rr.......rr', '.r.w...w.r.', '.rrRRRRRrr.', 'rRRRRRRRRRr', '.rRRRRRRRr.'];
  function drawCrab() {
    if (!crab) return;
    const x0 = Math.round(crab.x), y0 = 199, leg = Math.floor(crab.step / 4) % 2;
    CRAB.forEach((row, y) => { for (let x = 0; x < row.length; x++) {
      const ch = row[x]; if (ch === '.') continue;
      px(x0 + x, y0 + y, ch === 'w' ? '#0b0d12' : ch === 'R' ? '#e8452f' : '#b0281c'); } });
    for (const lx of [1, 3, 7, 9]) px(x0 + lx + ((lx + leg) % 2 ? 1 : -1) * (crab.wait > 0 ? 0 : 1) * 0, y0 + 6, '#b0281c');
    for (const lx of [0, 2, 8, 10]) px(x0 + lx + (leg ? 1 : 0), y0 + 6 + (lx % 4 === 0 ? 0 : 0), '#9a2218');
  }
  function drawSnow() {
    for (const m of snow) { ctx.fillStyle = `rgba(215,238,250,${0.18 + m.z * 0.35})`; ctx.fillRect(Math.round(m.x), Math.round(m.y), 1, 1); }
  }
  function drawSurface() {
    for (let x = 0; x < LW; x++) {
      const v = Math.sin(x * 0.31 + t * 0.09) + Math.sin(x * 0.13 - t * 0.05) + Math.sin(x * 0.07 + t * 0.02);
      if (v > 1.5) { ctx.fillStyle = 'rgba(225,248,255,0.55)'; ctx.fillRect(x, 0, 1, 1); }
      if (v > 2.1) { ctx.fillStyle = 'rgba(225,248,255,0.3)'; ctx.fillRect(x, 1, 1, 1); }
    }
  }
  function drawLight() {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 6; i++) {
      const x = ((i * 97 + t * 0.15) % (LW + 120)) - 60, a = 0.035 + 0.02 * Math.sin(t * 0.02 + i);
      ctx.fillStyle = `rgba(150,220,255,${a})`;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 14, 0); ctx.lineTo(x + 70, 170); ctx.lineTo(x + 46, 170); ctx.fill();
    }
    ctx.restore();
  }
  function draw() {
    ctx.drawImage(img.water, 0, 0, LW, LH);
    drawLight();
    for (const f of fish) if (f.depth === 2) drawSprite(f);
    drawReef();
    drawCaustics();
    drawDecor();
    drawEels();
    drawCrab();
    for (const f of fish) if (f.depth < 2) drawSprite(f);
    drawSnow();
    drawSurface();
    ctx.fillStyle = '#d9f3ff';
    for (const b of bubbles) { if (b.r) { ctx.fillRect(Math.round(b.x) - 1, Math.round(b.y), 1, 1); ctx.fillRect(Math.round(b.x) + 1, Math.round(b.y), 1, 1); ctx.fillRect(Math.round(b.x), Math.round(b.y) - 1, 1, 1); ctx.fillRect(Math.round(b.x), Math.round(b.y) + 1, 1, 1); } else ctx.fillRect(Math.round(b.x), Math.round(b.y), 1, 1); }
    for (const k of flakes) { ctx.fillStyle = k.c; ctx.fillRect(Math.round(k.x), Math.round(k.y), 1, 1); }
    for (const e of fx) {
      if (e.k === 'heart') { ctx.fillStyle = '#ff7ad9'; const x = Math.round(e.x), y = Math.round(e.y - (30 - e.life) * 0.3);
        ctx.fillRect(x - 1, y, 1, 1); ctx.fillRect(x + 1, y, 1, 1); ctx.fillRect(x - 1, y + 1, 3, 1); ctx.fillRect(x, y + 2, 1, 1); }
      if (e.k === 'grain') { ctx.fillStyle = e.water ? '#cfefff' : '#d9b77a'; ctx.fillRect(Math.round(e.x), Math.round(e.y), 1, 1); continue; }
      if (e.k === 'ripple') { ctx.strokeStyle = `rgba(220,245,255,${e.life / 40})`; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(e.x, e.y, (40 - e.life) * 1.6, 0, Math.PI * 2); ctx.stroke(); }
    }

    if (rod.st !== 'landed') drawRod();
    if (Math.abs(slosh.x) > 0.4 || Math.abs(slosh.y) > 0.4) {
      if (shot.width !== LW || shot.height !== LH) { shot.width = LW; shot.height = LH; }
      sctx.clearRect(0, 0, LW, LH); sctx.drawImage(cv, 0, 0);
      const ox_ = Math.round(slosh.x), oy_ = Math.round(slosh.y);
      ctx.drawImage(shot, ox_ - 10, oy_ - 8, LW + 20, LH + 16);
    }
    if (mode === 'ambient' && dim > 0) { ctx.fillStyle = `rgba(3,14,24,${dim})`; ctx.fillRect(0, 0, LW, LH); }
    if (rod.st === 'landed') drawRod();
  }

  // ---------------------------------------------------------------- care-mode UI
  const $ = s => document.querySelector(s);
  function hud() {
    $('#food i').style.width = state.full.toFixed(0) + '%';
    $('#joy i').style.width = state.joy.toFixed(0) + '%';
  }
  function toast(msg) { const el = $('#toast'); el.textContent = msg; el.style.opacity = 1; clearTimeout(toast.t); toast.t = setTimeout(() => el.style.opacity = 0, 2600); }
  function setMode(m) {
    mode = m; document.body.classList.toggle('care', m === 'care'); hud();
    if (m === 'care') toast(state.full < 35 ? 'The fish are hungry. Click the water to drop food.' : state.joy < 40 ? 'The fish look bored. Pick Fish and move the hook around.' : 'The tank is thriving. Say hi!');
  }
  function back() {
    save();
    if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.mq) webkit.messageHandlers.mq.postMessage({ type: 'back' });
    else setMode('ambient');
  }
  document.querySelectorAll('[data-tool]').forEach(b => b.addEventListener('click', e => {
    e.stopPropagation(); tool = b.dataset.tool; document.body.dataset.tool = tool;
    document.querySelectorAll('[data-tool]').forEach(o => o.classList.toggle('on', o === b));
  }));
  $('#back').addEventListener('click', e => { e.stopPropagation(); back(); });
  function toLogical(e) { return { x: e.clientX / scale, y: e.clientY / scale }; }
  cv.addEventListener('mousemove', e => { const p = toLogical(e); mouse.x = p.x; mouse.y = p.y; mouse.inside = true; });
  cv.addEventListener('mouseleave', () => mouse.inside = false);
  addEventListener('mouseup', () => { rod.hold = false; });
  cv.addEventListener('mousedown', e => {
    if (mode !== 'care') return;
    const p = toLogical(e);
    if (tool === 'fish') {
      if (rod.st === 'fight') rod.hold = true;
      return;
    }
    if (tool === 'feed') {
      const cols = ['#c8763a', '#e0a050', '#a85a2a', '#f0c070'];
      for (let i = 0; i < 6; i++) flakes.push({ x: p.x + rnd(-6, 6), y: rnd(3, 8), vy: rnd(0.12, 0.22), p: rnd(0, 99), life: 180, c: pick(cols) });
    } else if (tool === 'tap') {
      fx.push({ k: 'ripple', x: p.x, y: p.y, life: 40 });
      for (const e of eels) if (Math.abs(ox + e.rx - p.x) < 60) e.shy = rnd(120, 240);
      for (const f of fish) {
        if (f.depth === 2) continue;
        const dx = f.x - p.x, dy = f.y - p.y, d = Math.hypot(dx, dy) || 1;
        if (d < 75) { f.vx += dx / d * 2.2; f.vy += dy / d * 1.2; f.fear = 45; }
      }
      state.joy = clamp(state.joy - 0.4, 0, 100);
    }
  });
  addEventListener('keydown', e => {
    if (e.key === 'Escape') back();
    if (e.key === 'c' && !(window.webkit && webkit.messageHandlers && webkit.messageHandlers.mq)) setMode(mode === 'care' ? 'ambient' : 'care');
  });

  // ---------------------------------------------------------------- loop
  function resize() {
    scale = Math.max(1, innerHeight / LH);
    LW = Math.max(160, Math.ceil(innerWidth / scale));
    cv.width = LW; cv.height = LH; ctx.imageSmoothingEnabled = false;
    ox = Math.floor((LW - REEF.w) / 2);
  }
  let last = 0, acc = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    if (paused || document.hidden) { last = now; return; }
    acc += Math.min(250, now - (last || now)); last = now;
    let steps = 0;
    while (acc >= STEP && steps < 5) { update(); acc -= STEP; steps++; }
    if (steps) draw();
  }
  function start() {
    resize(); spawn(); setMode(window.__pendingMode || mode); hud();
    if (window.mqLog) mqLog('tank running ' + LW + 'x' + LH + ' at scale ' + scale.toFixed(2) + ', ' + fish.length + ' fish');
    addEventListener('resize', () => { const oldW = LW; resize(); for (const f of fish) f.x *= LW / oldW; for (const f of fish) newTarget(f); });
    requestAnimationFrame(frame);
  }
  let loaded = 0;
  for (const n of ['atlas', 'water', 'reef', 'caustics']) {
    const i = new Image(); i.onload = () => { if (++loaded === 4) start(); }; i.src = n + '.png'; img[n] = i;
  }
  addEventListener('beforeunload', save);

  // ---------------------------------------------------------------- API for the Mac app
  window.mq = {
    setMode, shake, setDim: d => { dim = clamp(+d, 0, 0.9); }, pause: p => { paused = !!p; },
    stats: () => ({ full: Math.round(state.full), joy: Math.round(state.joy) }),
    _debug: { rod, fish: () => fish, state, step: n => { for (let i = 0; i < n; i++) update(); draw(); } },
  };
})();
