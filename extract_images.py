import fitz # PyMuPDF
import os

pdf_path = "The-Girl-Who-Never-Made-Mistakes.pdf"
output_dir = "images_extracted"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

doc = fitz.open(pdf_path)
for i in range(len(doc)):
    page = doc.load_page(i)
    # Increase resolution to 2x for better quality
    zoom = 2 
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(f"{output_dir}/page_{i+1}.png")
    print(f"Extracted page {i+1}")

doc.close()
