# Legal Document Processing Framework

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Dataset Size](https://img.shields.io/badge/documents-51-orange.svg)](https://github.com/RafiFirnanda/projectLegalDocuments)
[![Format](https://img.shields.io/badge/format-Excel%20%7C%20TXT-yellow.svg)](https://github.com/RafiFirnanda/projectLegalDocuments)

## About The Project

This repository contains a comprehensive collection of 51 legal documents from the Yogyakarta District Court (PN Yogyakarta), specifically focusing on narcotics cases. The project includes both the raw documents and a Python-based processing framework for extracting and structuring the legal information.

The framework simplifies common tasks in legal document processing, such as:

- Automated extraction of case numbers and court information
- Intelligent evidence (barang bukti) identification and cleaning
- Court decision (amar putusan) extraction and formatting
- Standardized output generation in Excel format
- Robust text cleaning and normalization

## Getting Started

To get started with this project, you'll need Python 3.12 or higher installed on your machine. Here's how to use it:

```bash
# Clone the repository
git clone https://github.com/RafiFirnanda/projectLegalDocuments.git

# Navigate to the project directory
cd projectLegalDocuments

# Install required dependencies
pip install pandas pathlib

# Run the document processor
python Overview_new.py
```

## Project Structure

```
.
├── data/
│   ├── raw/          # Original legal documents (51 files)
│   └── processed/    # Processed Excel outputs
├── Overview_new.py   # Main processing script
├── casebase.py       # Supporting module
└── README.md         # Documentation
```

## Core Features

The framework provides several powerful features for legal document processing:

### Document Parser
```python
from Overview_new import DocumentParser

parser = DocumentParser()
result = parser.extract_nomor_putusan(text)
```

### Pattern Recognition
- Advanced regex patterns for legal document structure
- Intelligent text cleaning algorithms
- Standardized output formatting

### Data Extraction
The framework extracts key information including:
- Case numbers (nomor putusan)
- Court information
- Evidence lists (barang bukti)
- Court decisions (amar putusan)

## Dataset Information

The dataset includes:
- **Source**: Pengadilan Negeri Yogyakarta
- **Document Type**: Narcotics case verdicts
- **Total Documents**: 51
- **Format**: Raw text files (.txt)
- **Output**: Structured Excel file

## Documentation

### Processing Pipeline

1. **Document Loading**
   - UTF-8 encoding support
   - Automatic directory traversal

2. **Information Extraction**
   - Pattern-based extraction
   - Context-aware parsing
   - Error handling

3. **Text Cleaning**
   - Remove page markers
   - Standardize formatting
   - Clean redundant information

4. **Output Generation**
   - Excel file generation
   - Structured column format
   - Data validation

## Usage Examples

### Basic Usage
```python
# Initialize parser
parser = DocumentParser()

# Process single document
with open('data/raw/case_001.txt', 'r', encoding='utf-8') as f:
    text = f.read()
    result = parser.extract_barang_bukti(text)
```

### Batch Processing
```python
# The script will automatically process all documents
python Overview_new.py
```

## Contributing

Contributions are welcome and greatly appreciated. To contribute:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Pengadilan Negeri Yogyakarta for the source documents
- Contributors and researchers in legal document processing
- Python community for excellent text processing tools

## Contact

Project Maintainer - your.email@example.com

Project Link: [https://github.com/RafiFirnanda/projectLegalDocuments](https://github.com/RafiFirnanda/projectLegalDocuments)

---

Made with ❤️ by Rafi Firnanda