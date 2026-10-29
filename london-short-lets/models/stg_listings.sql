-- One row per listing, typed, with only the columns the metrics need. Names and free text are dropped.
select
    cast(id as bigint)                                                as listing_id,
    cast(host_id as bigint)                                           as host_id,
    cast(last_scraped as date)                                        as scraped_on,
    cast(calendar_last_scraped as date)                               as calendar_scraped_on,
    neighbourhood_cleansed                                            as borough,
    room_type,
    try_cast(latitude as double)                                      as latitude,
    try_cast(longitude as double)                                     as longitude,
    try_cast(try_cast(minimum_nights as double) as integer)           as minimum_nights,
    try_cast(number_of_reviews_ltm as integer)                        as reviews_ltm_source,
    try_cast(estimated_occupancy_l365d as integer)                    as est_nights_source,
    try_cast(availability_365 as integer)                             as availability_365_source,
    try_cast(calculated_host_listings_count as integer)               as host_listings,
    try_cast(calculated_host_listings_count_entire_homes as integer)  as host_entire_homes,
    try_cast(first_review as date)                                    as first_review,
    try_cast(last_review as date)                                     as last_review
from read_csv('{raw}/listings.csv.gz', all_varchar = true, header = true)
