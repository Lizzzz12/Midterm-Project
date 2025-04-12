# Web Scraping Midterm Project: Quote Scraper

_Team Members_: Lizi Saxokia, Lasha Bregadze, Giorgi Parulava

---

1. Clone the repository:
   ```bash
   git clone https://github.com/Lizzzz12/Midterm-Project


## 📌 Overview

A Python tool to scrape quotes from [quotes.toscrape.com](http://quotes.toscrape.com) with:

- _GUI_ (Tkinter) and _CLI_ interfaces
- _Data storage_ (JSON/CSV/TXT)
- _Tag/author analysis_

---

## ✨ Equal Contributions

### _Giorgi Parulava_

1. _GUI Development_

   - Designed Tkinter interface (buttons, progress bar, scrollable text).
   - Implemented threaded scraping to prevent UI freezing.
   - Added error dialogs (messagebox) for user feedback.

2. _User Experience_
   - Status updates during scraping.
   - Quote display formatting.

---

### _Lasha Bregadze_

1. _Core Scraping Engine_

   - Built QuoteScraper class (requests, BeautifulSoup).
   - Handled pagination and multithreading.
   - Implemented rate limiting (delay=1s) and robots.txt checks.

2. _Error Handling_
   - Retry logic for failed requests (max_retries=3).
   - Fallback to single-threaded scraping if multithreading fails.

---

### _Lizi Sakhokia_

1. _Data Management_

   - Saved quotes to JSON/CSV/TXT (QuoteStorage class).
   - Added load_from_json() to reload saved data.

2. _Analysis & Testing_
   - Tag frequency analysis (TagAnalyzer).
   - Author quote counts (AuthorAnalyzer).
   - Unit tests for scraping/storage.

---

## 🛠️ Installation & Usage

(Same as before, but now equally attributed)

1. _Setup_ (All):
   ```bash
   pip install -r requirements.txt
   ```
