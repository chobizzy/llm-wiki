# Landing page art

Seven decorative illustrations for `docs/index.html`. **These are AI-generated
images**, produced with a text-to-image model and committed here so the page
makes no third-party requests.

They are decoration, not documentation. Nothing in them is a screenshot, a
measurement, or a claim about how llm-wiki behaves. The one visual on the page
that *is* real data is the link graph, which `scripts/graph-svg.py` draws from an
actual vault.

| File | Section | Depicts |
| --- | --- | --- |
| `hero.webp` | Hero | Paper fragments drawn into an aperture, a crystalline column rising out |
| `compile.webp` | #1 Compile | Shredded scraps entering a press, aligned sheets leaving it |
| `govern.webp` | #2 Govern | A stacked stone monolith on a plinth |
| `ingest.webp` | #3 Ingest | Sealed archive boxes, one open and lit |
| `link.webp` | #4 Link | A lattice of illuminated nodes and filaments |
| `verify.webp` | #5 Verify | A slotted gate: a clean sheet passes, crumpled ones are stopped |
| `own.webp` | #6 Own | A card catalog drawer pulled open |

## Constraints these files have to meet

The page composites them with `mix-blend-mode: screen` over the flood colour.
Screen maps black to the backdrop and white to white, so art has to be
**grayscale on a near-black ground** or it will sit in a visible rectangle
instead of dissolving into the page.

That is measured rather than eyeballed: the outer 24px frame of each image is
averaged, and anything above roughly 40/255 reads as a lit box.

Measuring alone was not enough. These were shot against studio backdrops, which
photograph as mid-grey, so the whole field lifted and the tiles read as lit
rectangles no matter how far the borders were feathered. The fix is a black-point
crush at 84/255 with a soft shoulder, applied before export: the backdrop drops
to true zero, where screen leaves the flood untouched, while paper and highlights
survive. It made the pictures more dramatic as a side effect.

Edge luminance after the crush: four files at 0.0, the rest at 0.1 to 6.5.

Also enforced:

- Grayscale, `L` mode, so no stray colour survives the blend.
- Longest edge 1200px, WebP quality 80.
- No lettering. Generated text is meaningless and would read as a fake caption.

## Regenerating

There is no script for this: the images are fixed assets, not derived data. To
replace one, generate a grayscale image on a black ground, downscale it to
1200px, save as WebP, and check the edge luminance before committing.
