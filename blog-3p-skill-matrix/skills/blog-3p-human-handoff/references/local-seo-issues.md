# Local SEO ISSUES reference

Use this report as a compact controllable preflight, not as a substitute for an external scanner. Treat it as a derived exception/check matrix: reference the one evidence pack, visual manifest and handoff manifest by path/hash, rather than manually repeating source prose, keyword lists, metadata, links, image Alt text or captions.

| Item | Result | Evidence / action |
| --- | --- | --- |
| Title relevance, intent and field mapping | PASS / FINDING / WARN / N/A | Judge reader task, clarity, value, naturalness and market fit. Keyword/length are WARN signals only; verify platform title is not a shorter substitute for the canonical article title. |
| Description accuracy and intent | PASS / FINDING / WARN / N/A | |
| Canonical outline and title/body transfer | PASS / FINDING / WARN / N/A | Check the local authoring outline and copy-selection boundary only. Do not inspect or require editor HTML/DOM semantics. Final heading hierarchy is accepted only from public reader-page visual evidence after `HUMAN_ACCEPTED`. |
| Natural focus-keyword coverage | PASS / FINDING / WARN / N/A | |
| Cross-language trend / regional-SERP localization | PASS / FINDING / WARN / N/A | |
| Link text, href and context | PASS / FINDING / WARN / N/A | |
| Image cards, alt and rights | PASS / FINDING / WARN / N/A | Cite the single visual manifest and report only an exception, affected image ID and action. |
| Reader value | PASS / FINDING / WARN / N/A | The article independently answers the reader task; it must remain coherent and useful if the required CTA is removed. |
| Required secondary CTA and disclosure | PASS / FINDING / WARN / N/A | Check the exact frozen visible anchor text, product/destination, claim basis, reader-task relevance and any applicable visible disclosure. Missing, substituted or changed CTA fields are FINDING. |
| Canonical-to-visual payload fidelity | PASS / FINDING / WARN / N/A | Cite the handoff manifest plus the compiled payload hash; do not duplicate its contents. |

For a cross-language target, record `MODEL_TRANSLATION_FALLBACK` only with two independent regional-SERP checks showing no usable consensus variant, plus the model wording and rationale. It is a reviewed working variant, not claimed SERP evidence. `FINDING` is a quality defect and receives a stable ID. `WARN` is an optimization note unless the frozen brief makes it mandatory. Record external SEO scan state separately as `RAN`, `UNAVAILABLE` or `NOT_REQUESTED`.

Once text and SEO fields are stable, the final visual/payload delta records only changed manifest entries, asset/payload hashes, affected local-SEO rows and stable findings. It must not become a second full article audit. A source, canonical, metadata, link, CTA or reader-value change is outside this narrow scope and returns to the normal W–R repair path.
