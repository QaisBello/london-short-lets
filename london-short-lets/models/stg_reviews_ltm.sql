-- Per listing: reviews in the 12 months up to and including the scrape day (inclusive window, as Inside Airbnb counts it).
select r.listing_id, count(*) as reviews_ltm
from (select cast(listing_id as bigint) as listing_id, cast("date" as date) as reviewed_on
      from read_csv('{raw}/reviews.csv.gz', header = true, all_varchar = true)) r
join stg_listings l using (listing_id)
where r.reviewed_on >= l.scraped_on - interval 365 day and r.reviewed_on <= l.scraped_on
group by 1
