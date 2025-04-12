"""
Web Scraping Midterm Project - Quote Scraper
Complete version with GUI, CLI, and tag analysis

Project Resources:
- Main scraping site: http://quotes.toscrape.com
- BeautifulSoup docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- Requests docs: https://requests.readthedocs.io/en/latest/
- Tkinter docs: https://docs.python.org/3/library/tkinter.html
"""

import requests
import time
import json
import csv
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Optional, Tuple
import unittest
import concurrent.futures
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from threading import Thread
from collections import defaultdict


# ====================== OOP MODELS ======================
class Quote:
    """Represents a quote with text, author, and tags
    Documentation: https://docs.python.org/3/tutorial/classes.html
    """
    def __init__(self, text: str, author: str, tags: List[str]):
        self.text = text
        self.author = author
        self.tags = tags

    def __repr__(self) -> str:
        return f"Quote(text='{self.text[:20]}...', author='{self.author}')"

    def to_dict(self) -> Dict:
        """Convert Quote object to dictionary for storage"""
        return {
            "text": self.text,
            "author": self.author,
            "tags": self.tags
        }


# ====================== TAG ANALYZER ======================
class TagAnalyzer:
    """Analyzes tag frequency across all quotes
    Reference: https://docs.python.org/3/library/collections.html#collections.defaultdict
    """
    @staticmethod
    def count_tags(quotes: List[Dict]) -> Dict[str, int]:
        """Count how many times each tag appears across all quotes"""
        tag_counts = defaultdict(int)
        for quote in quotes:
            for tag in quote['tags']:
                tag_counts[tag] += 1
        return dict(tag_counts)

    @staticmethod
    def get_top_tags(quotes: List[Dict], n: int = 10) -> List[Tuple[str, int]]:
        """Get the top n most frequently used tags"""
        tag_counts = TagAnalyzer.count_tags(quotes)
        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    @staticmethod
    def display_tag_analysis(quotes: List[Dict]) -> str:
        """Generate a formatted string of tag analysis"""
        if not quotes:
            return "No quotes available for tag analysis"

        tag_counts = TagAnalyzer.count_tags(quotes)
        total_unique_tags = len(tag_counts)
        total_tag_uses = sum(tag_counts.values())

        analysis = [
            f"\n=== TAG ANALYSIS ===",
            f"Total unique tags: {total_unique_tags}",
            f"Total tag uses: {total_tag_uses}",
            f"Average tags per quote: {total_tag_uses/len(quotes):.1f}",
            "\nTop 10 most popular tags:"
        ]

        for tag, count in TagAnalyzer.get_top_tags(quotes):
            analysis.append(f"- {tag}: {count} quotes")

        return "\n".join(analysis)


# ====================== SCRAPER COMPONENTS ======================
class QuoteScraper:
    """Handles HTTP requests and scraping logic with enhanced error handling
    Requests docs: https://requests.readthedocs.io/en/latest/
    BeautifulSoup docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
    """
    def __init__(self, base_url: str = "http://quotes.toscrape.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        self.robots_txt = self._check_robots_txt()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.timeout = 10
        self.max_retries = 3
        self.delay = 1  # Delay between requests in seconds

    def _check_robots_txt(self) -> bool:
        """Check robots.txt with better error handling"""
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            response = self.session.get(robots_url, timeout=self.timeout)
            response.raise_for_status()
            if "Disallow: /" in response.text:
                print("Warning: Scraping disallowed by robots.txt")
                return False
            return True
        except Exception as e:
            print(f"Warning: Could not check robots.txt ({e}). Proceeding anyway.")
            return True

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with retries and better timeout handling"""
        if not self.robots_txt:
            return None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                if not response.text.strip():
                    raise ValueError("Empty response content")

                time.sleep(self.delay)  # Respectful scraping delay
                return response.text
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                    return None
                time.sleep(1 * (attempt + 1))
        return None

    def scrape_all_quotes(self) -> List[Dict]:
        """Scrape all quotes with fallback to single-threaded if needed
        Threading docs: https://docs.python.org/3/library/concurrent.futures.html
        """
        try:
            urls = self._get_all_page_urls()
            if not urls:
                print("Warning: No pages found to scrape")
                return []

            try:
                return self._scrape_multithreaded(urls)
            except Exception as e:
                print(f"Multithreading failed ({e}), falling back to single-threaded")
                return self._scrape_singlethreaded(urls)
        except Exception as e:
            print(f"Scraping failed completely: {e}")
            return []

    def _get_all_page_urls(self) -> List[str]:
        """Get all page URLs with better pagination handling"""
        urls = []
        next_url = self.base_url

        while next_url and len(urls) < 10:  # Safety limit
            urls.append(next_url)
            page_content = self.fetch_page(next_url)
            if not page_content:
                break

            soup = BeautifulSoup(page_content, "html.parser")
            next_button = soup.find("li", class_="next")
            if not next_button or not next_button.a:
                break

            next_url = urljoin(self.base_url, next_button.a.get("href", ""))
            if not next_url or next_url in urls:
                break

        return urls

    def _scrape_multithreaded(self, urls: List[str]) -> List[Dict]:
        """Multithreaded scraping with progress tracking"""
        quotes = []
        with self.executor as executor:
            future_to_url = {executor.submit(self._scrape_page, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    page_quotes = future.result()
                    if page_quotes:
                        quotes.extend(page_quotes)
                        print(f"Scraped {len(page_quotes)} quotes from {url}")
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
        return quotes

    def _scrape_singlethreaded(self, urls: List[str]) -> List[Dict]:
        """Fallback single-threaded scraping"""
        quotes = []
        for url in urls:
            page_quotes = self._scrape_page(url)
            if page_quotes:
                quotes.extend(page_quotes)
                print(f"Scraped {len(page_quotes)} quotes from {url}")
            time.sleep(self.delay)  # Add delay between requests
        return quotes

    def _scrape_page(self, url: str) -> List[Dict]:
        """Scrape a single page with robust parsing"""
        page_content = self.fetch_page(url)
        if not page_content:
            return []

        try:
            soup = BeautifulSoup(page_content, "html.parser")
            quote_divs = soup.find_all("div", class_="quote")

            if not quote_divs:
                print(f"Warning: No quotes found on {url}")
                return []

            return self._parse_quotes(quote_divs)
        except Exception as e:
            print(f"Error parsing {url}: {e}")
            return []

    def _parse_quotes(self, quote_divs: List) -> List[Dict]:
        """Parse quote divs with validation and include links"""
        quotes = []
        for quote_div in quote_divs:
            try:
                text_elem = quote_div.find("span", class_="text")
                author_elem = quote_div.find("small", class_="author")
                tag_elems = quote_div.select(".tags a")
                quote_link = quote_div.find("a", href=True)  # Get the quote's individual page link

                if not (text_elem and author_elem):
                    continue

                text = text_elem.get_text(strip=True)
                author = author_elem.get_text(strip=True)
                tags = [tag.get_text(strip=True) for tag in tag_elems if tag]
                link = urljoin(self.base_url, quote_link['href']) if quote_link else ""

                if text and author:
                    quotes.append({
                        "text": text,
                        "author": author,
                        "tags": tags,
                        "link": link  # Add the quote's individual page link
                    })
            except Exception as e:
                print(f"Error parsing quote: {e}")
                continue

        return quotes
# ====================== STORAGE HANDLERS ======================
class QuoteStorage:
    """Handles saving quotes to various file formats with validation
    JSON docs: https://docs.python.org/3/library/json.html
    CSV docs: https://docs.python.org/3/library/csv.html
    Pathlib docs: https://docs.python.org/3/library/pathlib.html
    """

    @staticmethod
    def save_to_json(quotes: List[Dict], filename: str) -> bool:
        """Save quotes to JSON file with error handling"""
        try:
            path = Path(filename)
            with path.open('w', encoding='utf-8') as f:
                json.dump(quotes, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved {len(quotes)} quotes to {filename}")
            return True
        except Exception as e:
            print(f"Error saving to JSON: {e}")
            return False

    @staticmethod
    def save_to_csv(quotes: List[Dict], filename: str) -> bool:
        """Save quotes to CSV file with error handling"""
        try:
            path = Path(filename)
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['text', 'author', 'tags', 'link'])
                writer.writeheader()
                for quote in quotes:
                    quote_copy = quote.copy()
                    quote_copy['tags'] = ', '.join(quote['tags'])
                    writer.writerow(quote_copy)
            print(f"Successfully saved {len(quotes)} quotes to {filename}")
            return True
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False

    @staticmethod
    def save_to_txt(quotes: List[Dict], filename: str) -> bool:
        """Save quotes to plain text file with error handling"""
        try:
            path = Path(filename)
            with path.open('w', encoding='utf-8') as f:
                for quote in quotes:
                    f.write(f"\"{quote['text']}\"\n")
                    f.write(f"— {quote['author']}\n")
                    f.write(f"Tags: {', '.join(quote['tags'])}\n")
                    f.write(f"Link: {quote.get('link', 'N/A')}\n\n")
            print(f"Successfully saved {len(quotes)} quotes to {filename}")
            return True
        except Exception as e:
            print(f"Error saving to TXT: {e}")
            return False

    @staticmethod
    def save_tag_analysis(quotes: List[Dict], filename: str) -> bool:
        """Save tag analysis to a file"""
        try:
            analysis = TagAnalyzer.display_tag_analysis(quotes)
            path = Path(filename)
            with path.open('w', encoding='utf-8') as f:
                f.write(analysis)
            print(f"Successfully saved tag analysis to {filename}")
            return True
        except Exception as e:
            print(f"Error saving tag analysis: {e}")
            return False


# ====================== GUI APPLICATION ======================
class QuoteScraperApp:
    """Tkinter GUI application for the quote scraper
    Tkinter docs: https://docs.python.org/3/library/tkinter.html
    Threading docs: https://docs.python.org/3/library/threading.html
    """
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Quote Scraper")
        self.root.geometry("800x600")
        self.scraper = QuoteScraper()
        self.quotes = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="Scrape Quotes", command=self._start_scraping).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save to JSON", command=lambda: self._save_quotes('json')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save to CSV", command=lambda: self._save_quotes('csv')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save to TXT", command=lambda: self._save_quotes('txt')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Analyze Tags", command=self._analyze_tags).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Save Analysis", command=lambda: self._save_quotes('analysis')).pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        # Status label
        self.status = ttk.Label(main_frame, text="Ready to scrape quotes", relief=tk.SUNKEN)
        self.status.pack(fill=tk.X, pady=5)

        # Quote display
        self.quote_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD)
        self.quote_display.pack(fill=tk.BOTH, expand=True)
        self.quote_display.config(state=tk.DISABLED)

    def _update_status(self, message: str):
        """Update the status label"""
        self.status.config(text=message)
        self.root.update_idletasks()

    def _display_quotes(self):
        """Display quotes in the text widget with links"""
        self.quote_display.config(state=tk.NORMAL)
        self.quote_display.delete(1.0, tk.END)

        if not self.quotes:
            self.quote_display.insert(tk.END, "No quotes to display")
        else:
            for i, quote in enumerate(self.quotes, 1):
                self.quote_display.insert(tk.END, f"{i}. \"{quote['text']}\"\n")
                self.quote_display.insert(tk.END, f"   — {quote['author']}\n")
                self.quote_display.insert(tk.END, f"   Tags: {', '.join(quote['tags'])}\n")
                if quote.get('link'):
                    self.quote_display.insert(tk.END, f"   Link: {quote['link']}\n\n")
                else:
                    self.quote_display.insert(tk.END, "   Link: N/A\n\n")

        self.quote_display.config(state=tk.DISABLED)

    def _start_scraping(self):
        """Start the scraping process in a separate thread"""
        self._update_status("Scraping in progress...")
        self.progress["value"] = 0
        self.quote_display.config(state=tk.NORMAL)
        self.quote_display.delete(1.0, tk.END)
        self.quote_display.insert(tk.END, "Scraping quotes... Please wait.")
        self.quote_display.config(state=tk.DISABLED)

        # Disable buttons during scraping
        for child in self.root.winfo_children():
            for btn in child.winfo_children():
                if isinstance(btn, ttk.Button):
                    btn.config(state=tk.DISABLED)

        Thread(target=self._scrape_quotes_thread, daemon=True).start()

    def _scrape_quotes_thread(self):
        """Thread function for scraping quotes"""
        try:
            self.quotes = self.scraper.scrape_all_quotes()
            self.progress["value"] = 100
            self._display_quotes()
            self._update_status(f"Successfully scraped {len(self.quotes)} quotes")
        except Exception as e:
            self._update_status(f"Error: {str(e)}")
            self.quote_display.config(state=tk.NORMAL)
            self.quote_display.delete(1.0, tk.END)
            self.quote_display.insert(tk.END, f"Error occurred: {str(e)}")
            self.quote_display.config(state=tk.DISABLED)
        finally:
            # Re-enable buttons
            for child in self.root.winfo_children():
                for btn in child.winfo_children():
                    if isinstance(btn, ttk.Button):
                        btn.config(state=tk.NORMAL)

    def _analyze_tags(self):
        """Display tag analysis in the quote display"""
        if not self.quotes:
            messagebox.showwarning("No Quotes", "No quotes to analyze. Please scrape first.")
            return

        analysis = TagAnalyzer.display_tag_analysis(self.quotes)

        self.quote_display.config(state=tk.NORMAL)
        self.quote_display.delete(1.0, tk.END)
        self.quote_display.insert(tk.END, analysis)
        self.quote_display.config(state=tk.DISABLED)
        self._update_status("Tag analysis completed")

    def _save_quotes(self, format_type: str):
        """Save quotes to a file in the specified format"""
        if not self.quotes:
            messagebox.showwarning("No Quotes", "No quotes to save. Please scrape first.")
            return

        if format_type == 'analysis':
            filename = "tag_analysis.txt"
            success = QuoteStorage.save_tag_analysis(self.quotes, filename)
        else:
            filename = f"quotes.{format_type}"
            if format_type == 'json':
                success = QuoteStorage.save_to_json(self.quotes, filename)
            elif format_type == 'csv':
                success = QuoteStorage.save_to_csv(self.quotes, filename)
            elif format_type == 'txt':
                success = QuoteStorage.save_to_txt(self.quotes, filename)
            else:
                messagebox.showerror("Error", f"Unknown format: {format_type}")
                return

        if success:
            messagebox.showinfo("Success", f"Saved to {filename}")
            self._update_status(f"Saved to {filename}")
        else:
            messagebox.showerror("Error", f"Failed to save to {filename}")


# ====================== TEST CASES ======================
class TestQuoteScraper(unittest.TestCase):
    """Enhanced unit tests with better diagnostics
    Unittest docs: https://docs.python.org/3/library/unittest.html
    """
    @classmethod
    def setUpClass(cls):
        cls.scraper = QuoteScraper()
        print("\nStarting scraping test...")
        cls.test_quotes = cls.scraper.scrape_all_quotes()
        print(f"Scraped {len(cls.test_quotes)} quotes in test setup")

    def test_quote_count(self):
        """Test that we scraped at least one quote"""
        self.assertGreater(len(self.test_quotes), 0,
                         f"Failed to scrape quotes. Robots.txt allowed: {self.scraper.robots_txt}")

    def test_quote_structure(self):
        """Test the structure of scraped quotes"""
        for i, quote in enumerate(self.test_quotes):
            with self.subTest(quote=i):
                self.assertIn("text", quote, f"Quote {i} missing text")
                self.assertIn("author", quote, f"Quote {i} missing author")
                self.assertIn("tags", quote, f"Quote {i} missing tags")


class TestTagAnalyzer(unittest.TestCase):
    """Tests for the TagAnalyzer class"""
    def test_count_tags(self):
        """Test tag counting functionality"""
        test_quotes = [
            {"text": "Quote 1", "author": "Author 1", "tags": ["love", "life"]},
            {"text": "Quote 2", "author": "Author 2", "tags": ["life", "wisdom"]},
            {"text": "Quote 3", "author": "Author 3", "tags": ["love"]}
        ]

        counts = TagAnalyzer.count_tags(test_quotes)
        self.assertEqual(counts["love"], 2)
        self.assertEqual(counts["life"], 2)
        self.assertEqual(counts["wisdom"], 1)

    def test_top_tags(self):
        """Test top tags functionality"""
        test_quotes = [
            {"text": "Quote 1", "author": "Author 1", "tags": ["a", "b", "c"]},
            {"text": "Quote 2", "author": "Author 2", "tags": ["a", "b"]},
            {"text": "Quote 3", "author": "Author 3", "tags": ["a"]}
        ]

        top_tags = TagAnalyzer.get_top_tags(test_quotes, 2)
        self.assertEqual(top_tags, [("a", 3), ("b", 2)])


# ====================== MAIN EXECUTION ======================
def main():
    """Main function to run either GUI or CLI version"""
    # Run tests first
    print("Running tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)

    # Ask user for mode
    choice = input("\nRun in (G)UI or (C)LI mode? [G/c]: ").strip().lower()

    if choice == 'c':
        # CLI mode
        print("\nRunning in CLI mode...")
        scraper = QuoteScraper()
        quotes = scraper.scrape_all_quotes()

        if quotes:
            print(f"\nSuccessfully scraped {len(quotes)} quotes:")
            for i, quote in enumerate(quotes[:5], 1):
                print(f"\n{i}. \"{quote['text']}\"")
                print(f"   — {quote['author']}")
                print(f"   Tags: {', '.join(quote['tags'])}")
                print(f"   Link: {quote.get('link', 'N/A')}")  # Show the link

            # Save data and analysis
            QuoteStorage.save_to_json(quotes, "quotes.json")
            QuoteStorage.save_to_csv(quotes, "quotes.csv")
            QuoteStorage.save_to_txt(quotes, "quotes.txt")
            QuoteStorage.save_tag_analysis(quotes, "tag_analysis.txt")

            print("\nTag Analysis:")
            print(TagAnalyzer.display_tag_analysis(quotes))
        else:
            print("No quotes were scraped.")
    else:
        # GUI mode (default)
        print("\nRunning in GUI mode...")
        root = tk.Tk()
        app = QuoteScraperApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()