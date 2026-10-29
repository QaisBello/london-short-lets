# Decision memo: where to look first for full-time short lets in London

**For:** a London housing or planning-enforcement team. **Data:** Inside Airbnb, London, scraped 18-22 September 2026.

## The question

Where is London's short-let supply concentrating, and which homes look like full-time rentals rather than occasional lets?

## The answer

- **12,550 entire homes** (38% of the 33,243 active entire homes taking short stays) are modelled above 90 booked nights in the last 12 months.
- **Five boroughs hold half of them (51%):**

  | Borough | Homes | Share of London's total |
  |---|---:|---:|
  | Westminster | 2,442 | 19% |
  | Kensington & Chelsea | 1,224 | 10% |
  | Camden | 1,168 | 9% |
  | Tower Hamlets | 788 | 6% |
  | Islington | 737 | 6% |

- **It is not only large operators.** By the host's number of London listings:

  | Host's listings | Share of the over-90 homes |
  |---|---:|
  | 20+ | 25% (3,172) |
  | 1 | 29% (3,579) |
  | 2-4 | 20% |
  | 5-19 | 26% |

## Recommendation

1. **Start in the five boroughs above**, beginning with Westminster, where 46% of active short-stay entire homes are over the line.
2. **Within them, look at two groups first:** homes modelled far above 90 nights (3,543 sit at the model's 255-night cap), and hosts with many listings, where one contact covers many homes.
3. **Ask for planning permission before assuming a breach.** Airbnb blocks London entire homes at 90 nights unless the host declares permission, so a home above the line may well have it.
4. **Use one occupancy number.** Report the certified rate: **26.4%** for active listings. The 13.5% and 57.7% figures also circulating come from different definitions and should not be compared with it.

## How sure are we?

The count depends on how many stays leave a review:

| Share of stays reviewed | Homes above 90 nights |
|---|---:|
| 72% (the most cautious) | 8,490 (26%) |
| 50% (default) | 12,550 (38%) |
| 30.5% | 16,755 (50%) |

The top five boroughs are the same, in the same order, under all three assumptions.

## Why "occupancy" needs one definition

The same snapshot gives four answers:

| Definition | London | Status |
|---|---:|---|
| Modelled, active listings | 26.4% | Certified |
| Modelled, all listings | 13.5% | Dormant listings dilute it |
| Booked share of bookable nights | 33.9% | Mixes last year with next year |
| Calendar unavailable | 57.7% | A night the host blocked looks the same as a booked one |

Each metric is now defined once, in `metrics.yml`, and the web page, Power BI and Excel all read the same published table.

*Full analysis: https://qaisbello.github.io/data-engineering/london-short-lets/ · Not legal advice.*
