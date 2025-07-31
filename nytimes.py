import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
import random
import os
import json

class NYTimesScraper:
    def __init__(self):
        self.session = requests.Session()
        base_api_url = os.getenv('CAPI_URL', 'http://localhost:4000')
        self.api_url = f"{base_api_url}/news/create"
        # Rotate user agents to appear more human-like
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        self.update_headers()
        self.base_url = "https://www.nytimes.com"
    
    def update_headers(self):
        """Update headers with random user agent and additional headers"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        self.session.headers.update(headers)
    
    def get_homepage_stories(self):
        """Scrape stories from NY Times homepage"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            stories = []
            
            # Look for story containers using multiple selectors
            story_selectors = [
                '[data-tpl="sli"]',  # Story list item
                '.story-wrapper',    # Story wrapper
                'article',           # Article tags
                '[class*="story"]'   # Any class containing "story"
            ]
            
            for selector in story_selectors:
                story_elements = soup.select(selector)
                if story_elements:
                    print(f"Found {len(story_elements)} stories using selector: {selector}")
                    break
            
            for story_element in story_elements[:10]:  # Limit to first 10 stories
                story_data = self.extract_story_data(story_element)
                if story_data:
                    stories.append(story_data)
            
            return stories
            
        except Exception as e:
            print(f"Error scraping homepage: {e}")
            return []
    
    def extract_story_data(self, element):
        """Extract title, summary, and link from story element"""
        story_data = {}
        
        # Find title using multiple approaches
        title_selectors = [
            '[data-tpl="h"] a',
            'h1 a', 'h2 a', 'h3 a',
            '.indicate-hover',
            '[class*="headline"]',
            'a[href*="/2025/"]'  # Links to 2025 articles
        ]
        
        title_element = None
        link = None
        
        for selector in title_selectors:
            elements = element.select(selector)
            if elements:
                title_element = elements[0]
                if title_element.get('href'):
                    link = title_element.get('href')
                break
        
        if not title_element:
            return None
        
        # Extract title text
        title = title_element.get_text(strip=True)
        if not title or len(title) < 10:  # Skip if title too short
            return None
        
        story_data['title'] = title
        
        # Make link absolute
        if link:
            if link.startswith('/'):
                link = urljoin(self.base_url, link)
            story_data['link'] = link
        
        # Find summary/description
        summary_selectors = [
            '.summary-class',
            '[class*="summary"]',
            'p[class*="css-"]',  # Generic paragraph with CSS class
            '.css-sarx3u p'      # Specific to the example
        ]
        
        summary = ""
        for selector in summary_selectors:
            summary_elements = element.select(selector)
            if summary_elements:
                summary = summary_elements[0].get_text(strip=True)
                if len(summary) > 20:  # Only use if substantial
                    break
        
        story_data['summary'] = summary
        
        # Extract timestamp if available
        time_selectors = ['time', '[datetime]', '[data-time]']
        for selector in time_selectors:
            time_elements = element.select(selector)
            if time_elements:
                time_text = time_elements[0].get_text(strip=True)
                story_data['timestamp'] = time_text
                break
        
        return story_data
    
    def get_full_article(self, url):
        """Scrape full article content from article URL with multiple fallback strategies"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"Fetching article (attempt {attempt + 1}): {url}")
                
                # Update headers for each request
                self.update_headers()
                
                # Add referrer to look more natural
                headers = {'Referer': self.base_url}
                
                # Random delay between requests
                time.sleep(random.uniform(2, 5))
                
                response = self.session.get(url, headers=headers, timeout=15)
                
                # Handle different status codes
                if response.status_code == 403:
                    print(f"Access forbidden (403) for {url}")
                    if attempt < max_retries - 1:
                        print(f"Retrying with different approach...")
                        time.sleep(random.uniform(5, 10))
                        continue
                    else:
                        return self.try_alternative_access(url)
                
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                return self.extract_article_content(soup)
                
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                    continue
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    continue
        
        print(f"Failed to fetch article after {max_retries} attempts")
        return []
    
    def try_alternative_access(self, url):
        """Try alternative methods to access the article"""
        print("Trying alternative access methods...")
        
        # Try accessing through Google Cache (if available)
        # Or try a different approach with minimal headers
        try:
            minimal_session = requests.Session()
            minimal_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)',
            })
            
            response = minimal_session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self.extract_article_content(soup)
            else:
                print(f"Alternative access failed with status: {response.status_code}")
                
        except Exception as e:
            print(f"Alternative access error: {e}")
        
        return []
    
    def extract_article_content(self, soup):
        """Extract article content from BeautifulSoup object"""
        # Look for article body using multiple selectors
        article_selectors = [
            'section[name="articleBody"]',
            '.StoryBodyCompanionColumn',
            '[data-testid*="companionColumn"]',
            '.css-s99gbd',
            'section.meteredContent',
            '.css-at9mc1',  # Specific paragraph class from your example
            '[class*="story-body"]',
            '.article-body'
        ]
        
        article_content = []
        
        for selector in article_selectors:
            content_sections = soup.select(selector)
            if content_sections:
                print(f"Found content using selector: {selector}")
                for section in content_sections:
                    # Extract paragraphs
                    paragraphs = section.select('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        # Filter out short paragraphs and ads
                        if len(text) > 50 and not self.is_ad_content(text):
                            article_content.append(text)
                if article_content:  # If we found content, break
                    break
        
        # If no structured content found, try broader search
        if not article_content:
            print("No structured content found, trying broader search...")
            all_paragraphs = soup.select('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 100 and not self.is_ad_content(text):
                    article_content.append(text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_content = []
        for paragraph in article_content:
            if paragraph not in seen:
                seen.add(paragraph)
                unique_content.append(paragraph)
        
        return unique_content
    
    def is_ad_content(self, text):
        """Check if text is likely advertisement or non-article content"""
        ad_indicators = [
            'subscribe', 'subscription', 'advertisement', 
            'support our journalism', 'times access',
            'play these games', 'connections', 'spelling bee',
            'crossword', 'newsletter', 'sign up', 'log in',
            'create account', 'paywall', 'digital subscription'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in ad_indicators)
    
    def send_story_to_api(self, story):
        """Send story data to the API endpoint"""
        try:
            # Prepare the payload
            payload = {
                'title': story.get('title', ''),
                'summary': story.get('summary', ''),
                'content': '\n\n'.join(story.get('full_content', [])) if story.get('full_content') else '',
                'date': story.get('timestamp', '')
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'NYTimesScraper/1.0'
            }
            
            print(f"Sending story to API: {self.api_url}")
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=10
            )
            
            if response.status_code == 200 or response.status_code == 201:
                print(f"✓ Successfully sent story: {story['title'][:50]}...")
                return True
            else:
                print(f"✗ API error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Failed to send story to API: {e}")
            return False
    
    def scrape_stories_with_content(self, max_stories=5):
        """Main method to scrape homepage and get full article content"""
        print("Scraping NY Times homepage...")
        stories = self.get_homepage_stories()
        
        if not stories:
            print("No stories found on homepage")
            return []
        
        print(f"Found {len(stories)} stories on homepage")
        
        detailed_stories = []
        successful_sends = 0
        
        for i, story in enumerate(stories[:max_stories]):
            print(f"\nProcessing story {i+1}: {story['title'][:50]}...")
            
            if 'link' in story:
                article_content = self.get_full_article(story['link'])
                story['full_content'] = article_content
                story['content_length'] = len(article_content)
                
                if article_content:
                    print(f"Successfully extracted {len(article_content)} paragraphs")
                else:
                    print("No content extracted")
            
            # Send story to API
            if self.send_story_to_api(story):
                successful_sends += 1
            
            detailed_stories.append(story)
        
        print(f"\n✓ Successfully sent {successful_sends}/{len(detailed_stories)} stories to API")
        return detailed_stories

def main():
    scraper = NYTimesScraper()
    stories = scraper.scrape_stories_with_content(max_stories=3)
    
    for i, story in enumerate(stories, 1):
        print(f"\n{'='*50}")
        print(f"STORY {i}")
        print(f"{'='*50}")
        print(f"Title: {story['title']}")
        
        if 'summary' in story and story['summary']:
            print(f"\nSummary: {story['summary']}")
        
        if 'timestamp' in story:
            print(f"Time: {story['timestamp']}")
        
        if 'link' in story:
            print(f"Link: {story['link']}")
        
        if 'full_content' in story and story['full_content']:
            print(f"\nFull Article ({story['content_length']} paragraphs):")
            print("-" * 30)
            for j, paragraph in enumerate(story['full_content'][:5]):  # Show first 5 paragraphs
                print(f"{j+1}. {paragraph}")
            
            if len(story['full_content']) > 5:
                print(f"\n... and {len(story['full_content']) - 5} more paragraphs")
        else:
            print("\nNo full content available")

if __name__ == "__main__":
    main()