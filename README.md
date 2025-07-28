# 📄 PDF Outline Extractor – Adobe India Hackathon Round 1A Submission

## 🧠 Problem Statement

Extract a structured outline from a PDF:
- Detect and tag hierarchical headings (H1–H4)
- Extract the document title
- Output a JSON with heading text and page number

This solution runs **offline**, meets **amd64** architecture constraints, completes in **≤10 seconds**, and stays under **200MB**.

---

## 🔍 Methodology

We use `PyMuPDF` to analyze the visual and structural layout of each page:
- **Font Size & Style Detection**: Larger, bold fonts are prioritized for higher-level headings.
- **Regex Patterns**: Identifies common heading formats like `1`, `1.1`, `2.1.1`, etc.
- **Heuristics**: Flags capitalized phrases and common keywords like “Appendix”, “Timeline”, etc.
- **Flat Output**: Each heading is flattened but tagged by level (`H1` to `H4`) and accurately mapped to the PDF page number.

---

## 🧾 Output Format

```json
{
  "title": "RFP: Request for Proposal To Present a Proposal for Developing the Business Plan for the Ontario Digital Library",
  "outline": [
    { "level": "H1", "text": "Ontario’s Digital Library", "page": 2 },
    { "level": "H2", "text": "Summary", "page": 2 },
    { "level": "H3", "text": "Timeline:", "page": 2 },
    { "level": "H4", "text": "1) A preliminary report will be issued during June 2003.", "page": 7 }
  ]
}
```

### ✅ The output is:
- Flat (not nested), but sorted by appearance
- Level-tagged (`H1` to `H4`)
- Page-accurate
- Clean, compact, and hackathon-ready

---

## 🧱 Project Structure

```
.
├── Dockerfile                 # Multi-stage optimized container (amd64)
├── extractor/
│   ├── extract.py             # Main script for PDF heading extraction
│   └── requirements.txt       # Python dependencies (PyMuPDF)
├── input/                     # Input PDF files
├── output/                    # Output JSON files
└── README.md                  # This documentation
```

---

## 🚀 How to Use

### 🧪 Run Locally

```bash
# Clone project
git clone https://github.com/your-username/pdf-outline-extractor.git
cd pdf-outline-extractor

# Setup Python environment
cd extractor
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add PDFs to input folder and run
cd ..
mkdir -p input output
cp your_file.pdf input/
python extractor/extract.py
```

### 🐳 Run via Docker (Offline / amd64)

```bash
# Prepare folders
mkdir -p input output
cp your_file.pdf input/

# Build image
docker build --platform linux/amd64 -t pdf-outline-extractor .

# Run container
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outline-extractor
```

---

## 📦 Dependencies

In `extractor/requirements.txt`:

```
PyMuPDF==1.23.7
```

> No large libraries or ML models used — keeping total size <200MB.

---

## ✅ Hackathon Constraints Checklist

| Constraint                        | Status       |
|----------------------------------|--------------|
| Runtime ≤ 10 seconds             | ✅ Pass       |
| No Internet / Offline only       | ✅ Pass       |
| Model Size ≤ 200MB               | ✅ No model   |
| Platform Compatibility (amd64)  | ✅ Docker OK  |
| No hardcoded filenames           | ✅ Generic    |

---

## 🎯 Evaluation Alignment

| Criteria                                 | Our Solution                          |
|------------------------------------------|----------------------------------------|
| Accurate Heading Extraction (25 points)  | Multi-pattern detection with layout    |
| Offline Support                          | ✅ Fully offline                        |
| Performance (≤10s / ≤200MB)              | ✅ Fast, lightweight                    |
| JSON Output Format                       | ✅ Matches required schema              |
| Optional Bonus: Multilingual Handling    | ✅ Unicode-safe text extraction         |

---

## 👨‍💻 Built With

- Python 3.10
- PyMuPDF (fitz)
- Docker (for isolated amd64 builds)

---

## 📬 Contact

Made with 💡 for **Adobe India Hackathon – Round 1A**
**GitHub**: https://github.com/your-username
**Email**: you@example.com

