# ClaimReview export (S-04)

Chronicle provides a schema.org `ClaimReview` interoperability profile for investigation claims.

## API

`chronicle.store.commands.generic_export.build_claimreview_export(read_model, get_defensibility_score, investigation_uid, *, claim_limit=10000, publisher_name="Chronicle")`

Returns an `ItemList` containing one `ClaimReview` per active claim with available defensibility.

## Rating mapping

Chronicle defensibility labels map to `reviewRating` as:

| `provenance_quality` | `ratingValue` | `alternateName` |
|---|---:|---|
| `strong` | 4 | Supported |
| `medium` | 3 | Mostly Supported |
| `weak` | 2 | Weakly Supported |
| `challenged` | 1 | Challenged |

## Caveats

1. Chronicle exports defensibility posture, not absolute truth verdicts.
2. ClaimReview entries are derived from Chronicle support/challenge/tension structure and policy-relative scoring.
3. Consumers should display Chronicle caveats alongside ratings to avoid overclaiming certainty.
