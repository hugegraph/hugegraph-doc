# Ask AI Visual Directions

- Method: built-in `image_gen`
- Asset:
  `evidence/ask-ai-visual-directions.png`
- Dimensions: 1717×916 PNG
- SHA-256:
  `68a97ffa93941608fa6d112e77331e464df59a824b8073ebf1c5543a472c98c2`

## Directions

1. Search Tail — append one Ask AI action after native results for a non-empty
   ordinary query.
2. Floating Launcher — keep a global compact launcher that opens the AI modal
   without submitting a query.
3. Side Panel — reserve a persistent right-side assistant surface.

## Selection

Use Search Tail and Floating Launcher as two entrypoints into one shared modal
and state machine. Do not adopt the persistent Side Panel because it competes
with the document TOC and reduces content width. Native summary results remain
the primary surface in every state.

The old red/pink Docusaurus treatment is explicitly excluded. The selected
surface uses the OINK/HugeGraph purple token in light and dark modes.

## Generation prompt

```text
Use case: ui-mockup
Asset type: design-review comparison board for a documentation website
Primary request: create one polished landscape comparison board showing three clearly separated Ask AI interface directions for the Apache HugeGraph OINK documentation site.
Scene/backdrop: clean off-white product-design review canvas with a restrained header and three equal desktop UI panels.
Subject: Panel A shows an AI action appended as the final row of native documentation search results; Panel B shows a compact floating Ask AI launcher opening a centered modal; Panel C shows a right-side assistant panel beside documentation content. Each panel should visibly preserve native local search as the primary interface.
Style/medium: realistic shippable web product UI mockup, crisp and restrained, not concept art.
Composition/framing: 16:9 landscape, three equal columns, consistent browser chrome, strong comparison hierarchy, generous whitespace.
Color palette: OINK/HugeGraph purple #532FC9 with neutral white, charcoal, soft lavender, and a credible dark-mode inset; strictly no red or pink legacy UI.
Text (verbatim): "HugeGraph", "A · Search Tail", "B · Floating Launcher", "C · Side Panel", "Search documentation", "Ask AI", "Native results stay available".
Constraints: render the listed text exactly once where appropriate; preserve accessibility-minded contrast; use modest borders and 10–12px rounding; no gradients, no glassmorphism, no decorative blobs, no unrelated logos, no watermark, no red, no pink, no extra marketing copy.
```
