import pdfplumber

def extract_text_from_pdf(pdf_path, txt_path):
    with pdfplumber.open(pdf_path) as pdf:
        with open(txt_path, "w", encoding="utf-8") as f:
            for page in pdf.pages:
                text = page.extract_text()
                if text:  # Write text only if extraction is successful
                    f.write(text + "\n--- Page Break ---\n") # Separates pages

# Example usage:
pdf_file = "Company Documentation.pdf"
text_file = "output.txt"
extract_text_from_pdf(pdf_file, text_file)
print(f"Text extracted and saved to {text_file}")