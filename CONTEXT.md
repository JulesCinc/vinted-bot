# Vinted GPU Watcher

A bot that watches vinted.fr for GPU listings and alerts the user when one is priced below what that GPU model typically sells for, in that condition. Detect-and-alert only; it never reserves or buys.

## Language

**Listing**:
A single GPU offered for sale on vinted.fr at a given point in time, with its own price, condition, and seller.
_Avoid_: Item, product, ad.

**GPU Model**:
The specific graphics card model a Listing is for (e.g. "RTX 3070"), independent of condition or price. Two Listings can share a GPU Model.
_Avoid_: Card, product line.

**Condition**:
The Listing's stated wear/functional state (Vinted's own condition scale, e.g. new/very good/good/satisfactory). Market Price Baseline is always scoped to a GPU Model *and* a Condition together, not the model alone.

**Market Price Baseline**:
The typical price a given GPU Model in a given Condition sells for, against which a Listing's price is judged. Not a price the user sets by hand.
_Avoid_: Fair price, reference price, threshold (threshold implies a fixed number, which this isn't).

**Underpriced Listing**:
A Listing whose price falls far enough below its Market Price Baseline to be worth surfacing to the user.
_Avoid_: Deal, bargain, cheap listing.

**Alert**:
A notification sent to the user about one Underpriced Listing. Sent at most once per Listing, ever — a Listing that already triggered an Alert is never Alerted again, even if its price drops further afterward.
_Avoid_: Notification (reserve for generic/system use), ping.

**Pass**:
One run of the bot: check every tracked GPU Model against Vinted, recompute Market Price Baselines, and send any resulting Alerts. Runs once daily. A Pass can end early — e.g. aborted partway through after an anti-bot block — in which case GPU Models already checked before the abort are still processed normally, and the untried remainder waits for tomorrow's Pass.
_Avoid_: Run (ambiguous with "the bot's process" generally), cycle, check.
