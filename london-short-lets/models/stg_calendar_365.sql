-- Per listing: open and unavailable nights in the 365 days from the day its calendar was scraped.
-- The calendar cannot tell a booked night from a night the host blocked; both show as unavailable.
with cal as (
    select cast(listing_id as bigint) as listing_id, cast("date" as date) as night, available = 't' as is_open
    from read_csv('{raw}/calendar.csv.gz', header = true, columns = {{'listing_id': 'VARCHAR', 'date': 'VARCHAR', 'available': 'VARCHAR', 'minimum_nights': 'VARCHAR', 'maximum_nights': 'VARCHAR'}})
)
select c.listing_id,
       count(*)                                  as calendar_nights,
       count(*) filter (where c.is_open)         as nights_open,
       count(*) filter (where not c.is_open)     as nights_unavailable
from cal c join stg_listings l using (listing_id)
where c.night >= l.calendar_scraped_on and c.night < l.calendar_scraped_on + interval 365 day
group by 1
