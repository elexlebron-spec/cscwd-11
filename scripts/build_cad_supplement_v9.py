"""Restore the unchanged v5 CAD figure in a standalone supplementary PDF.

Build with the optional paper/supplementary/requirements-build.txt dependency.
This reads frozen graph/results files and never reruns any solver.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import hashlib
import json
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper/supplementary"
IMAGE = ROOT / "paper/manuscript/images/public_graphs_v5.png"
ORIGINAL_IMAGE_SHA256 = "afbf685f66ee8e98b3df738c2b3bfed5830b61dd3a9dfadbbfc637e9198e7cd5"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(IMAGE) == ORIGINAL_IMAGE_SHA256, "Use the unchanged original matrix figure"
    provenance_path = ROOT / "data/bath_00621/provenance_v5.json"
    provenance = json.loads(provenance_path.read_text())
    summary_path = ROOT / "results/public_comparison_v5/summary.json"
    summary = json.loads(summary_path.read_text())
    assert sum(g["cases"] for g in summary["groups"]) == 72
    assert sum(g["CP_required"] for g in summary["groups"]) == 6
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in [IMAGE, provenance_path, summary_path]}
    for g in provenance["graphs"]:
        path = ROOT / f"data/bath_00621/graphs/{g['project']}_{g['hours']}h.json"
        assert sha(path) == g["graph_sha256"]
        graph = json.loads(path.read_text())
        assert len(graph["vertices"]) == g["n"] and len(graph["edges"]) == g["m"]
        adj = [set() for _ in graph["vertices"]]
        for i, j, _ in graph["edges"]:
            adj[i].add(j); adj[j].add(i)
        unseen = set(range(len(adj)))
        components = []
        while unseen:
            first = unseen.pop(); stack = [first]; size = 0
            while stack:
                i = stack.pop(); size += 1
                for j in adj[i] & unseen:
                    unseen.remove(j); stack.append(j)
            components.append(size)
        assert g["components"] == len(components) and g["largest_component"] == max(components)
        assert g["isolates"] == sum(not neighbors for neighbors in adj)
        inputs[str(path.relative_to(ROOT))] = sha(path)
    fontdir = Path(reportlab.__file__).resolve().parent / "fonts"
    for name, filename in [("Vera", "Vera.ttf"), ("VeraBold", "VeraBd.ttf"), ("VeraItalic", "VeraIt.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fontdir / filename)))
    pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="VeraBold", italic="VeraItalic", boldItalic="VeraBold")
    blue = colors.HexColor("#244F72")
    style = ParagraphStyle("Body", fontName="Vera", fontSize=9.6, leading=13.4, spaceAfter=8)
    title = ParagraphStyle("Title", parent=style, fontName="VeraBold", fontSize=17, leading=22, textColor=blue)
    small = ParagraphStyle("Small", parent=style, fontSize=8.4, leading=11.2, textColor=colors.HexColor("#444444"))
    caption = ParagraphStyle("Caption", parent=style, fontSize=9, leading=12.5)
    header = ParagraphStyle("Header", parent=small, fontName="VeraBold", alignment=TA_CENTER, spaceAfter=0, textColor=colors.white)
    pdf = OUT / "BARR_CAD_Supplement.pdf"
    doc = SimpleDocTemplate(str(pdf), pagesize=letter, rightMargin=45, leftMargin=45,
                            topMargin=57, bottomMargin=42, title="BARR Supplement: Public CAD Co-edit Structures",
                            author="Zhiran Wang", subject="Original v5 matrix figure and public graph structure audit")
    story = [
        Paragraph("Public CAD Co-edit Structures", title),
        Paragraph("Supplementary to <i>Budget Anchored Region Reduction for Collaborative Responsibility Repair</i>", small),
        Paragraph("Zhiran Wang &nbsp; | &nbsp; Ocean University of China &nbsp; | &nbsp; 2174560006@qq.com", small),
        Spacer(1, 7),
        Image(str(IMAGE), width=522, height=522 * 592 / 2240),
        Spacer(1, 5),
        Paragraph("<b>Figure S1.</b> Original three-panel BARR v5 figure, restored unchanged. Twelve-hour co-edit proxy matrices for projects A, B and C from the public Bath CAD logs [1, 2]. Rows and columns use the same subsystem/file-ID ordering. Color denotes quantized association weight, not measured handoff effort. Isolated files remain.", caption),
        Paragraph("<b>Construction.</b> Files have at least five distinct edit times. For each edit, another file counts once before the earlier of the next same-file edit and the one- or twelve-hour window end. Average the directional conditional frequencies, retain pairs at least 1/4, and round after scaling by eight. Table S1 includes both windows used by the paper.", style),
        Paragraph("<b>Table S1.</b> Structure of all six saved public graphs. The figure displays the twelve-hour rows.", caption)
    ]
    headings = ["Project", "Window (h)", "Files", "Edges", "Components", "Largest component", "Isolates"]
    rows = [[Paragraph(escape(x), header) for x in headings]]
    rows += [[g["project"], g["hours"], g["n"], f'{g["m"]:,}', g["components"],
              g["largest_component"], g["isolates"]] for g in provenance["graphs"]]
    table = Table(rows, colWidths=[60, 72, 52, 65, 85, 118, 70], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 1), (-1, -1), "Vera"), ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), blue), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"), ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F5F9")]),
        ("LINEBELOW", (0, -1), (-1, -1), .7, blue),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)
    ]))
    story.extend([table, Spacer(1, 11),
        Paragraph("<b>Interpretation and scope.</b> A/B/C identify three historical vehicle-design projects, not the two modeled responsibility teams. Co-edit association is not a verified physical interface. Ownership, costs, qualifications and capacity reservations remain synthetic or assumed. In the 72 saved repair cases, 66 finish by the shared unconstrained-cut shortcut; only six require constrained solving. The matrices describe public graph structure and do not establish industrial acceleration.", style),
        Paragraph("<b>Sources and reproduction.</b> [1] J. Gopsill, C. Snider and B. Hicks, University of Bath Research Data Archive (2019), "
                  '<link href="https://doi.org/10.15125/BATH-00621" color="#244F72">doi:10.15125/BATH-00621</link>. '
                  '[2] Related study, <i>Design Science</i> 5 (2019), '
                  '<link href="https://doi.org/10.1017/dsj.2019.20" color="#244F72">doi:10.1017/dsj.2019.20</link>. '
                  "Dataset/README: CC BY 4.0. This figure is our disclosed transformation, not a reproduction of the full original DSM pipeline. "
                  'Graphs, attribution, importer and hashes: <link href="https://github.com/elexlebron-spec/cscwd-11" color="#244F72">github.com/elexlebron-spec/cscwd-11</link>.', small)
    ])

    def decoration(canvas, document):
        canvas.saveState()
        canvas.setFont("VeraBold", 8)
        canvas.setFillColor(blue)
        canvas.drawString(45, 760, "BARR  /  SUPPLEMENTARY MATERIAL")
        canvas.setStrokeColor(colors.HexColor("#CAD9E4"))
        canvas.line(45, 751, 567, 751)
        canvas.setFont("Vera", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawString(45, 25, "Original matrix figure preserved; prepared 5 November 2026")
        canvas.drawRightString(567, 25, f"S{document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=decoration, onLaterPages=decoration)
    record = {"date": "2026-11-05", "inputs": inputs, "builder_sha256": sha(Path(__file__)),
              "figure_is_unchanged_original": True, "original_figure_sha256": ORIGINAL_IMAGE_SHA256,
              "graph_rows_verified": 6, "public_cases": 72, "shared_shortcuts": 66,
              "output_sha256": sha(pdf), "reportlab_version": reportlab.Version}
    (OUT / "provenance_v9.json").write_text(json.dumps(record, indent=2) + "\n")
    print(pdf)


if __name__ == "__main__":
    main()
