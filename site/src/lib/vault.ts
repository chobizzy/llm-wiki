// Build-time only. Reads the repo the site documents, so the laws, the guide, the skill list
// and the link index on screen are the ones in git, never a hand-copied version.
import fs from 'node:fs';
import path from 'node:path';
import { skillGroups, guideSummaries } from '../data/site';

export const REPO = path.resolve(process.cwd(), '..');
const read = (rel: string) => fs.readFileSync(path.join(REPO, rel), 'utf8').replace(/\r\n/g, '\n');
export const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');

// ---- Inline markdown: enough for the laws and the specimen notes ----------------------------
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
export function inline(md: string) {
  return esc(md)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

// ---- The guide: page order follows each page's own "Next:" link ------------------------------
export const guideOrder = ['architecture', 'layouts', 'configuration', 'multi-agent', 'maintenance-loops', 'trust-and-provenance'];
for (const g of guideOrder) if (!guideSummaries[g] || !fs.existsSync(path.join(REPO, 'guide', `${g}.md`))) throw new Error(`guide page or summary missing: ${g}`);
const onDisk = fs.readdirSync(path.join(REPO, 'guide')).filter((f) => f.endsWith('.md')).map((f) => f.slice(0, -3));
if (onDisk.some((g) => !guideOrder.includes(g))) throw new Error(`guide/ has pages not in guideOrder: ${onDisk}`);
export const guideSummary = (slug: string) => guideSummaries[slug];
const guideTitle = (slug: string) => read(`guide/${slug}.md`).match(/^# (.+)$/m)![1];

// ---- The constitution ------------------------------------------------------------------------
const agents = read('presets/base/AGENTS.md');
const numbered = (heading: string) => {
  const block = agents.split(/^## /m).find((s) => s.startsWith(heading))!;
  return [...block.matchAll(/^(\d+)\. (.+)$/gm)].map((m) => ({ n: +m[1], md: m[2] }));
};
export const laws = numbered('NEVER');
export const done = numbered('DONE');
if (laws.length !== 11 || done.length !== 6) throw new Error(`AGENTS.md parse: ${laws.length} laws, ${done.length} DONE items`);

/** Split "Never x. Rest." into the never-clause and the explanation. */
export const lawParts = (md: string) => {
  const i = md.search(/\.\s/);
  return i < 0 ? { head: md, rest: '' } : { head: md.slice(0, i + 1), rest: md.slice(i + 2) };
};

// Which guide page explains a law further. These become the laws page's outgoing links.
export const lawLinks: Record<number, string> = { 1: 'trust-and-provenance', 2: 'architecture', 3: 'layouts', 9: 'multi-agent', 10: 'trust-and-provenance' };

// ---- Skills: every folder in skills/ must be in exactly one group ---------------------------
const skillDirs = fs.readdirSync(path.join(REPO, 'skills')).filter((d) => fs.existsSync(path.join(REPO, 'skills', d, 'SKILL.md')));
const grouped = skillGroups.flatMap((g) => g.skills);
const missing = skillDirs.filter((s) => !grouped.includes(s));
const extra = grouped.filter((s) => !skillDirs.includes(s));
if (missing.length || extra.length || new Set(grouped).size !== grouped.length)
  throw new Error(`skillGroups out of sync with skills/: missing ${missing}, unknown ${extra}`);
export const skillCount = skillDirs.length;

// ---- The specimen: a real demo page, shown raw ---------------------------------------------
export const specimen = read('presets/demo/why-agents-need-a-constitution.md').trim();

// ---- The real vault graph (scripts/graph-svg.py writes this file) ---------------------------
export const vaultSvg = fs.readFileSync(path.resolve('src/data/vault-graph.svg'), 'utf8');
export const vaultCounts = { pages: (vaultSvg.match(/<circle/g) || []).length, links: (vaultSvg.match(/<line/g) || []).length };

// ---- This site as a vault: nodes, edges, layout ---------------------------------------------
export type Node = { id: string; title: string; label: string; href: string; x: number; y: number; r: number; lx: number; ly: number; anchor: 'start' | 'middle' | 'end' };
const titles: Record<string, string> = { home: 'llm-wiki', laws: 'The laws' };
guideOrder.forEach((s) => (titles[s] = guideTitle(s)));
const ids = ['home', 'laws', ...guideOrder];
export const hrefOf = (id: string) => (id === 'home' ? BASE : id === 'laws' ? `${BASE}laws/` : `${BASE}guide/${id}/`);

// Links written in each page. Guide pages: their markdown links. Home links to every page;
// the laws page links where lawLinks says.
const out: Record<string, string[]> = {
  home: ids.filter((i) => i !== 'home'),
  laws: [...new Set(Object.values(lawLinks))],
};
let broken = 0;
for (const s of guideOrder) {
  const targets = [...read(`guide/${s}.md`).matchAll(/\]\(([\w-]+)\.md\)/g)].map((m) => m[1]);
  broken += targets.filter((t) => !ids.includes(t)).length;
  out[s] = targets.filter((t) => ids.includes(t));
}
const edgeSet = new Set<string>();
for (const [a, ts] of Object.entries(out)) for (const b of ts) if (a !== b) edgeSet.add([a, b].sort().join('|'));
export const edges = [...edgeSet].sort().map((e) => e.split('|') as [string, string]);
const degree = Object.fromEntries(ids.map((i) => [i, edges.filter((e) => e.includes(i)).length]));
export const lint = { pages: ids.length, links: edges.length, broken, orphans: ids.filter((i) => degree[i] === 0).length };

// Fruchterman-Reingold with gravity, seeded: same graph every build (same as scripts/graph-svg.py).
function layout(seed: number) {
  let s = seed;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const C = 100;
  const pos: Record<string, number[]> = Object.fromEntries(ids.map((i) => [i, [rnd() * C, rnd() * C]]));
  const k = Math.sqrt((C * C) / ids.length) * 0.62;
  let temp = C / 8;
  for (let it = 0; it < 400; it++) {
    const d: Record<string, [number, number]> = Object.fromEntries(ids.map((i) => [i, [0, 0]]));
    for (const a of ids) for (const b of ids) {
      if (a === b) continue;
      const dx = pos[a][0] - pos[b][0], dy = pos[a][1] - pos[b][1];
      const dist = Math.hypot(dx, dy) || 0.01;
      const f = (k * k) / dist;
      d[a][0] += (dx / dist) * f; d[a][1] += (dy / dist) * f;
    }
    for (const [a, b] of edges) {
      const dx = pos[a][0] - pos[b][0], dy = pos[a][1] - pos[b][1];
      const dist = Math.hypot(dx, dy) || 0.01;
      const f = (dist * dist) / k;
      d[a][0] -= (dx / dist) * f; d[a][1] -= (dy / dist) * f;
      d[b][0] += (dx / dist) * f; d[b][1] += (dy / dist) * f;
    }
    for (const n of ids) {
      d[n][0] += (C / 2 - pos[n][0]) * 0.02; d[n][1] += (C / 2 - pos[n][1]) * 0.02;
      const t = Math.hypot(...d[n]) || 0.01, step = Math.min(t, temp);
      pos[n][0] += (d[n][0] / t) * step; pos[n][1] += (d[n][1] / t) * step;
    }
    temp *= 0.975;
  }
  // Fit into a 0..100 box with room for labels.
  const xs = ids.map((i) => pos[i][0]), ys = ids.map((i) => pos[i][1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const sx = 56 / (x1 - x0), sy = 76 / (y1 - y0); // narrower than tall: labels need the side room
  return Object.fromEntries(ids.map((i) => [i, [22 + (pos[i][0] - x0) * sx, 12 + (pos[i][1] - y0) * sy]])) as Record<string, number[]>;
}
// Graph labels stay short so they fit beside a node on a phone.
const shortLabel: Record<string, string> = { layouts: 'Layouts', 'multi-agent': 'Multi-agent', 'maintenance-loops': 'Maintenance', 'trust-and-provenance': 'Trust' };

// Pick the seed that spreads nodes furthest apart (labels need the room).
const spread = (pos: Record<string, number[]>) => {
  let m = Infinity;
  for (const a of ids) for (const b of ids) if (a < b) m = Math.min(m, Math.hypot(pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]));
  return m;
};
let placed = layout(1);
for (let seed = 2; seed <= 80; seed++) { const p = layout(seed); if (spread(p) > spread(placed)) placed = p; }

// Put each label in the widest gap between that node's edges, so it never sits on a line.
function labelSpot(id: string, r: number) {
  const [x, y] = placed[id];
  const angles = edges.filter((e) => e.includes(id)).map((e) => {
    const o = placed[e[0] === id ? e[1] : e[0]];
    return Math.atan2(o[1] - y, o[0] - x);
  }).sort((a, b) => a - b);
  let dir = 0;
  if (angles.length === 1) dir = angles[0] + Math.PI;
  else if (angles.length > 1) {
    let best = -1;
    angles.forEach((a, i) => {
      const next = i === angles.length - 1 ? angles[0] + Math.PI * 2 : angles[i + 1];
      if (next - a > best) { best = next - a; dir = a + (next - a) / 2; }
    });
  }
  const cx = Math.cos(dir), cy = Math.sin(dir), d = r + 1.6;
  return { lx: +(cx * d).toFixed(2), ly: +(cy * d + 1.2 + (cy > 0.5 ? 1.6 : 0)).toFixed(2), anchor: (cx > 0.35 ? 'start' : cx < -0.35 ? 'end' : 'middle') as Node['anchor'] };
}
const peak = Math.max(...Object.values(degree));
export const nodes: Node[] = ids.map((id) => ({
  id, title: titles[id], label: shortLabel[id] ?? titles[id], href: hrefOf(id), x: +placed[id][0].toFixed(2), y: +placed[id][1].toFixed(2),
  r: +(1.4 + 2.2 * (degree[id] / peak)).toFixed(2), ...labelSpot(id, 1.4 + 2.2 * (degree[id] / peak)),
}));
export const nodeOf = (id: string) => nodes.find((n) => n.id === id)!;
