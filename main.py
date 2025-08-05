from typing import Union
import os
from nytimes import NYTimesScraper

from fastapi import FastAPI, Response, Query

app = FastAPI()



@app.post("/scrape-nytimes")
async def scrape_nytimes(max_stories: int = Query(default=5, description="Number of stories to scrape")):
    """Trigger NYTimes scraping and send articles to API"""
    try:
        scraper = NYTimesScraper()
        stories = scraper.scrape_stories_with_content(max_stories=max_stories)
        
        return {
            "success": True,
            "message": f"Successfully processed {len(stories)} stories",
            "stories_count": len(stories),
            "requested_count": max_stories
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to scrape NYTimes"
        }


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/get-scraped-jokes")
def get_scraped_jokes():
    jokes_dir = "jokes"
    combined = []
    print(f"Reading files from directory: {jokes_dir}")
    for filename in os.listdir(jokes_dir):
        file_path = os.path.join(jokes_dir, filename)
        print(f"Processing file: {file_path}")
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"Read {len(content)} characters from {filename}")
                combined.append(f"--- {filename} ---\n{content}\n")
    result = "\n".join(combined)
    output_file = "combined_jokes.txt"
    with open(output_file, "w", encoding="utf-8") as out_f:
        out_f.write(result)
        print(f"Combined jokes written to {output_file}")
    
    return Response(content=result, media_type="text/plain")