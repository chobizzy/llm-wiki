// Home only: the DONE contract ticks as each condition reaches the reading line,
// and the real vault's links draw themselves in as its section scrolls through.
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { onPage, prefersReducedMotion } from '../engine';

export function startHome() {
  onPage(() => {
    if (prefersReducedMotion()) return;

    document.querySelectorAll<HTMLElement>('[data-done] li').forEach((li) => {
      const box = li.querySelector<HTMLElement>('.done__box')!;
      const tick = (on: boolean) => { box.textContent = on ? '[x]' : '[ ]'; li.classList.toggle('is-done', on); };
      ScrollTrigger.create({ trigger: li, start: 'top 62%', end: 'max', onEnter: () => tick(true), onLeaveBack: () => tick(false) });
    });

    const vault = document.querySelector<SVGSVGElement>('[data-vault] svg');
    if (vault) {
      const lines = [...vault.querySelectorAll<SVGLineElement>('line')];
      const dots = vault.querySelectorAll('circle');
      lines.forEach((l) => l.setAttribute('pathLength', '1'));
      gsap.timeline({ scrollTrigger: { trigger: vault, start: 'top 80%', end: 'bottom 45%', scrub: 0.6 } })
        .fromTo(dots, { scale: 0, transformOrigin: '50% 50%' }, { scale: 1, stagger: 0.02, ease: 'none', duration: 0.3 }, 0)
        .fromTo(lines, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, stagger: 0.008, ease: 'none', duration: 0.3 }, 0.1);
      const count = document.querySelector<HTMLElement>('[data-vault-links]');
      if (count) {
        const total = +count.textContent!;
        const o = { v: 0 };
        gsap.to(o, { v: total, ease: 'none', scrollTrigger: { trigger: vault, start: 'top 70%', end: 'bottom 45%', scrub: 0.6 }, onUpdate: () => (count.textContent = String(Math.round(o.v))) });
      }
    }
  });
}
