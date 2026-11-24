# Spec v2: Supabase quota (phase 10)

Status: diagnosed 2026-11-24 from the usage page of the organization (Free plan); the first measure is below. The grace period ends **2026-12-12**: after that the
Fair Use Policy applies and requests to the project may answer 402.

## Diagnosis

The previous billing cycle went over **Egress** (5 GB included). The current cycle (16 Nov – 16 Dec) was at 0.78 GB on 24 Nov (≈ 100–240 MB a day). Everything
else is far from its limit: database 105 MB of 500 MB, Storage 3 MB of 1 GB, Edge Function invocations 25 of 500 000, MAU 0.

What costs egress: **the images of the RFCs are rows of `rfc_assets` with their bytes as base64 in the row** (278 rows, 55 MB; PHZ-0001 has 147, PHZ-0003 56).
The RFC page reads **every image of the page, in the three languages, as soon as it opens** (`hydrateAssets` in `assets/js/live.js`): one visit to PHZ-0001 downloads
144 images, **≈ 32 MB on the wire**, one visit to PHZ-0003 ≈ 26 MB, and nothing is kept for the next visit. At that size ≈ 150 visits use the 5 GB of a month.
The other reads are small (a revision's text 50–380 KB, the lists a few KB, the themes 9 KB).

## Decision

Cut what a visit downloads, without changing what the reader sees, what is stored or how images are published (no migration, no data move). Two measures, in this order:

1. **On demand.** An image is read only when it is about to be seen: its language is the one on screen and it is near the viewport (`IntersectionObserver`, 600 px of margin);
   when the reader switches language, the images of that language load then. A visit that only reads the top of the RFC costs the images of the top of the RFC.
2. **Remembered.** An image read is kept in the browser (Cache Storage, cache name `phiz-rfc-assets-v1`) under the key `<rfc>/<name>@<rev>`: the row that answers for a name and a version never changes
   (a new revision is a new `rev`), so a return visit, another language or another RFC version that uses the same image reads it from the browser. Pictures are never served from the
   cache for a different `rev`. If the cache is not available (private mode, an old browser) the page works as before, just without the memory.

What the reader sees does not change: the same `<img>`, the same click to open full size, the same "missing" mark. The preview of the new-RFC page (`nova.js`) keeps loading its own images.

Expected effect: a first visit to PHZ-0001 that reads the first screens goes from ≈ 32 MB to a few MB; a return visit to ≈ 0. With the measured use, a month stays well under 5 GB.

## Result (measured on the real data, 2026-11-24)

Opening PHZ-0001 reads **no image bytes** on the first screens (the first picture is far below), and still none at 25 % of the page; before, the same visit read 144 images
(≈ 32.5 MB). Reading the whole page in one language reads at most its 48 pictures (≈ 11 MB), the other two languages only when chosen; a return visit reads nothing.
(The scroll through the whole page could not be timed in the headless pane, so the "whole page" figure is computed from the sizes of the rows, not observed.)

## Next levers (not done now; each is its own spec when needed)

- Images in a **public Storage bucket** with a long `Cache-Control` (the CDN absorbs the traffic as *cached egress*, a separate 5 GB pool, and images stop being base64 in the database); needs a data move and a change of the publish flow.
- A **paid plan** removes the limit; the usage page shows the real figures to decide.
- After the **sign-in** phase, images may need to be served with the session (the same lever).

## Watching it

| date | egress used in the cycle | egress per day | note |
|---|---|---|---|
| 2026-11-24 | 0.78 GB (of 5 GB) | 100–240 MB | baseline, before the on-demand images (PR #44) were live; database 0.105 GB, Storage 0.003 GB |
| 2026-12-01 | — | — | check scheduled (a one-time task of the owner's Claude app reads the usage page and reports); fill in here |

The usage page (`supabase.com/dashboard/org/<org>/usage`) shows the egress per day; the target is to stay under 3 GB a month. A reading of `Egress` above 4 GB before the end of a cycle reopens this spec.

## Acceptance

- The images of a language that is not on screen are not read until that language is chosen.
- The images below the viewport are not read until the reader scrolls near them; an image that is read is shown, can be opened full size and keeps the "missing" mark when it does not exist.
- An image that was read once is not read again by a reload of the page, by the other language, or by another version of the RFC that uses the same row (the same `rev`); a different `rev` is read.
- Printing (or saving as PDF) the page reads the images of the language on screen that were not read yet, so the printout has them all.
- Without the cache (it throws), the page still shows every image.
- The compatibility tests of the images (`tests/test_images.py`, `tests/test_live.py`) keep passing.
