# 📄 PDF Outline Extractor — Round 1A Hackathon Submission

---

## 🧠 Problem Statement

Extract a **structured outline** from a PDF:
- Document `title`
- Headings classified into `H1`, `H2`, `H3`
- Include the `page number` of each heading

This solution runs **offline**, meets the performance and architecture constraints (amd64, ≤10s, ≤200MB), and outputs a JSON per PDF file.

---

## 🧱 Project Structure

```bash
.
├── Dockerfile                   # Multi-stage optimized Dockerfile
├── go/
│   └── cmd/
│       └── main.go              # Go binary to trigger Python logic
├── extractor/
│   ├── extract.py               # PDF heading extractor
│   └── requirement.txt          # Python dependencies (PyMuPDF)
├── input/                       # Put your PDFs here (used by Docker/local)
├── output/                      # JSON output will be placed here
└── README.md                    # You're reading it

🧾 PDF Outline Extractor
A simple tool to extract structured outlines (headings like H1, H2, H3) from PDF files and export them as JSON.

🧪 Option 1: Run Locally (with Python Virtual Environment)
✅ Step 1: Clone the repository
git clone https://github.com/your-username/pdf-outline-extractor.git
cd pdf-outline-extractor
✅ Step 2: Create virtual environment
cd extractor
python3 -m venv venv
✅ Step 3: Activate the environment
On Linux/macOS:

source venv/bin/activate
On Windows:

venv\Scripts\activate
✅ Step 4: Install Python dependencies
pip install -r requirement.txt
✅ Step 5: Add a PDF file to input directory
cd ..
mkdir -p input output
cp your_file.pdf input/
✅ Step 6: Run the Python script
python extractor/extract.py
This will read all PDF files from input/ and generate corresponding .json files in output/.

🐳 Option 2: Run via Docker (Offline Submission Mode)
✅ Step 1: Add PDFs to input directory
mkdir -p input output
cp your_file.pdf input/
✅ Step 2: Build the Docker image
docker build --platform linux/amd64 -t pdf-outline-extractor:submission .
Replace submission with any tag you prefer.

✅ Step 3: Run the container
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outline-extractor:submission
✅ Step 4: Check output
cat output/your_file.json
Each PDF will result in a JSON like:

{
  "title": "Understanding AI",
  "outline": [
    { "level": "H1", "text": "Introduction", "page": 1 },
    { "level": "H2", "text": "What is AI?", "page": 2 },
    { "level": "H3", "text": "History of AI", "page": 3 }
  ]
}

