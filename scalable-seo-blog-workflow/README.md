# Scalable SEO Blog Workflow

[简体中文](README.zh-CN.md) · Version 0.16.6 · [MIT license](LICENSE)

**Start with a reader's question. Deliver a useful article, relevant images, and copy-ready publishing pages.**

Scalable SEO Blog Workflow is an open-source AI skill bundle for research, localized writing, images, independent review and preparation for human publication. It supports brand content, multilingual SEO and articles published on third-party platforms.

Use it for a single article or multiple independent articles. Reuse relevant research, writers and reviewers, then check and deliver each article.

[Core capabilities](#why-use-this-workflow) · [SEO value](#seo-value-of-the-delivered-article) · [Deliverables](#what-you-get) · [Workflow](#workflow) · [Task cost](#how-task-cost-is-controlled) · [Getting started](#getting-started)

## Why use this workflow?

- **Deliver articles built for SEO and relevant backlinks.** Preserve keyword meanings and search intent, support links with useful content, and use language and platform fit to reduce avoidable removal risks and avoid link-farm-style content.
- **Write for a specific reader problem.** Shape the topic around who needs what answer, then deliver useful explanations, steps, or choices. Connect product recommendations to the actual task.
- **Localize SEO with evidence.** Preserve required keyword meanings, prefer applicable brand wording, and check regional natural variants. Each title highlights the question its article answers.
- **Turn research into a writing plan.** Use the destination's content to understand readers and depth, then propose a topic, content direction and a concrete product role within the owner's search goal. Independent sources inform the plan; factual claims need support, while useful new angles need not already be popular.
- **Use rich, brand-aligned images to explain.** Show concrete objects, actions, comparisons or usable examples beside the relevant text. Let content determine composition, inspect every final image, and provide a separate cover.
- **Review the finished article.** Independent R examines the rendered page, real images and material sources, then checks affected changes after repairs.
- **Deliver complete illustrated articles.** The model selects an image host and obtains public direct URLs, then builds complete HTML and Markdown pages from one draft, with clean article text, images and reader-facing captions. Image reference details stay outside the body, alongside separate SEO fields and an excerpt.
- **Reduce repeated work.** Reuse research, writers and reviewers. Let code generate publishing pages, count links and check file consistency.

## SEO value of the delivered article

- **Align the title and body with one search goal.** Keep required keyword meanings in the title and answer related specific questions in the body. Different articles offer different answers around the same main keyword.
- **Give links a useful context.** Explain which step the recommended product helps with, include its confirmed brand name in visible target-product link text, and retain required anchors, link counts and relationship disclosure.
- **Reduce avoidable removal risks.** Match language and format to actual platform articles, follow verified rules, disclose relationships and support capability or result claims with evidence.
- **Avoid articles written merely to carry links.** Give each article useful content and a distinct focus. Keep links relevant to its question. Preserve requested anchors and links while checking applicable rules; count target-link occurrences across introductions, recommendations and sources together.
- **Check consistency through to the public page.** Review titles, SEO fields, excerpts, links and images in the finished publishing page. After human publication, the coordinator checks that the public page preserves them.

Links must follow [Google's spam policies](https://developers.google.com/search/docs/essentials/spam-policies) and each platform's current rules. Refer conflicting requirements to the owner. Search engines and platforms determine rankings, indexing and content removal.

## What you get

Open the publishing page in a browser, select the content and copy it into a rich-text editor.

| Deliverable | Purpose |
| --- | --- |
| Complete illustrated HTML page | Full article with public images at their exact positions; copy a clean title and body, with operation notes outside the article |
| Complete illustrated Markdown page | Full article with public image URLs, alt text and captions for Markdown editors |
| Numbered PNG/JPG/JPEG body images | Match adjacent sections, with quantity and placement agreed in the plan |
| Separate cover image | Local file and public URL listed at the end, separate from body images |
| SEO title, tags, and description | Retrieve individual fields at the bottom |
| Excerpt | A separate reader-facing summary for platform cards or excerpt fields |

The page follows a consistent order: **title → complete illustrated body → SEO fields → excerpt**. Select the text to copy it.

One draft and one asset set generate the delivery, with source notes kept alongside the article.

## Workflow

G coordinates the task, W writes the article, and R reviews it independently.

```text
G: summarize research and propose a plan for each article
        ↓
Owner confirms the plan
        ↓
W: write, illustrate, host images, verify URLs and build complete illustrated pages
        ↓
R: one full review of the rendered page, images, cover and material sources
        ↓ Quality passed
G: verify original requirements and hand off to the publisher
        ↓
Human publishes, returns the public URL and confirms acceptance or requests fixes
        ↓
Same G: compare the public page with the delivered article
        ↓ Owner accepts and the check passes
Task complete

Platform formatting or transfer issue → Human repair → Same G rechecks affected content
```

| Role | Responsibility |
| --- | --- |
| G: `blog-gate` | Research coordination, plan confirmation, writer assignment, requirement acceptance and public-page checks |
| W: `blog-writer` | Research, keyword localization, writing, images and publishing-page preparation |
| R: `blog-review` | Independent review of the rendered publishing page, images, cover and material sources |

### When the reviewer finds a problem

```text
R identifies the problem and its location
   → Original W fixes it and rebuilds the publishing pages
   → Same R checks the changes and affected content
   → G accepts the reviewed delivery
```

Refer unresolved material issues or changes to the confirmed plan to the owner. Record the review verdict for the revised version.

## How task cost is controlled

Costs come mainly from research, writing, images, review and repairs. Usage varies with article count, language difficulty, model and context.

- Reuse valid research and working agents to reduce repeated background reading.
- Generate both publishing pages from one Markdown draft; use code for counts and consistency.
- Review the complete article once, then recheck affected content after repairs. Keep approval notes brief.
- Have G verify owner requirements and check public URLs in returned batches.
- Save progress while waiting for human actions and resume when a reply arrives.

Image generation may carry a separate charge. Parallel work can reduce waiting; report token usage from actual records.

## Getting started

Once this workflow is connected to your local skill-capable tool, start with `$blog-gate`. Adapt this request to your task:

```text
$blog-gate

Brand and target page: <product-page URL>
Candidate platforms: <my supplied list or file>
Article count: 3, each on a different platform
Keywords: <required meanings and supporting angles>
CTA: <exact anchor, URL, and founder disclosure>
Images: <body-image quantity, ratio, and style; plus a cover>

First report each article's research, language/platform fit, and writing plan.
Wait for my confirmation before writing.
Deliver HTML, Markdown, images, SEO fields, and an excerpt for human publication.
```

Keep the complete `scalable-seo-blog-workflow` directory and register `blog-gate`, `blog-writer` and `blog-review` using your tool's skill installation mechanism.

### Installation and updates

1. Pull or download this repository and keep the complete package, including `docs/`, `templates/` and internal tools.
2. Point all three skill entries to their respective directories in the same package. For copied installations, update the complete bundle and the installed entries; for linked installations, update the linked bundle.
3. Confirm `matrix.yaml` reports version `0.16.6` and the actually loaded G/W/R entries describe complete articles, public image URLs and image reference details outside the body. New and resumed tasks should reread those entries and the short workflow.

This version delivers complete illustrated HTML/Markdown articles by default: HTML displays public images in place, and Markdown references the same URLs at the same positions. Placeholder cards are draft-only under `preview/`; operation notes and file details stay outside the article body.

## Task boundaries

Research stays within owner-supplied and confirmed platforms, with language fit based on actual platform articles. Writing and image generation begin after confirmation of the per-article plan. Humans handle publication; machines must not enter article editors, upload images to the target blog platform, save drafts, publish or delete. The model may upload intended-public article images to an image host under the [image-hosting rules](skills/blog-writer/references/image-hosting.md); extra payment or account access requires owner confirmation. Account preparation requires [separate authorization](docs/account-preparation.md).

## Runtime and further reading

Use an environment with local skills and file tools, plus Python 3.9+. Markdown building requires `markdown-it-py==3.0.0`; install it in an isolated environment where appropriate:

```sh
python -m pip install -r skills/blog-human-handoff/scripts/requirements.txt
```

Install the internal tools with the complete directory. Existing workspaces with `campaign.json`, article packages or review indexes keep their original workflow.

- [Short workflow](docs/workflow-core.md): task order and boundaries; reread after context compression.
- [Image hosting](skills/blog-writer/references/image-hosting.md): host selection, public URLs and complete illustrated publishing pages.
- [Authoring and tools](skills/blog-writer/references/markdown-authoring.md): draft format and build/check commands.
- [Editorial standard](skills/blog-writer/references/editorial-standard.md): reader value, keywords, images, and recommendations.
- [Platform matching](skills/blog-gate/references/platform-matching.md): audience and delivery fit within the supplied candidates.
- [Historical compatibility](README.legacy.md): reference for existing projects.

[MIT license](LICENSE). Contributions grounded in real articles, publishing experience and reproducible issues are welcome.
