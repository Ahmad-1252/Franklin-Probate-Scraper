# Franklin County Probate & Property Data Scraper

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Selenium](https://img.shields.io/badge/Selenium-4.0%2B-orange)
![Pandas](https://img.shields.io/badge/Pandas-1.3%2B-brightgreen)

Automated tool for extracting probate case details and associated property data from Franklin County, Ohio government portals. Designed for legal professionals, real estate analysts, and government researchers.

## Key Features

### 🏛️ Probate Case Extraction
- Retrieves complete case details including:
  - Decedent information (name, address)
  - Case subtype (with/without will)
  - Fiduciary administrator details
  - Attorney contact information

### 🏡 Property Data Enhancement
- Cross-references probate cases with property records
- Extracts 20+ property characteristics:
  - Parcel ID, square footage, year built
  - Bedroom/bathroom count
  - Transfer history (dates, prices)

### ⚙️ Advanced Technical Capabilities
- **Smart Address Parsing**: Converts ordinal numbers (e.g., "5TH" → "Fifth") and splits addresses into components
- **Multi-Source Data Integration**: Combines data from probate court and auditor websites
- **Retry Logic**: 5-tier retry mechanism with incremental delays
- **Headless Operation**: Fully automated browser interactions

## Installation

### Prerequisites
- Python 3.8+
- Chrome browser (latest version)

### Setup
git clone https://github.com/yourusername/franklin-county-scraper.git

cd franklin-county-scraper

pip install -r requirements.txt

### Usage
python scraper.py
When prompted, enter:
Date in YYYYMMDD format (e.g., 20230101)

### Output Files
File	Description
case_data.csv	Current extraction results
Previous_data.csv	Backup of previous run
logs/	Error logs and processing history
Data Fields Extracted
Probate Case Details
Case number, subtype, and links

Decedent full name and address

Administrator contact information

Attorney details (name, phone, email)

Property Characteristics
Parcel ID and physical attributes

Transfer history (date, price)

Dwelling data (rooms, square footage)

Troubleshooting
Issue	Solution
ChromeDriver errors	Verify Chrome version matches ChromeDriver
Timeout failures	Increase wait times in WebDriverWait calls
Missing data	Check target website structure changes
License
MIT License - See LICENSE for details.


### Key Documentation Features:
1. **Visual Badges** - Quickly shows tech stack requirements
2. **Structured Data Flow** - Clearly explains the multi-source scraping process
3. **Troubleshooting Table** - Provides instant solutions for common issues
4. **Output Documentation** - Details all generated files and their purposes
5. **Field Reference** - Lists all extracted data points for end-users

The README emphasizes:
- The **dual-source** nature (probate + property data)
- **Data transformation** capabilities (address parsing)
- **Professional use cases** (legal/real estate applications)
