// Engine core: page lifecycle. No DOM access at import time.
//   boot(setup) once, then leave() → cleanup() → enter() per navigation.
// onPage(fn) runs on every page load inside a gsap.context; return a cleanup for the rest.
// Transitions are not here: the link index owns them (src/motion/index-graph.ts).
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { initScroll, resetScroll, startScroll, stopScroll } from './scroll';
import { initReveals } from './reveal';
import { prefersReducedMotion } from './env';

export { onScroll, scrollState, stopScroll, startScroll } from './scroll';
export { ease, isTouch, isMobile, prefersReducedMotion } from './env';

export type Transition = { leave: () => Promise<unknown>; enter: () => Promise<unknown> };
let transition: Transition = { leave: async () => {}, enter: async () => {} };
export const setTransition = (t: Transition) => { transition = t; };

export type PageFn = (page: { intro: gsap.core.Timeline; path: string }) => void | (() => void);
const pageFns = new Set<PageFn>();
const cleanups: (() => void)[] = [];
let ctx: gsap.Context | null = null;
let intro: gsap.core.Timeline | null = null;
let ready = false;
let booted = false;

/** Run fn on every page load (and now, if a page is ready). Returns an unsubscribe. */
export function onPage(fn: PageFn) {
  pageFns.add(fn);
  if (ready) runPageFn(fn);
  return () => { pageFns.delete(fn); };
}

function runPageFn(fn: PageFn) {
  ctx?.add(() => {
    const c = fn({ intro: intro!, path: location.pathname });
    if (typeof c === 'function') cleanups.push(c);
  });
}

// Flags on <html>, re-applied on every page because Astro swaps root attributes.
export function syncFlags() {
  const h = document.documentElement.classList;
  h.add('js', 'is-booted', 'is-loaded');
  h.toggle('motion', !prefersReducedMotion());
}

function initPage() {
  syncFlags();
  ctx = gsap.context(() => { intro = initReveals(document); });
  ready = true;
  pageFns.forEach(runPageFn);
  requestAnimationFrame(() => ScrollTrigger.refresh());
}

export function boot(setup?: () => void) {
  if (booted) return;
  booted = true;
  syncFlags();
  initScroll();
  setup?.();
  initPage();
  startScroll();
  intro?.play();
}

export async function leave() {
  stopScroll();
  await transition.leave();
}

/** Revert every tween, ScrollTrigger and split of the current page. */
export function cleanup() {
  if (!ready) return;
  ready = false;
  cleanups.splice(0).forEach((c) => c());
  ctx?.revert();
  ctx = null;
}

export async function enter({ scrollTop = true } = {}) {
  if (!booted) return;
  cleanup();
  if (scrollTop) resetScroll();
  initPage();
  const lift = transition.enter();
  gsap.delayedCall(0.3, () => intro?.play()); // the new page draws in while the sheet lifts
  await lift;
  startScroll();
}
