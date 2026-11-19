LunarCV public development release

The intended portfolio deliverable is a reproducible real-data registration experiment with inspectable mappings, confidence, coverage, failures and resource costs. The available scene is development data. The current backend must not be described as ISRO-deployed, generally robust across payloads, or independently sub-pixel accurate.

The release default uses ALIKED with pretrained LightGlue. LightGlue code/weights are Apache-2.0, ALIKED is BSD-3-Clause, and DISK is Apache-2.0 according to the official LightGlue README: https://github.com/cvg/LightGlue#license. Original SuperPoint has a separate restrictive license, so it is not a release preset. The installed official LightGlue revision is pinned in backend/pyproject.toml and backend/uv.lock; each run records local model hashes.

The bundled RIFT2 phase-congruency files retain their MIT notices. The wrapper/descriptor implementation lacks a recorded upstream redistribution license; this remains a publication blocker. Do not invent or apply a license to someone else's code. A license for the project's original contributions also needs the rights holder's decision. scripts/release_check.py reports these gates.

ISSDC's Chandrayaan-2 disclaimer says the data remain ISRO property, are supplied for non-profit scientific use and restrict copying/redistribution without permission: https://pradan.issdc.gov.in/ch2/disclaimer.xhtml. Public availability does not grant unrestricted hosting rights. Keep raw products, source crops, derived images and existing showcase imagery out of a new distributable bundle until applicable permission is confirmed. An approved portfolio demonstration can link to the official acquisition workflow; do not assume screenshots or derived products are exempt.

LROC distinguishes PDS archive data from copyrighted website/curated imagery, with different conditions and citation requirements: https://www.lroc.im-ldi.com/about/terms. Record the actual acquisition source and appropriate NASA/GSFC/ASU credit. Read the provider's terms for the specific product, including SELENE when added.

Before publication: run the backend tests/lint and inspect_mapping.py on the chosen real run; retain all development preset failures in the report; confirm imagery and third-party redistribution rights; choose the project-code license; verify the clean installed package and deployment environment; and run the integrated frontend/browser checks. No GitHub release or public deployment is performed by these scripts.

A public demonstration should show source/reference product IDs, their real-file provenance, the complete processing windows, actual matched points, coverage and rejected regions, the native transform direction, the registered product and quality decision. Show fit residual as a diagnostic and independent accuracy as unavailable. Include hardware and cold/cache timing. Do not substitute generated metrics when a job fails.

Independent controls and additional untouched complete scenes remain follow-up work. The target engineering score of 90+/100 has not been earned by this development release.

The integrated React/TypeScript workspace replaces the old simulated runtime. Vite disables copying the legacy public directory; the production build contains code/styles and an inline first-party icon. Docker also excludes public imagery. Existing tracked assets and Git history remain subject to rights review; build exclusion alone is not repository sanitization. Local browser screenshots/traces contain real products and must not be published without permission. See production_readiness_report.md for current verification and score.
