# Raw data (not committed)

Download the London snapshot from [insideairbnb.com/get-the-data](https://insideairbnb.com/get-the-data/) (September 2026, scraped 18-22 September) and put these files here:

- `listings.csv.gz`
- `calendar.csv.gz`
- `reviews.csv.gz` (gzip the plain `reviews.csv` if that's what you downloaded)

`python src/pipeline.py` then stages them into `data/staged/`. Without them it rebuilds from the committed `data/staged/` files, with identical results.
