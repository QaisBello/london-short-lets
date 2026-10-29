-- The one table every metric reads. Parameters come from metrics.yml, so changing an assumption changes every metric at once.
select
    l.listing_id, l.host_id, l.borough, l.room_type, l.latitude, l.longitude, l.minimum_nights, l.host_listings,
    case when l.host_listings = 1 then '1 listing' when l.host_listings <= 4 then '2-4 listings'
         when l.host_listings <= 19 then '5-19 listings' else '20+ listings' end                     as host_size,
    coalesce(r.reviews_ltm, 0)                                                                       as reviews_ltm,
    coalesce(r.reviews_ltm, 0) > 0                                                                   as is_active,
    l.room_type = 'Entire home/apt'                                                                  as is_entire_home,
    l.minimum_nights < {short_let_limit_nights}                                                      as is_short_let,
    least(round(coalesce(r.reviews_ltm, 0) / {review_rate} * greatest({avg_stay_nights}, l.minimum_nights)),
          floor(365 * {occupancy_cap}))                                                              as modelled_nights,
    c.nights_open, c.nights_unavailable, c.calendar_nights,
    l.est_nights_source, l.reviews_ltm_source, l.availability_365_source
from stg_listings l
left join stg_reviews_ltm r using (listing_id)
left join stg_calendar_365 c using (listing_id)
