// Rehype plugin for guide/*.md: rewrite `x.md` links to the site's guide routes (and the
// README link to GitHub), and hang `##` markdown syntax in the margin of h2/h3.
const REPO = 'https://github.com/chobizzy/llm-wiki';

export default function rehypeGuide({ base }) {
  const walk = (node, fn) => { fn(node); (node.children || []).forEach((c) => walk(c, fn)); };
  return (tree) => {
    // The page head renders the title as the page's only <h1>; drop the markdown's own.
    const i = tree.children.findIndex((c) => c.type === 'element' && c.tagName === 'h1');
    if (i > -1) tree.children.splice(i, 1);
    const text = (n) => (n.value ?? '') + (n.children || []).map(text).join('');
    const els = tree.children.filter((c) => c.type === 'element');
    const last = els[els.length - 1];
    if (last?.tagName === 'p' && /^(Next|Back to):/.test(text(last).trim())) tree.children.splice(tree.children.indexOf(last), 1);
    walkAll(tree);
  };
  function walkAll(tree) { walk(tree, (n) => {
    if (n.type !== 'element') return;
    if (n.tagName === 'a' && typeof n.properties.href === 'string') {
      const href = n.properties.href;
      const m = href.match(/^([\w-]+)\.md(#.*)?$/);
      if (m) {
        n.properties.href = `${base}guide/${m[1]}/${m[2] || ''}`;
        n.properties.dataNode = m[1];
      } else if (/README\.md$/.test(href)) n.properties.href = `${REPO}#readme`;
    }
    if (n.tagName === 'h2' || n.tagName === 'h3') {
      n.children.unshift({
        type: 'element', tagName: 'span',
        properties: { className: ['md-hash'], ariaHidden: 'true' },
        children: [{ type: 'text', value: n.tagName === 'h2' ? '## ' : '### ' }],
      });
    }
    if (n.tagName === 'table' && !n.wrapped) {
      // Wide tables scroll inside their own box on phones.
      const copy = { ...n, wrapped: true };
      n.tagName = 'div';
      n.properties = { className: ['table-scroll'], tabIndex: 0, role: 'region', ariaLabel: 'Table' };
      n.children = [copy];
    }
  });
}
}
