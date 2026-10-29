# The occupancy model

Airbnb does not publish bookings. Inside Airbnb estimates them from reviews (its "San Francisco model"), and this project reproduces that estimate exactly from the raw review log, so the number is traceable rather than copied.

```
modelled nights = min( round( reviews in the last 12 months / review rate × max(average stay, minimum stay) ), floor(365 × cap) )
```

| Parameter | Value | Where it comes from |
|---|---|---|
| Review rate | 50% | Inside Airbnb's default. It publishes 72% (attributed to Airbnb's CEO, unverified) and 30.5% (a New York comparison) as the range. |
| Average stay | 4.6 nights | Recovered from the data: every listing's published estimate equals reviews × 2 × max(4.6, minimum stay). |
| Cap | 70% of the year (255 nights) | Inside Airbnb caps occupancy so stale minimum stays and heavy reviewers can't push a listing to a full year. |

**Reproduction check.** The pipeline rebuilds reviews in the last 12 months from `reviews.csv` (an inclusive 365-day window up to the scrape day) and recomputes modelled nights. Both match the listings file for all 91,954 listings. These are two error-level checks: if Inside Airbnb changes its method, the build stops instead of quietly publishing different numbers.

**The 90-night line.** In Greater London, short-letting a home for more than 90 nights in a calendar year needs planning permission: section 25A of the Greater London Council (General Powers) Act 1973, inserted by section 44 of the Deregulation Act 2015 ([summary](https://anthonygold.co.uk/latest/blog/short-term-lets)). Since 2017, Airbnb has automatically blocked London entire homes after 90 nights unless the host declares permission ([summary](https://www.kingsleynapley.co.uk/our-insights/articles/are-you-a-responsible-host-airbnb-enforces-90-night-annual-limit-for-london-hosts/)).

So an entire home modelled above 90 nights is a **flag to check**, not a finding of a breach:
- the host may have planning permission;
- the estimate may be high (the review rate and average stay are assumptions);
- the model covers the 12 months before the scrape, while the rule counts calendar years.

Listings with a minimum stay of 90 nights or more are not short lets, so they are excluded. So are the 309 listings with no minimum stay in the source.

Source of the assumptions: [insideairbnb.com/data-assumptions](https://insideairbnb.com/data-assumptions/).
