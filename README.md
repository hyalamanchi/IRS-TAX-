# IRS Tax Form Parser

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive Python application for parsing, processing, and analyzing IRS tax forms using advanced OCR, NLP, and machine learning techniques. This system automates the extraction of structured data from tax documents and supports integration with e-filing systems.

## 🚀 Features

### Core Capabilities
- **Advanced OCR Processing**: Extract text from PDF and image files using Tesseract OCR with preprocessing optimization
- **Intelligent Form Recognition**: Automatically identify tax form types (1040, W2, 1099, Schedule C, etc.)
- **NLP-Powered Data Extraction**: Use state-of-the-art NLP models for entity recognition and data validation
- **Multi-Database Support**: Store and manage data with SQLite, PostgreSQL, or MongoDB
- **E-Filing Integration**: Prepare and submit forms to IRS systems with encryption and security
- **Batch Processing**: Process multiple documents simultaneously with progress tracking
- **RESTful API**: Optional web service interface for integration with other systems

### AI/ML Features
- **Named Entity Recognition**: Extract taxpayer information, amounts, dates, and identifiers
- **Form Classification**: Automatically categorize different types of tax documents
- **Data Validation**: Intelligent validation rules for tax-specific data
- **Confidence Scoring**: Quality assessment for extracted data
- **Pattern Recognition**: Identify recurring patterns and anomalies in tax data

### Enterprise Features
- **Containerized Deployment**: Docker support for easy deployment and scaling
- **Security & Encryption**: Secure handling of sensitive tax information
- **Audit Logging**: Complete audit trail for compliance and monitoring
- **Error Handling**: Robust error recovery and reporting mechanisms
- **Configuration Management**: Flexible configuration for different environments

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Docker Deployment](#docker-deployment)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🛠 Installation

### Prerequisites

- Python 3.11 or higher
- Tesseract OCR
- Git

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng libtesseract-dev
sudo apt-get install poppler-utils libpoppler-cpp-dev
sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev
```

#### macOS
```bash
brew install tesseract poppler
```

#### Windows
1. Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install Poppler from: https://blog.alivate.com.au/poppler-windows/
3. Add both to your system PATH

### Python Package Installation

#### Option 1: Clone and Install
```bash
# Clone the repository
git clone https://github.com/your-org/irs-tax-form-parser.git
cd irs-tax-form-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

#### Option 2: Docker Installation
```bash
# Pull the Docker image
docker pull your-registry/irs-tax-parser:latest

# Or build locally
docker build -t irs-tax-parser .
```

## ⚡ Quick Start

### Basic Usage

```python
from src.main import TaxFormProcessor

# Initialize the processor
processor = TaxFormProcessor()

# Process a single document
result = processor.process_document('path/to/tax_form.pdf')

if result['success']:
    print(f"Form Type: {result['form_type']}")
    print(f"Confidence: {result['confidence_score']:.2f}")
    print(f"Extracted Data: {result['extracted_data']}")
else:
    print(f"Error: {result['error']}")
```

### Command Line Interface

```bash
# Process a single file
python -m src.main --file tax_return.pdf

# Process a directory of files
python -m src.main --directory /path/to/tax/documents

# Show processing statistics
python -m src.main --stats

# Interactive mode
python -m src.main
```

### Batch Processing Example

```python
# Process multiple files
batch_result = processor.process_batch('/path/to/documents')

print(f"Processed: {batch_result['successful_count']}/{batch_result['total_files']}")
print(f"Success Rate: {batch_result['success_rate']:.1f}%")
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DB_TYPE=sqlite  # sqlite, postgresql, mongodb
DATABASE_URL=sqlite:///tax_forms.db

# OCR Configuration
TESSERACT_PATH=/usr/bin/tesseract  # Optional: specify custom path

# NLP Configuration
NLP_MODEL=dbmdz/bert-large-cased-finetuned-conll03-english

# E-Filing Configuration (Optional)
ENABLE_EFILING=false
EFILING_PROVIDER=irs_mef
EFILING_ENV=test
EFILING_ENDPOINT=https://testclient.irs.gov/efile/ws
EFILING_USERNAME=your_username
EFILING_PASSWORD=your_password
EFILING_ENCRYPTION_KEY=your-32-byte-encryption-key

# Output Configuration
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### Configuration File

Alternatively, create a `config.json` file:

```json
{
  "database_type": "sqlite",
  "database_connection": "sqlite:///tax_forms.db",
  "enable_efiling": false,
  "nlp_model": "dbmdz/bert-large-cased-finetuned-conll03-english",
  "output_directory": "./output",
  "log_level": "INFO",
  "tesseract_path": null
}
```

## 📖 Usage

### Processing Individual Documents

#### Supported File Formats
- PDF documents
- Image files (PNG, JPG, JPEG, TIFF, BMP)

#### Example: Processing a 1040 Form
```python
from src.main import TaxFormProcessor

processor = TaxFormProcessor()

# Process a Form 1040
result = processor.process_document('form_1040.pdf', form_type='1040')

# Access extracted data
if result['success']:
    extracted_data = result['extracted_data']
    
    print(f"Taxpayer Name: {extracted_data.get('name', 'Not found')}")
    print(f"SSN: {extracted_data.get('ssn', 'Not found')}")
    print(f"Filing Status: {extracted_data.get('filing_status', 'Not found')}")
    print(f"Total Income: {extracted_data.get('total_income', 'Not found')}")
```

### Advanced Processing Options

#### Custom OCR Configuration
```python
from src.ocr_parser import OCRParser

# Initialize with custom Tesseract path
ocr_parser = OCRParser(tesseract_path='/custom/path/to/tesseract')

# Process document with custom settings
results = ocr_parser.process_document('document.pdf')
```

#### NLP Analysis
```python
from src.nlp_processor import NLPProcessor

nlp_processor = NLPProcessor()

# Analyze extracted text
text = "Form 1040 Individual Income Tax Return..."
analysis = nlp_processor.process_tax_form_text(text)

print(f"Detected Form Type: {analysis['form_type']}")
print(f"Entities Found: {len(analysis['entities'])}")
print(f"Validation Status: {analysis['validation'].is_valid}")
```

#### Database Operations
```python
from src.db_handler import DatabaseHandler, TaxFormRecord

# Initialize database
db = DatabaseHandler(db_type='sqlite')

# Create a form record
form_record = TaxFormRecord(
    form_type='1040',
    form_name='Individual Income Tax Return',
    tax_year=2023,
    processing_status='processed',
    confidence_score=0.95
)

# Insert into database
form_id = db.insert_tax_form(form_record)

# Search forms
results = db.search_tax_forms({'form_type': '1040', 'tax_year': 2023})
```

### E-Filing Integration

```python
from src.efiling_integration import EFilingIntegration, EFilingConfiguration

# Configure e-filing
config = EFilingConfiguration(
    service_provider='irs_mef',
    environment='test',
    api_endpoint='https://testclient.irs.gov/efile/ws',
    username='your_username',
    password='your_password'
)

efiling = EFilingIntegration(config)

# Prepare submission
form_data = {
    'form_type': '1040',
    'name': 'John Doe',
    'ssn': '123-45-6789',
    'filing_status': 'single',
    'total_income': 50000
}

submission = efiling.prepare_submission(form_data, '1040', 2023)

# Submit to IRS (test environment)
result = efiling.submit_tax_form(submission)
```

## 🌐 API Reference

### REST API Endpoints (Optional)

Start the API server:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

#### Process Document
```http
POST /api/v1/process
Content-Type: multipart/form-data

file: [tax_form.pdf]
form_type: 1040 (optional)
```

#### Get Processing Status
```http
GET /api/v1/status/{form_id}
```

#### Search Forms
```http
GET /api/v1/forms?form_type=1040&tax_year=2023&limit=10
```

### Python API

#### Core Classes

- **`TaxFormProcessor`**: Main orchestration class
- **`OCRParser`**: OCR and text extraction
- **`NLPProcessor`**: Natural language processing and validation
- **`DatabaseHandler`**: Data persistence and retrieval
- **`EFilingIntegration`**: E-filing system integration

#### Key Methods

```python
# Process documents
processor.process_document(file_path, form_type=None)
processor.process_batch(directory_path, file_patterns=None)

# Database operations
db.insert_tax_form(form_record)
db.get_tax_form(form_id)
db.search_tax_forms(filters, limit=100, offset=0)
db.get_processing_statistics()

# OCR operations
ocr.process_document(file_path)
ocr.extract_text_from_image(image_path)
ocr.extract_text_from_pdf(pdf_path)

# NLP operations
nlp.process_tax_form_text(text, form_type=None)
nlp.extract_entities(text)
nlp.validate_extracted_data(form_type, data)

# E-filing operations
efiling.prepare_submission(form_data, form_type, tax_year)
efiling.submit_tax_form(submission)
efiling.check_submission_status(submission_id)
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t irs-tax-parser .

# Run in development mode
docker run -it --rm \
  -v $(pwd)/data:/home/taxparser/app/data \
  -v $(pwd)/output:/home/taxparser/app/output \
  irs-tax-parser:latest

# Run in production mode
docker run -d \
  --name tax-parser \
  -p 8000:8000 \
  -v tax-data:/home/taxparser/app/data \
  -v tax-output:/home/taxparser/app/output \
  -e DB_TYPE=postgresql \
  -e DATABASE_URL=postgresql://user:pass@db:5432/taxforms \
  irs-tax-parser:latest
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  tax-parser:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_TYPE=postgresql
      - DATABASE_URL=postgresql://taxuser:taxpass@db:5432/taxforms
    volumes:
      - ./data:/home/taxparser/app/data
      - ./output:/home/taxparser/app/output
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=taxforms
      - POSTGRES_USER=taxuser
      - POSTGRES_PASSWORD=taxpass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

## 👨‍💻 Development

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/irs-tax-form-parser.git
cd irs-tax-form-parser

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Install pre-commit hooks
pre-commit install

# Download required models
python -m spacy download en_core_web_sm
```

### Code Quality Tools

```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src

# Run all checks
pre-commit run --all-files
```

### Adding New Features

1. **New Form Types**: Add patterns to `src/nlp_processor.py`
2. **Database Backends**: Extend `src/db_handler.py`
3. **E-filing Providers**: Implement new providers in `src/efiling_integration.py`
4. **OCR Improvements**: Enhance preprocessing in `src/ocr_parser.py`

### Project Structure

```
irs-tax-form-parser/
├── src/                     # Main source code
│   ├── __init__.py
│   ├── main.py             # Main application entry point
│   ├── ocr_parser.py       # OCR functionality
│   ├── nlp_processor.py    # NLP and text analysis
│   ├── db_handler.py       # Database operations
│   └── efiling_integration.py  # E-filing systems
├── tests/                   # Test suite
│   ├── test_ocr_parser.py
│   ├── test_nlp_processor.py
│   ├── test_db_handler.py
│   ├── test_efiling_integration.py
│   └── test_main.py
├── data/                    # Sample data and schemas
│   └── tax_forms.csv
├── .github/
│   └── workflows/
│       └── ci.yml          # CI/CD pipeline
├── Dockerfile              # Container definition
├── docker-compose.yml      # Multi-service deployment
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_ocr_parser.py

# Run with verbose output
pytest -v
```

### Test Categories

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test processing speed and memory usage

### Example Test

```python
def test_form_identification():
    processor = TaxFormProcessor()
    
    # Test 1040 identification
    result = processor.process_document('tests/data/sample_1040.pdf')
    
    assert result['success'] is True
    assert result['form_type'] == '1040'
    assert result['confidence_score'] > 0.8
```

## 📊 Performance Considerations

### Optimization Tips

1. **Batch Processing**: Process multiple documents together for better throughput
2. **Image Preprocessing**: Optimize image quality before OCR
3. **Model Caching**: Keep NLP models loaded in memory
4. **Database Indexing**: Add indexes on frequently queried fields
5. **Memory Management**: Monitor memory usage for large documents

### Benchmarks

Typical processing times on standard hardware:
- Single page PDF: 2-5 seconds
- Multi-page PDF: 5-15 seconds
- Batch of 100 forms: 5-10 minutes

## 🔒 Security

### Data Protection

- **Encryption**: All sensitive data is encrypted at rest and in transit
- **Access Control**: Role-based access control for multi-user environments
- **Audit Logging**: Complete audit trail of all operations
- **Data Retention**: Configurable data retention policies

### Best Practices

1. Use environment variables for sensitive configuration
2. Regularly rotate encryption keys
3. Implement proper access controls
4. Monitor for suspicious activities
5. Keep dependencies updated

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Reporting Issues

Please use the GitHub issue tracker to report bugs or request features.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Tesseract OCR**: For optical character recognition capabilities
- **spaCy**: For natural language processing
- **Transformers**: For state-of-the-art NLP models
- **OpenCV**: For image processing functionality
- **FastAPI**: For API framework
- **SQLAlchemy**: For database ORM

## 📞 Support

- **Documentation**: [Full documentation](https://your-org.github.io/irs-tax-form-parser)
- **Issues**: [GitHub Issues](https://github.com/your-org/irs-tax-form-parser/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/irs-tax-form-parser/discussions)
- **Email**: support@your-org.com

---

**Note**: This software is for educational and development purposes. Always consult with tax professionals and ensure compliance with IRS regulations when processing actual tax documents.