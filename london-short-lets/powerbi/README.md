# London short lets: Power BI

The Power BI consumer of the metric layer. It defines nothing of its own: it reads the published metric table and re-aggregates it with one generic measure.

This folder is a Power BI project (`London_Short_Lets.pbip`): a TMDL semantic model and a PBIR report, generated from one Python spec, checked against Microsoft's JSON schemas, with every card recomputed independently.

## Open it

1. Open **`London_Short_Lets.pbip`** in Power BI Desktop. In versions before mid-2025, first turn on the preview features for Power BI Project (.pbip), the TMDL model format and the PBIR report format.
2. Click **Refresh**. The model reads `data/published/` from GitHub through the **BaseUrl** parameter. If asked, choose **Anonymous** access for `raw.githubusercontent.com`.
3. Check the visuals against [`docs/expected_values.md`](docs/expected_values.md).

## Pages

- **One number:** five headline cards; London occupancy under all four definitions (only one certified); the metric registry with versions and hashes.
- **Where:** entire homes likely over 90 nights by borough, and a borough table with active listings, occupancy and the over-90 share.
- **Metric explorer:** pick a metric and a dimension. One measure serves every combination. Pick one of each: with nothing selected, different metrics would be added together.
- **Who and how sure:** over-90 homes by host size, the review-rate sensitivity, and the quality checks behind every number.

## Model

- **Tables:** Metric Values (the published table), Definitions (the registry), Quality Report, Sensitivity.
- **Relationship:** Metric Values[metric_id] to Definitions[id].
- **The generic measure:**

  ```dax
  Metric Value =
  VAR num = SUM ( 'Metric Values'[numerator] )
  VAR den = SUM ( 'Metric Values'[denominator] )
  RETURN IF ( ISBLANK ( den ), num, DIVIDE ( num, den ) )
  ```

  Counts and sums have no denominator and add up. Ratios sum their parts, then divide. The other 15 measures only pick a metric and a dimension. All DAX is in [`docs/measures.md`](docs/measures.md).

## Rebuild and check

```bash
pip install jsonschema referencing pandas
python tools/spec.py
python tools/validate.py
python tools/expected.py
```
