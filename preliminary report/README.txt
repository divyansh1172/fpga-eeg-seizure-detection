============================================================
README — Preliminary Report Compilation Instructions
============================================================

FILES
-----
  main.tex        — Complete LaTeX source (CVF/CVPR template, review mode)
  references.bib  — BibTeX bibliography

COMPILATION
-----------
  To compile, you need the CVPR/CVF LaTeX style files. Download the
  official CVPR Author Kit from:

    https://github.com/cvpr-org/author-kit/releases

  You need the following files in the same directory as main.tex:

    cvpr.sty

  Then compile with:

    pdflatex main
    bibtex main
    pdflatex main
    pdflatex main

  Alternatively, use latexmk:

    latexmk -pdf main

BEFORE SUBMISSION — EDIT CHECKLIST
-----------------------------------
  1. AUTHOR NAMES:
     Replace "Author 1" through "Author 4" with real names.
     Replace placeholder email addresses.

  2. AI DISCLOSURE SECTION:
     Search for "AI USAGE DISCLOSURE" in main.tex.
     Review and edit the AI usage statement as your team sees fit.

  3. PAPER ID:
     Replace \def\cvprPaperID{****} with your assigned paper ID
     (if applicable), or remove if not needed.

  4. CONFERENCE YEAR:
     \def\confYear{2026} is set; adjust if needed.

  5. REVIEW THE LITERATURE TABLE:
     Table 1 summarizes published results. Verify that all cited
     numbers match what your team independently checks.

  6. FIGURES:
     The block diagram (Figure 1) is generated via TikZ.
     If it does not compile cleanly, ensure the tikz and
     tikzlibrary packages are available.

NOTES
-----
  - The document uses \usepackage[review]{cvpr} for review mode
    as instructed by the professor.

  - There is NO page limit. The report is not artificially shortened.

  - No experimental results from this project are presented.
    All performance numbers are attributed to published literature.
============================================================
