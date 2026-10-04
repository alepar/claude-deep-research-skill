# Optional HTML and PDF delivery

Generate HTML or PDF only when the user requests it. Put the rendered file in
the user's requested destination, or beside the final Markdown report in the
default research folder. Include the final Markdown report and linked dossiers
in the delivered folder. Do not open files automatically.

## HTML

Render the complete final Markdown content, including its answer, synthesis,
uncertainty, methodology, bibliography, and links to dossiers. Preserve each
relative dossier link so it resolves from the HTML file's location in the
delivered package. If the HTML file is in a different subdirectory, adjust
those links and verify their targets.

The optional [HTML template](../templates/mckinsey_report_template.html) is
one presentation choice. It has placeholders for title, date, source count,
metrics, content, and bibliography. Populate only metrics actually supported
by registered evidence; an empty dashboard is preferable to invented metrics.
The helper in scripts/md_to_html.py returns content and bibliography fragments
for traditional multi-section reports. Its command-line entry point prints a
preview, not a finished HTML file, and its conversion may omit text before the
first level-two heading. Inspect the full rendered output, especially for a
compact final report, before using those fragments.

Run:

    python scripts/verify_html.py --html [html_path] --md [final_report_path]

Check that all material Markdown content and bibliography entries survive
conversion, each original source citation remains beside its claim, and every dossier
link opens the intended local Markdown file. Repair only the defective rendered
part, then rerun the affected checks. The Markdown package remains the
authoritative evidence trail. Claim and facet comments are invisible in HTML;
preserve their adjacent visible claim text and citation instead.

## PDF

Use [WeasyPrint guidelines](weasyprint_guidelines.md) for print layout when
generating a PDF. A typical command is:

    weasyprint [html_path] [pdf_path]

Check legibility, page breaks, bibliography, and any dossier links in the PDF.
Deliver the linked Markdown folder alongside the PDF. If PDF links cannot
reliably open the accompanying Markdown, state clearly in the PDF that the
detailed dossiers are in that folder. A provider or renderer failure affects
only the requested rendered format; retain the verified Markdown package and
report the specific rendering blocker.
