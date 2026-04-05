import fitz
import pathlib

pdf = fitz.open("research_paper.pdf")
out = pathlib.Path("page_renders")
out.mkdir(exist_ok=True)
for i, page in enumerate(pdf, start=1):
    out_file = out / ("page_%02d.png" % i)
    page.get_pixmap(matrix=fitz.Matrix(2, 2)).save(str(out_file))
print("rendered", len(pdf), "pages")
