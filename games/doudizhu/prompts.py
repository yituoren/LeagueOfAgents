"""Dou Dizhu prompt templates.

These are appended after the general AGENT_BASE_PROMPT which defines
the <thought>/<memory>/<output> tag format.
"""

DOUDIZHU_SYSTEM_PROMPT = """\
## Your Game: Dou Dizhu (Fight the Landlord)

3-player Chinese card game: **1 Landlord vs 2 Peasants (teammates)**.

### Card Ranks (low → high)
`3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < 2 < SJ < BJ`

Note: `2` is second-highest (not lowest). `SJ` = small joker, `BJ` = big joker.
The deck has 54 cards (4 × 13 ranks + 2 jokers). Suits are irrelevant.

### Valid Combos
- **Single**: one card — e.g. `7`
- **Pair**: two of a rank — e.g. `K K`
- **Triple**: three of a rank — e.g. `9 9 9`
- **Triple + 1**: triple with any single — e.g. `9 9 9 4`
- **Triple + 2**: triple with any pair — e.g. `9 9 9 4 4`
- **Straight**: 5+ consecutive singles, ranks 3–A only — e.g. `5 6 7 8 9`
- **Pair Straight**: 3+ consecutive pairs, ranks 3–A only — e.g. `5 5 6 6 7 7`
- **Plane**: 2+ consecutive triples, ranks 3–A only — e.g. `7 7 7 8 8 8`
- **Plane + singles**: each triple with 1 extra single — e.g. `7 7 7 8 8 8 3 4`
- **Plane + pairs**: each triple with 1 extra pair — e.g. `7 7 7 8 8 8 3 3 4 4`
- **Four + 2**: four of a kind + 2 singles — e.g. `K K K K 3 5`
- **Four + 2 pairs**: four of a kind + 2 pairs — e.g. `K K K K 3 3 5 5`
- **Bomb**: 4 of a kind — beats any non-bomb, e.g. `K K K K`
- **Rocket** (王炸): both jokers `SJ BJ` — beats everything

### Playing Rules
- Landlord plays first. Turns rotate.
- To follow a previous play, you must match its **exact type and length** AND have a higher main rank.
- You can always play a **bomb** to beat any non-bomb, or a **rocket** to beat anything.
- You may **pass**. When two players pass consecutively, the third player (who last played) leads freely.
- First player to empty their hand wins the round.

### Scoring
- Base score × bid_multiplier × 2^(number of bombs & rockets played in the round).
- Landlord wins: landlord +2×score, each peasant −1×score.
- Landlord loses: landlord −2×score, each peasant +1×score.

### Strategic Tips
- Count cards: 4 of each rank + 2 jokers. Track what's played.
- As landlord, you have 20 cards vs 17 each for peasants — use the extra cards wisely.
- As peasant, **coordinate with your teammate**: sometimes pass to let them lead, or play small to feed them control.
- Bombs are powerful but you lose combo flexibility — save them for key moments.
- Holding onto 2s and jokers late can secure the win.

### Output Format (STRICT — any deviation forfeits your turn)
Your `<output>` must be **exactly one** of the following, with no extra text:
- `pass` — to pass this turn (lowercase)
- A whitespace-separated list of card tokens from this exact set:
  `3 4 5 6 7 8 9 10 J Q K A 2 SJ BJ`

Rules for the card list format:
- Case-sensitive: write `J`, not `j`; `SJ`, not `sj` or `小王`.
- Use `10` for ten (not `T`).
- No commas, no dashes, no brackets, no explanatory text.
- Examples of valid outputs:
  `<output>7</output>`
  `<output>K K</output>`
  `<output>7 7 7 8 8 8 3 4</output>`
  `<output>SJ BJ</output>`
  `<output>pass</output>`

If your output does not match this format exactly, or if the cards you list are not in your hand, or the combo is invalid, or it cannot beat the last play, **your turn is forfeited** (treated as a pass). There is no auto-correction — be precise.
"""

BID_PROMPT = """\
[Bidding Phase — Round {round_num}]

Your hand ({num_cards} cards, sorted): {hand}

Bids so far this round: {bids_so_far}

Bid **0** (pass), **1**, **2**, or **3** points to compete for the landlord role.
- Higher bids mean higher stakes (the final score is multiplied by your bid).
- Bid 3 for a dominant hand (rocket, multiple bombs, many 2s/jokers).
- Bid 1–2 for decent hands with some control cards.
- Pass (0) if your hand is weak.

The **highest bidder becomes the landlord**, receives the 3 hidden cards, and plays first — but plays alone against the 2 peasants.

**Output format (STRICT)**: your `<output>` must be exactly one of the characters `0`, `1`, `2`, or `3` — nothing else. Any other output is treated as bid 0.
"""

PLAY_PROMPT = """\
[Playing Phase — Round {round_num}]

You are: **{player_name}** — role: **{role}**
Landlord: **{landlord_name}**

Hand sizes: {hand_sizes}

Recent plays:
{history}

Last play on table: {last_play}
{lead_notice}

Your hand ({num_cards} cards, sorted): {hand}

{instruction}

**Output format (STRICT)**: your `<output>` must be EXACTLY one of:
- `pass`
- A whitespace-separated list of cards from `{{3,4,5,6,7,8,9,10,J,Q,K,A,2,SJ,BJ}}` (case-sensitive, no extra text)

Any deviation forfeits your turn.
"""
