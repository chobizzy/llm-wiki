// Buttons: ink floods in from where the pointer enters. The copy button copies the install lines.
import { gsap } from 'gsap';
import { ease, isTouch, onPage, prefersReducedMotion } from '../engine';

export function startLinks() {
  onPage(() => {
    const off: (() => void)[] = [];

    document.querySelectorAll<HTMLButtonElement>('[data-copy]').forEach((btn) => {
      const label = btn.querySelector<HTMLElement>('[data-copy-label]')!;
      let timer = 0;
      const click = () => {
        const text = document.getElementById(btn.dataset.copy!)?.innerText.replace(/^\$ /gm, '').trim() ?? '';
        const done = (s: string) => { label.textContent = s; clearTimeout(timer); timer = window.setTimeout(() => (label.textContent = 'Copy'), 2000); };
        if (!navigator.clipboard) return done('Select and copy');
        navigator.clipboard.writeText(text).then(() => done('Copied'), () => done('Copy failed'));
      };
      btn.addEventListener('click', click);
      off.push(() => { btn.removeEventListener('click', click); clearTimeout(timer); });
    });

    if (isTouch() || prefersReducedMotion()) return () => off.forEach((f) => f());
    document.querySelectorAll<HTMLElement>('.btn').forEach((btn) => {
      const fill = btn.querySelector<HTMLElement>('.btn__fill');
      if (!fill) return;
      const at = (e: PointerEvent) => { const r = btn.getBoundingClientRect(); return `${e.clientX - r.left}px ${e.clientY - r.top}px`; };
      let closed = true;
      const open = (p: string) => {
        if (closed) gsap.set(fill, { clipPath: `circle(0% at ${p})` });
        closed = false;
        btn.classList.add('is-filled');
        gsap.to(fill, { clipPath: `circle(150% at ${p})`, duration: 0.55, ease: ease.soft, overwrite: true });
      };
      const close = (p: string) => {
        btn.classList.remove('is-filled');
        gsap.to(fill, { clipPath: `circle(0% at ${p})`, duration: 0.45, ease: ease.soft, overwrite: true, onComplete: () => { closed = true; } });
      };
      const enter = (e: PointerEvent) => open(at(e));
      const leave = (e: PointerEvent) => close(at(e));
      const focus = () => btn.matches(':focus-visible') && open('50% 50%');
      const blur = () => close('50% 50%');
      btn.addEventListener('pointerenter', enter); btn.addEventListener('pointerleave', leave);
      btn.addEventListener('focus', focus); btn.addEventListener('blur', blur);
      off.push(() => {
        btn.removeEventListener('pointerenter', enter); btn.removeEventListener('pointerleave', leave);
        btn.removeEventListener('focus', focus); btn.removeEventListener('blur', blur);
      });
    });
    return () => off.forEach((f) => f());
  });
}
