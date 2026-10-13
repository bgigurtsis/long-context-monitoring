# Screenshots and Diagrams

**Version:** v1.1.0
**Owner:** Developer Experience (Priya Nair)
**Last updated:** 2024-10-11

## Summary

This page covers image sizing, alt text, and diagram labeling conventions for illustrating how pieces of the package and the service fit together. If you're adding a terminal capture, a window screenshot, or a box-and-arrow diagram to any page under docs/, the conventions here apply. This is the only page in docs-style/ that deals with visual assets specifically — voice-and-tone.md and markdown-conventions.md cover prose and structure, but neither says anything about images, so treat this page as the source of truth for anything you'd embed with an `![]()` tag.

## Why this page exists

Screenshots and diagrams rot faster than prose. A terminal capture showing the shell prompt style from two laptops ago, a diagram with a box labeled with a term the glossary no longer uses, a PNG that's 4000px wide and blows out the layout on a phone — these are the recurring complaints in doc reviews. Priya Nair put this page together after the Q2 2024 review cycle turned up eleven stale screenshots across six pages. The goal isn't to make images pretty. It's to make them replaceable without archaeology.

## Coverage

This page applies to:

- Terminal/shell capture screenshots showing CLI-style output panes
- Screenshots of the loopback service responding in a browser or in an HTTP request tool
- Diagrams showing how the package's pieces relate to each other (component diagrams, sequence-style flow diagrams, folder/file diagrams)
- Any embedded image in a page under docs/, including this docs-style/ folder itself

It does not apply to inline code blocks (see code-block-standards.md) or to plain-text file tree listings, which should stay as text, not screenshots, per markdown-conventions.md.

## When to use a screenshot vs. a diagram vs. nothing

Not every concept needs a picture. Use this rough guideline list:

1. If the reader needs to recognize what something looks like on their own screen (an error dialog, a specific pane layout) → screenshot.
2. If the reader needs to understand how components relate, or a sequence of steps across more than two actors → diagram.
3. If the concept is a single command's output and the output is short (under ~15 lines) → prefer a code block over a screenshot. Screenshots of short text output are almost always unnecessary and go stale faster than the text they replace.
4. If you're documenting a folder layout or file relationships → text tree in a code block, not a screenshot.

Owner note (Priya Nair): I still see people screenshot a config file's contents instead of pasting the text. Don't do that. If it's text, it goes in a code block.

## Image sizing

**Section owner: Priya Nair**

Screenshots should be captured and cropped to a maximum of 1200px wide. Anything wider gets scaled down awkwardly by our renderer and text inside the screenshot becomes unreadable on a laptop screen at 100% zoom.

| Asset type | Max width | Max height | Notes |
|---|---|---|---|
| Terminal capture | 1000px | 700px | Crop trailing blank lines; don't capture the whole terminal window chrome |
| Browser/HTTP request screenshot | 1200px | 900px | Crop browser chrome unless the chrome itself is relevant |
| Component diagram | 1200px | no hard limit | Tall diagrams should be split into two images rather than shrunk |
| Sequence/flow diagram | 1100px | 1000px | Prefer landscape orientation |

Steps to resize on macOS or Linux without a paid tool:

1. Take the capture at native resolution.
2. Open a shell and check the current dimensions:
   ```
   sips -g pixelWidth -g pixelHeight capture.png
   ```
3. Resize to the target width, keeping aspect ratio:
   ```
   sips --resampleWidth 1000 capture.png
   ```
4. On Linux, the equivalent with ImageMagick:
   ```
   convert capture.png -resize 1000x capture-resized.png
   ```
5. Re-check dimensions before committing. If height still exceeds the max in the table above, crop rather than squash — squashing distorts text.

File format: PNG for screenshots (lossless, text stays crisp), SVG for diagrams where the diagramming tool supports export to SVG. Avoid JPEG; compression artifacts make small terminal text blurry.

## Alt text

**Section owner: Priya Nair**

Every embedded image needs alt text. This isn't optional and it isn't a one-line afterthought — alt text is read by screen readers and also shows up as a tooltip and in broken-image fallback, so it has to actually describe content, not just repeat the filename.

Bad alt text:
```
![screenshot](img/shot1.png)
```

Better:
```
![Terminal window showing the record count after a lookup, with the count printed on the last line](img/lookup-count-2024-09.png)
```

Guidelines for alt text:

- Describe what the image shows, not why you included it. "Diagram of the package's three components" is fine; "diagram explaining the architecture" is vague.
- Keep it under ~125 characters where possible. Screen readers will read all of it, so don't write a paragraph.
- For diagrams, name the components shown, in the order they appear left-to-right or top-to-bottom.
- For screenshots, mention the pane or window type and the one detail that matters (a count, a status word, a shape of output) — not every pixel.
- Don't start with "Image of" or "Screenshot of" redundantly if the surrounding image markdown or caption already says so; but if there's no caption, do include that framing word.

Caption vs. alt text: alt text is for accessibility and must always be present. A caption (a line of italic text below the image) is optional and used when you want to add commentary that isn't strictly a description, e.g. *Captured on the September 2024 build; loopback service running on the default local port.*

## Diagram labeling conventions

**Section owner: Priya Nair**

Diagrams in the docs generally show one of three things: how the CLI tool, the loopback service, and the database file relate to each other; a sequence of steps a request or a record takes through the package; or a folder/file layout (though as noted above, folder layouts are usually better as text).

Labeling rules:

1. **Box labels are nouns, not verbs.** Label a box "Database file" not "Storing records."
2. **Use the same term the glossary uses.** If terminology-glossary.md calls something "the service," don't label a diagram box "HTTP server" — pick one term and match it. This is the single most common diagram bug we catch in review: a diagram drawn in 2025 using a term that's since been superseded in the glossary.
3. **Arrows get short labels, not sentences.** "reads from," "writes to," "starts" — three words max.
4. **Number sequence steps if order matters.** Use small numbered circles or numbered labels (1, 2, 3) rather than relying on arrow direction alone; readers scanning quickly miss directionality.
5. **One diagram, one idea.** If you're tempted to show both the component relationships and a sequence of steps in the same image, split it into two diagrams.
6. **Color is decoration, not information.** Never rely on color alone to distinguish elements — some readers view docs in grayscale or have color vision differences. Pair color with a label or shape difference.
7. **Include a one-line title inside the diagram image itself**, top-left, restating what the diagram shows. This helps when the image is viewed outside its page context (e.g., pasted into a support message).

### Worked example: component diagram

A minimal text description of what a compliant component diagram should contain (the actual image is drawn in a diagramming tool, not in markdown):

```
Title: How the package's pieces fit together

[Command-line tool] --invokes--> [Package core]
[Package core] --reads/writes--> [Database file]
[Loopback service] --reads/writes--> [Database file]
[Command-line tool] and [Loopback service] both sit above [Package core]
```

Box labels: "Command-line tool," "Package core," "Database file," "Loopback service" — these four terms should match exactly what's defined in the glossary section below and in terminology-glossary.md.

### Worked example: sequence diagram

```
Title: Sequence when a record is written

1. Caller invokes the command-line tool
2. Command-line tool calls into the package core
3. Package core opens the database file
4. Package core writes the record
5. Package core closes the database file
6. Command-line tool prints a confirmation line
```

Each numbered step becomes one labeled arrow or box in the actual diagram. Don't compress steps 3–5 into one box just to save space; readers use this diagram to understand ordering, and collapsing steps defeats the purpose.

## File naming and storage

**Section owner: Priya Nair**

Store image assets under `docs/img/`, organized by the page they belong to where practical:

- `docs/img/quickstart-terminal-2024-09.png`
- `docs/img/service-response-browser.png`
- `docs/img/component-diagram-v2.svg`

Naming conventions:

- Lowercase, hyphen-separated, no spaces.
- Include a rough date stamp (YYYY-MM) in the filename for screenshots that show a moving target (terminal output, browser views), since these are the ones most likely to go stale and need a diff-friendly replacement name.
- Diagrams that get updated should bump a version suffix (`-v2`, `-v3`) rather than overwrite the old file silently — this keeps the git log reviewable and lets a reviewer diff old vs. new in a pull request.
- Do not put images in the same folder as the page markdown files directly; keep `docs/img/` separate so page-listing scripts don't pick up binary files.

When you replace a screenshot, remove the old file in the same change rather than leaving orphaned images in `docs/img/` — a script in `scripts/` periodically flags images not referenced by any markdown page, and cleaning up proactively saves a review cycle.

## Accessibility checklist before committing an image

- [ ] Alt text present and descriptive (not just the filename)
- [ ] Image width within the table above
- [ ] Diagram box labels match current glossary terms
- [ ] Diagram has a one-line title embedded top-left
- [ ] File named with hyphens, lowercase, and a date stamp if it's a moving-target screenshot
- [ ] Old version of the image removed if this is a replacement
- [ ] Caption added if there's context the alt text doesn't cover

## Common mistakes seen in review

- Alt text that just says "screenshot" or "diagram" with nothing else.
- Screenshots at native resolution (often 2500px+ wide from a retina display) committed without resizing.
- Diagrams with box labels that predate a glossary term change — most often "HTTP server" instead of "the service," or "log file" instead of "database file."
- JPEG screenshots of terminal text, blurry enough that small numbers are unreadable.
- Two ideas crammed into one diagram (component relationships plus a sequence), making it hard to caption briefly.
- Images committed directly into the page's folder instead of `docs/img/`.

## Terminology

- **Screenshot** — A captured image of an actual screen, window, or terminal pane, as opposed to a drawn diagram.
- **Diagram** — A drawn illustration (boxes, arrows, labels) representing a relationship or sequence, not a literal screen capture.
- **Alt text** — The descriptive text attached to an image for accessibility and fallback display, set inside the `![...]()` markdown brackets.
- **Caption** — Optional italic text below an image adding context beyond what the alt text covers.
- **Component diagram** — A diagram showing how pieces of the package and service relate to one another, without implying a strict order.
- **Sequence diagram** — A diagram showing an ordered series of steps, typically numbered.
- **Moving-target screenshot** — A screenshot of output likely to change in appearance over time (terminal captures, browser views), as opposed to a static diagram.
- **Box label** — The short noun phrase inside a diagram shape identifying what it represents.
- **Arrow label** — The short verb phrase on a diagram connector describing the relationship between two boxes.
- **Docs/img/ folder** — The dedicated storage location for all embedded image assets, kept separate from markdown page files.

## Files referenced on this page

| Path | Purpose |
|---|---|
| `docs/img/` | Storage folder for all screenshot and diagram image assets |
| `docs/img/quickstart-terminal-2024-09.png` | Example moving-target screenshot naming pattern |
| `docs/img/component-diagram-v2.svg` | Example versioned diagram file |
| `scripts/` | Contains the script that flags orphaned images not referenced by any page |
| `docs-style/markdown-conventions.md` | Sibling page covering general markdown formatting, including when to use code blocks instead of images |
| `docs-style/terminology-glossary.md` | Canonical source of terms that diagram box labels must match |
| `docs-style/code-block-standards.md` | Sibling page covering formatting for text/code output, the alternative to screenshotting short output |

## Tools and libraries

| Tool | Version | Purpose |
|---|---|---|
| ImageMagick | 7.1.1 | Command-line image resizing and format conversion on Linux |
| sips | (built-in, macOS) | Command-line image resizing on macOS |
| draw.io desktop | 24.7.5 | Primary diagramming tool for component and sequence diagrams |
| Inkscape | 1.3.2 | SVG editing for diagrams needing manual touch-up |
| Optipng | 0.7.7 | Lossless PNG compression pass before committing screenshots |
| git | 2.43.0 | Version control for image assets, same as page content |

Diagram source files (the editable `.drawio` versions, not just exported PNG/SVG) should be kept alongside the exported image in `docs/img/` when the tool supports it, so future edits don't start from scratch.

## Review cadence for images specifically

Images get reviewed on the same cadence as the page they belong to — see review-cadence.md for the general schedule (owned by Support Enablement). There isn't a separate standalone review pass just for images; instead, reviewers checking a page for content accuracy also check that embedded screenshots still match current terminal/browser appearance and that diagram labels match the glossary. As of the 2025 review cycle, that shared-review approach replaced an earlier standalone quarterly image check that Priya Nair ran through most of 2024.

## Related pages

- [docs-style Folder Overview](./README.md)
- [Voice and Tone Guide](./voice-and-tone.md)
- [Terminology Glossary](./terminology-glossary.md)
- [Page Templates](./page-templates.md)
- [Review Cadence](./review-cadence.md)
- [Docs Publishing Workflow](./publishing-workflow.md)
- [Markdown Conventions](./markdown-conventions.md)
- [Code Block Standards](./code-block-standards.md)

## Change log

- **2023-11-08** — v1.0.0 — Initial page created by Priya Nair, covering basic image width limits.
- **2024-02-14** — v1.0.1 — Added alt text guidelines section after two pages shipped with empty alt attributes.
- **2024-05-02** — v1.0.2 — Added the docs/img/ naming convention and date-stamp recommendation for moving-target screenshots.
- **2024-07-19** — v1.0.3 — Added diagram labeling rules 1–5; rule 6 (color) and rule 7 (embedded title) added later.
- **2024-09-03** — v1.0.4 — Added worked examples for component and sequence diagrams; retired the old "screenshot everything" habit from early 2023 pages.
- **2024-10-11** — v1.1.0 — Folded the standalone quarterly image check into the general page review cadence; added the Tools and libraries table; updated ImageMagick version reference from 6.9 to 7.1.1.
