// The signature: the persistent link index (#graph).
//   - the current page is the lit node
//   - hovering or focusing any link to a page draws the edge from here to there
//   - navigating sends a spark down that edge while a sheet of paper covers the page
//   - on home it starts large in the hero and docks into the corner as you scroll
//   - at rest the nodes drift a little and lean toward the pointer
// Everything runs on gsap.ticker. Phones and reduced motion get the static inline copies.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ease, onPage, onScroll, prefersReducedMotion, setTransition } from '../engine';

type N = { id: string; g: SVGGElement; a: SVGAElement; c: SVGCircleElement; hit: SVGCircleElement; t: SVGTextElement; bx: number; by: number; x: number; y: number; ph: number; lx: number; ly: number };
type E = { el: SVGLineElement; a: string; b: string };

const desktop = () => matchMedia('(min-width: 1024px)').matches;
const norm = (p: string) => p.replace(/\/?$/, '/');

let root: HTMLElement;
let svg: SVGSVGElement;
let probe: SVGLineElement;
let spark: SVGCircleElement;
const nodes = new Map<string, N>();
const edges: E[] = [];
let current = '';
let hot = '';
let tweening = false;
const pose = { x: 0, y: 0, s: 1, h: 0 }; // h: 1 in the hero, 0 in the dock
const lean = { x: 0, y: 0, ax: 0, ay: 0 };
let dest: string | null = null; // node id the next navigation goes to

function collect() {
  root = document.getElementById('graph')!;
  svg = root.querySelector('svg')!;
  probe = svg.querySelector('.lg__probe')!;
  spark = svg.querySelector('.lg__spark')!;
  svg.querySelectorAll<SVGGElement>('.lg__node').forEach((g, i) => {
    const bx = +g.dataset.x!, by = +g.dataset.y!;
    const t = g.querySelector('text')!;
    nodes.set(g.dataset.id!, { id: g.dataset.id!, g, a: g.querySelector('a')!, c: g.querySelector('.lg__dot')!, hit: g.querySelector('.lg__hit')!, t, bx, by, x: bx, y: by, ph: i * 1.7, lx: +g.dataset.lx!, ly: +g.dataset.ly! });
  });
  svg.querySelectorAll<SVGLineElement>('.lg__edge').forEach((el) => edges.push({ el, a: el.dataset.a!, b: el.dataset.b! }));
}

const nodeFor = (href: string) => {
  try {
    const u = new URL(href, location.href);
    if (u.origin !== location.origin) return null;
    const p = norm(u.pathname);
    for (const n of nodes.values()) if (norm(new URL(n.a.getAttribute('href')!, location.href).pathname) === p) return n.id;
  } catch { /* not a URL */ }
  return null;
};

function setCurrent(id: string) {
  current = id;
  nodes.forEach((n) => {
    n.g.classList.toggle('is-current', n.id === id);
    if (n.id === id) n.a.setAttribute('aria-current', 'page');
    else n.a.removeAttribute('aria-current');
  });
}

// ---- Geometry: draw nodes, edges, probe at their (drifting) positions ----------------------
function draw() {
  nodes.forEach((n) => {
    const x = n.x.toFixed(2), y = n.y.toFixed(2);
    n.c.setAttribute('cx', x); n.c.setAttribute('cy', y); n.hit.setAttribute('cx', x); n.hit.setAttribute('cy', y);
    n.t.setAttribute('x', (n.x + n.lx).toFixed(2)); n.t.setAttribute('y', (n.y + n.ly).toFixed(2));
  });
  for (const e of edges) {
    const A = nodes.get(e.a)!, B = nodes.get(e.b)!;
    e.el.setAttribute('x1', A.x.toFixed(2)); e.el.setAttribute('y1', A.y.toFixed(2));
    e.el.setAttribute('x2', B.x.toFixed(2)); e.el.setAttribute('y2', B.y.toFixed(2));
  }
  if (hot && current) {
    const A = nodes.get(current)!, B = nodes.get(hot)!;
    probe.setAttribute('x1', A.x.toFixed(2)); probe.setAttribute('y1', A.y.toFixed(2));
    probe.setAttribute('x2', B.x.toFixed(2)); probe.setAttribute('y2', B.y.toFixed(2));
  }
}

function idleTick(t: number) {
  if (!desktop()) return;
  const k = 1 - Math.pow(0.94, gsap.ticker.deltaRatio());
  lean.x += (lean.ax - lean.x) * k; lean.y += (lean.ay - lean.y) * k;
  nodes.forEach((n) => {
    // A slow orbit of about one unit, plus a lean toward the pointer that grows with distance from centre.
    n.x = n.bx + Math.sin(t * 0.45 + n.ph) * 0.9 + lean.x * (n.bx - 50) * 0.05;
    n.y = n.by + Math.cos(t * 0.38 + n.ph * 1.3) * 0.9 + lean.y * (n.by - 50) * 0.05;
  });
  draw();
}

// ---- Placement: hero slot on home, corner dock everywhere else ------------------------------
let heroRect: { right: number; bottom: number; width: number } | null = null;
function measureHero() {
  const slot = document.querySelector<HTMLElement>('.hero__graph-slot');
  if (!slot) return (heroRect = null);
  const r = slot.getBoundingClientRect();
  heroRect = { right: r.right, bottom: r.bottom + scrollY, width: r.width };
}

function apply(x: number, y: number, s: number, h: number) {
  pose.x = x; pose.y = y; pose.s = s; pose.h = h;
  gsap.set(root, { x, y, scale: s });
  const w = svg.getBoundingClientRect().width / s || 220; // unscaled width of the drawing
  const unit = (w * s) / 100;                                // screen px per SVG unit
  svg.style.setProperty('--sw', (1 / unit).toFixed(3));
  svg.style.setProperty('--fs', `${(gsap.utils.interpolate(11.5, 15, h) / unit).toFixed(3)}px`);
  root.classList.toggle('is-hero', h > 0.5);
  svg.classList.toggle('lg--labels', h > 0.5);
}

function targetPose(scrollY: number) {
  if (!heroRect) return { x: 0, y: 0, s: 1, h: 0 };
  const w = svg.getBoundingClientRect().width / pose.s;
  const S = heroRect.width / w;
  const gut = parseFloat(getComputedStyle(root).right) || 24;
  const R = innerWidth - gut, B = innerHeight - gut;
  const dx = heroRect.right - R, dy = heroRect.bottom - B;
  const p = gsap.utils.clamp(0, 1, scrollY / (innerHeight * 0.75));
  const e = gsap.parseEase('power2.inOut')(p);
  return { x: dx * (1 - e), y: dy * (1 - e), s: 1 + (S - 1) * (1 - e), h: 1 - e };
}

const settle = (animate: boolean) => {
  const t = targetPose(scrollY);
  if (!animate || prefersReducedMotion()) return apply(t.x, t.y, t.s, t.h);
  tweening = true;
  const from = { ...pose };
  gsap.to(from, { ...t, duration: 1, ease: ease.inOut, overwrite: true, onUpdate: () => apply(from.x, from.y, from.s, from.h), onComplete: () => { tweening = false; } });
};

// ---- Hover: draw the edge from here to the link's page --------------------------------------
function showProbe(id: string) {
  if (id === hot) return;
  hideProbe(true);
  if (!current || id === current) return;
  hot = id;
  nodes.get(id)!.g.classList.add('is-hot');
  edges.forEach((e) => e.el.classList.toggle('is-hot', (e.a === current && e.b === id) || (e.b === current && e.a === id)));
  draw();
  if (prefersReducedMotion()) return void gsap.set(probe, { opacity: 1, strokeDasharray: 'none' });
  const A = nodes.get(current)!, B = nodes.get(id)!;
  const len = Math.hypot(B.x - A.x, B.y - A.y);
  gsap.fromTo(probe, { opacity: 1, strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.45, ease: ease.out, overwrite: true });
}
function hideProbe(now = false) {
  if (!hot) return;
  nodes.get(hot)?.g.classList.remove('is-hot');
  edges.forEach((e) => e.el.classList.remove('is-hot'));
  hot = '';
  gsap.to(probe, { opacity: 0, duration: now ? 0 : 0.25, overwrite: true });
}

function wireHover() {
  const over = (e: Event) => {
    const a = (e.target as Element).closest?.('a[href]');
    if (!a) return;
    const id = nodeFor(a.getAttribute('href')!);
    if (id) showProbe(id);
  };
  const out = (e: Event) => {
    const a = (e.target as Element).closest?.('a[href]');
    const to = (e as PointerEvent).relatedTarget as Element | null;
    if (a && to && a.contains(to)) return;
    hideProbe();
  };
  document.addEventListener('pointerover', over);
  document.addEventListener('pointerout', out);
  document.addEventListener('focusin', over);
  document.addEventListener('focusout', out);
}

// ---- Navigation: spark down the edge, paper over the page -----------------------------------
function wireTransition() {
  document.addEventListener('astro:before-preparation', (e) => {
    dest = nodeFor((e as unknown as { to: URL }).to.href);
  });
  const panel = () => document.querySelector<HTMLElement>('.curtain__panel')!;
  const curtain = () => document.getElementById('curtain')!;
  setTransition({
    leave: async () => {
      hideProbe(true);
      const title = curtain().querySelector<HTMLElement>('[data-curtain-title]')!;
      title.textContent = dest ? nodes.get(dest)!.a.getAttribute('aria-label') : 'Page not found';
      if (prefersReducedMotion()) {
        await gsap.timeline().set(curtain(), { autoAlpha: 1 }).set(panel(), { yPercent: 0 }).fromTo(curtain(), { opacity: 0 }, { opacity: 1, duration: 0.2 });
        return;
      }
      const tl = gsap.timeline();
      tl.set(curtain(), { autoAlpha: 1, opacity: 1 })
        .fromTo(panel(), { yPercent: 100 }, { yPercent: 0, duration: 0.75, ease: ease.inOut }, 0)
        .fromTo(title.parentElement!.querySelectorAll('.wl__b'), { x: (i: number) => (i ? 24 : -24), opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: ease.out }, 0.4);
      if (dest && current && dest !== current && desktop()) {
        const A = nodes.get(current)!, B = nodes.get(dest)!;
        const p = { t: 0 };
        tl.set(spark, { opacity: 1, attr: { cx: A.x, cy: A.y } }, 0)
          .to(p, { t: 1, duration: 0.7, ease: ease.inOut, onUpdate: () => {
            const a = nodes.get(current)!, b = nodes.get(dest!)!;
            spark.setAttribute('cx', String(a.x + (b.x - a.x) * p.t));
            spark.setAttribute('cy', String(a.y + (b.y - a.y) * p.t));
          } }, 0.05);
      }
      await tl;
    },
    enter: async () => {
      const id = document.documentElement.dataset.page || '';
      setCurrent(nodes.has(id) ? id : '');
      gsap.to(spark, { opacity: 0, duration: 0.3 });
      measureHero();
      if (desktop()) settle(true);
      if (prefersReducedMotion()) { await gsap.to(curtain(), { autoAlpha: 0, duration: 0.2 }); return; }
      await gsap.timeline()
        .to(panel(), { yPercent: -100, duration: 0.85, ease: ease.inOut })
        .set(curtain(), { autoAlpha: 0 });
    },
  });
}

export function startIndexGraph() {
  if (!document.getElementById('graph')) return;
  collect();
  const id = document.documentElement.dataset.page || '';
  setCurrent(nodes.has(id) ? id : '');
  wireHover();
  wireTransition();
  measureHero();
  settle(false);
  onScroll(({ y }) => { if (!tweening && heroRect && desktop()) { const t = targetPose(y); apply(t.x, t.y, t.s, t.h); } });
  addEventListener('resize', () => { measureHero(); if (!tweening) settle(false); }, { passive: true });
  if (!prefersReducedMotion()) {
    addEventListener('pointermove', (e) => { lean.ax = e.clientX / innerWidth - 0.5; lean.ay = e.clientY / innerHeight - 0.5; }, { passive: true });
    gsap.ticker.add(idleTick);
  }
  // The index steps aside when the footer arrives, so it never sits on the footer's rule.
  onPage(() => {
    const foot = document.querySelector('.site-footer');
    if (!foot) return;
    ScrollTrigger.create({ trigger: foot, start: 'top 85%', onToggle: (s) => gsap.to(root, { autoAlpha: s.isActive ? 0 : 1, duration: 0.4, overwrite: 'auto' }) });
    return () => gsap.set(root, { autoAlpha: 1 });
  });
  // Inline copies (phones, hero fallback): draw their edges in when the page arrives.
  onPage(({ intro }) => {
    if (prefersReducedMotion()) return;
    const lines = [...document.querySelectorAll<SVGLineElement>('#main .lg__edge, .li-foot .lg__edge')];
    if (!lines.length) return;
    lines.forEach((l) => l.setAttribute('pathLength', '1'));
    intro.add(gsap.fromTo(lines, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.9, stagger: 0.04, ease: ease.out }), 0.2);
  });
}
