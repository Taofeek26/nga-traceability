"""Randomised, quota-respecting allocation of a lot's volume across farmers.

The problem this solves: a lot arrives from a broker with a single total
weight. Nobody recorded which farmer supplied how much. All we know is:
  - the lot's total volume
  - how many receipts were issued for it (receipt_start..receipt_end)
  - each farmer's remaining quota (potential_volume_kg - delivered so far)

This module picks a random set of farmers (one per receipt) whose combined
remaining quota can cover the lot, then splits the volume across them
randomly so that no farmer's running total ever exceeds their quota.
"""
import random


class AllocationError(Exception):
    pass


#: Spread mode caps each chosen farmer's contribution to this one lot at a
#: random fraction of their remaining quota (see _apply_spread_cap) so a
#: farmer's whole remaining potential isn't plausibly used up in a single
#: delivery - real farmers deliver incrementally over a season.
SPREAD_FRACTION_RANGE = (0.45, 0.9)


def allocate_lot(eligible_farmers, lot_volume, n_receipts, max_retries=40, min_share=1.0,
                  required_ids=None, spread_mode=False):
    """
    eligible_farmers: list of (farmer_code, remaining_capacity_kg), capacity > 0 only
    lot_volume: total kg to split
    n_receipts: how many farmers/receipts this lot must be split across
                (= receipt_end - receipt_start + 1)
    required_ids: optional set of farmer codes that must be included in the
                  chosen subset if they're in eligible_farmers (the "search
                  and prefer specific farmers" option on the new-lot form).
    spread_mode: if True, cap each chosen farmer's allocation to a random
                 fraction of their remaining quota instead of allowing up
                 to the full remaining amount in one lot (see
                 SPREAD_FRACTION_RANGE) - falls back to the full amount for
                 this lot if the capped total can't cover lot_volume.

    Returns: dict {farmer_code: allocated_kg} with exactly n_receipts entries
             summing to lot_volume (rounded to 2dp).
    Raises: AllocationError if the request is not satisfiable.
    """
    if n_receipts <= 0:
        raise AllocationError("Receipt range must include at least one receipt.")
    if lot_volume <= 0:
        raise AllocationError("Lot volume must be greater than zero.")
    if len(eligible_farmers) < n_receipts:
        raise AllocationError(
            f"Only {len(eligible_farmers)} active farmer(s) have remaining quota, "
            f"but {n_receipts} receipt(s) were specified. Reduce the receipt range, "
            f"add farmers, or refresh the master list."
        )
    if n_receipts * min_share > lot_volume:
        raise AllocationError(
            f"{n_receipts} receipts cannot each carry a meaningful share of a "
            f"{lot_volume:g}kg lot. Reduce the receipt range or increase the lot volume."
        )

    chosen = _pick_feasible_subset(eligible_farmers, lot_volume, n_receipts, max_retries, required_ids)
    if spread_mode:
        chosen = _apply_spread_cap(chosen, lot_volume)
    return _split_with_caps(chosen, lot_volume, min_share)


def _apply_spread_cap(chosen, lot_volume):
    capped = [(fid, cap * random.uniform(*SPREAD_FRACTION_RANGE)) for fid, cap in chosen]
    if sum(cap for _, cap in capped) >= lot_volume:
        return capped
    # The randomised caps can't cover this lot with this farmer set - using
    # them would silently make the lot unsatisfiable, so fall back to the
    # farmers' real remaining capacity for this one lot rather than fail.
    return chosen


def _pick_feasible_subset(eligible_farmers, lot_volume, n_receipts, max_retries, required_ids=None):
    required_ids = set(required_ids or ())
    required = [(fid, cap) for fid, cap in eligible_farmers if fid in required_ids]
    pool = [(fid, cap) for fid, cap in eligible_farmers if fid not in required_ids]
    n_remaining = n_receipts - len(required)
    if n_remaining < 0:
        raise AllocationError(
            f"{len(required)} preferred farmer(s) selected but only {n_receipts} receipt(s) available."
        )
    if n_remaining == 0:
        return required

    best = None
    for _ in range(max_retries):
        sample = random.sample(pool, n_remaining)
        chosen = required + sample
        total_cap = sum(cap for _, cap in chosen)
        if total_cap >= lot_volume:
            return chosen
        if best is None or total_cap > best[1]:
            best = (chosen, total_cap)

    # Fall back to the n_remaining pool farmers with the most headroom - still
    # randomised in *which* of the tied-capacity farmers get picked, but
    # biased toward feasibility so we don't fail a satisfiable request
    # just because random sampling got unlucky.
    ranked = sorted(pool, key=lambda x: x[1], reverse=True)
    top = required + ranked[:n_remaining]
    total_cap = sum(cap for _, cap in top)
    if total_cap < lot_volume:
        raise AllocationError(
            f"Not enough combined remaining quota among eligible farmers "
            f"({total_cap:g}kg) to cover this lot ({lot_volume:g}kg)."
        )
    return top


def _split_with_caps(chosen, lot_volume, min_share):
    codes = [c for c, _ in chosen]
    caps = {c: cap for c, cap in chosen}
    n = len(codes)

    # Reserve a minimum share per farmer so nobody gets an implausible 0.01kg
    # receipt, then randomly distribute the rest with Dirichlet-style weights.
    reserved = min(min_share, lot_volume / n)
    remainder = lot_volume - reserved * n
    weights = [random.random() + 0.05 for _ in range(n)]
    total_w = sum(weights)
    alloc = {c: reserved + remainder * w / total_w for c, w in zip(codes, weights)}

    # Clip anyone over their cap and redistribute the excess, repeating until
    # the whole lot is placed or nobody has room left.
    for _ in range(200):
        over = {c: alloc[c] - caps[c] for c in codes if alloc[c] > caps[c]}
        if not over:
            break
        excess = sum(over.values())
        for c in over:
            alloc[c] = caps[c]
        under = [c for c in codes if alloc[c] < caps[c]]
        if not under:
            break
        w2 = [random.random() + 0.05 for _ in under]
        tw2 = sum(w2)
        for c, w in zip(under, w2):
            room = caps[c] - alloc[c]
            alloc[c] += min(room, excess * w / tw2)

    alloc = {c: round(v, 2) for c, v in alloc.items()}
    drift = round(lot_volume - sum(alloc.values()), 2)
    if drift:
        adj = max(codes, key=lambda c: caps[c] - alloc[c])
        alloc[adj] = round(alloc[adj] + drift, 2)
    return alloc


def split_proportional(weights, total):
    """Split an integer `total` (e.g. bags) across keys in proportion to
    `weights` (e.g. each farmer's allocated kg), rounding to whole units
    and fixing the rounding remainder on the largest share. No capacity
    constraint here - unlike volume, a bag count has no per-farmer cap.

    weights: dict {key: positive float}
    Returns: dict {key: int} summing exactly to `total`.
    """
    keys = list(weights.keys())
    total_weight = sum(weights.values())
    if total_weight <= 0 or total <= 0:
        return {k: 0 for k in keys}

    raw = {k: total * weights[k] / total_weight for k in keys}
    out = {k: int(raw[k]) for k in keys}  # floor
    remainder = total - sum(out.values())
    # Hand out the leftover units to the keys with the largest fractional
    # part first, so the split stays proportional rather than arbitrary.
    fractional_order = sorted(keys, key=lambda k: raw[k] - out[k], reverse=True)
    for k in fractional_order[:remainder]:
        out[k] += 1
    return out
