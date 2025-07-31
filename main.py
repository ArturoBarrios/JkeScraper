from typing import Union
import os

from fastapi import FastAPI, Response

app = FastAPI()



# @app.post("/scrape-nytimes")
# async def scrapeNYTimes():
    


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