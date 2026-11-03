// Astro adapter (ClientRouter). The leave animation runs in parallel with fetching the next page.
import { boot, cleanup, enter, leave, syncFlags } from './index';

let navigating = false;

export function start(setup?: () => void) {
  document.addEventListener('astro:before-preparation', (e) => {
    navigating = true;
    const load = e.loader;
    e.loader = async () => { await Promise.all([leave(), load()]); };
  });
  document.addEventListener('astro:before-swap', () => cleanup());
  document.addEventListener('astro:after-swap', () => syncFlags());
  document.addEventListener('astro:page-load', () => {
    if (!navigating) return void boot(setup);
    navigating = false;
    enter();
  });
  boot(setup);
}
