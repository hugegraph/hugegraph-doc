# Homepage design QA

Date: 2026-11-15 (Asia/Singapore).

## Scope and visual truth

The selected transition reference is the task image
`/workspace/generated_images/exec-da63ee44-1442-41c5-b2c5-e337f24343fd.png`
(1254 × 1254 pixels). The supplied D5 HTML is the source of the interactive
stack, graph evolution and camera timeline. The user explicitly requested that
the first viewport remain a complete hero, that later content appear on scroll,
and that the gradual graph changes remain intact.

This PR applies the chosen blue → pale-blue → near-white surface and fixes the
confirmed usability defects. The concept's compressed document composition is
not a requirement to expose the next section in the initial viewport. Native
OINK navigation, language, appearance, search, versions and AI consent remain in
place; the diagram remains live instead of becoming a raster illustration.

## Evidence and normalization

- Browser: Chromium; viewport 1440 × 1000 CSS pixels, deviceScaleFactor 1.
  Additional captures: 390 × 844, 320 × 844 and 844 × 390; both EN and CN.
- Full-view comparison: `/workspace/landing-review/design-comparison.png` puts
  the selected source and the actual hero/exit states in one comparison input.
  Both sides use equal display widths; the source's composite document and the
  runtime's separate scroll states are labelled. No pixel-difference claim is
  made across those intentionally different compositions.
- Focused evidence: four layer labels at 320/390px and 844 × 390; stopped
  Database/Computing/Storage/AI panels; the exit gradient; native Print media.
- [Before desktop](tests/e2e/screenshots/landing/before-en-1440.jpg) /
  [after desktop](tests/e2e/screenshots/landing/after-en-1440.jpg).
- [Before 320px](tests/e2e/screenshots/landing/before-en-320.jpg) /
  [after 320px](tests/e2e/screenshots/landing/after-en-320.jpg).
- [Chinese](tests/e2e/screenshots/landing/after-cn-1440.jpg),
  [progressive graph](tests/e2e/screenshots/landing/after-storage.jpg),
  [exit transition](tests/e2e/screenshots/landing/after-transition.jpg).
- Real browser recording: `/workspace/landing-review/animation.webm` (15 s).

## Comparison history and fixes

1. Initial integration had inherited section padding, clipped mobile labels,
   and a selector-specificity error hiding the text veil and story navigation.
   Reset the authored story padding, restore label geometry, and use a
   low-specificity initial hidden rule. Fresh captures confirm a complete first
   viewport, four visible layer names and readable text over the moving graph.
2. Native Print retained the pinned scene and hid its inactive explanations.
   Print now uses natural flow, exposes all four explanations and hides the
   animated canvas/controls. Browser Print-media inspection confirms all four
   panels have opacity 1 and visible text, with a static stage and white ground.
3. The small-screen AI launcher overlapped the restored layer legend. Its
   homepage-only position now uses the safe bottom edge; the final 390px capture
   shows separated hit areas. Documentation pages retain their existing layout.
4. A flat text veil introduced a color seam at the scene exit. The veil now
   masks the same blue gradient as the scene; the 240px desktop / 128px mobile
   transition blends into the reading surface without changing text opacity.

## Required fidelity surfaces

- **Fonts and typography:** retain the site's Inter heading and native body
  stacks, with a 700-weight display heading, readable body copy and localized
  Chinese fallbacks. Hero wrapping and controls remain readable at tested sizes.
  This deliberately reuses site fonts instead of embedding prototype fonts.
- **Spacing and rhythm:** complete initial viewport; aligned copy, diagram and
  downstream sections; all layer names fit on narrow and short screens. The
  chosen pale section begins only after the preserved progressive story.
- **Colors and tokens:** vivid violet/blue scene, white primary action, fixed
  semantic layer colors and pale reading surface. Dark appearance retains the
  blue scene and uses the native dark reading background.
- **Image and diagram quality:** existing brand assets and icon library are
  reused. The supplied live vector/canvas geometry is retained for real graph
  morphing, with consistent material and semantic accents. A static generated
  diagram would remove functionality explicitly required by the user.
- **Copy and content:** EN/CN cover every new visible section and feedback state.
  Components link to their own guides; the command matches the Server guide and
  offers the next step. Semantic Markdown and native printing retain content.

## Interaction verification

The new browser regressions cover first-viewport CTA/section placement, genuine
language navigation and persistence, eight component destinations, complete
clipboard content/status, reduced motion, 320px drawer reachability/Escape/focus,
visible layer names including landscape, and distinct nonempty graph frames
with one readable explanation at every sampled stop. Native theme, search and
AI enabled/disabled fixtures are checked by the existing browser suites.

Independent review confirmed the fixes. The actual Hugo runtime recording also
verified hero → lift-off → Database → Computing → Storage → AI, localized
Chinese counts, dark appearance and reduced-motion canvases, without page errors
or failed main-page requests. All assets load locally; the new runtime does not
make third-party requests. Native AI consent behavior is unchanged.

## Follow-up polish and limits

- Per-layer internal glyph composition can be refined in a later visual review;
  this PR preserves the reviewed interactive geometry and timeline.
- Device checks use Chromium emulation, not real-device Safari or a complete
  screen-reader certification.

## Implementation checklist

- [x] Keep the complete blue first viewport and progressive graph story.
- [x] Apply the selected transition after the story.
- [x] Fix text overlap, narrow/short viewport failures and layer-label clipping.
- [x] Reuse native language, theme, navigation and consent controls.
- [x] Add component guide links, copy feedback and the next action.
- [x] Preserve bilingual Markdown, reduced motion and native printing.
- [x] Compare source and rendered evidence; resolve actionable P1/P2 findings.

final result: passed
