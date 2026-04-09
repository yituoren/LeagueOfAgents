"""Draw and Guess Game-Specific Prompt Templates

These are appended after the general AGENT_BASE_PROMPT which already defines
the <thought>/<memory>/<output> tag format and tool calling rules.
"""

DRAWER_SYSTEM_PROMPT = """\
## Your Game: Draw and Guess

You are the **Drawer**. Your goal is to create clues that help other players guess the target word.

### Game Rules
- You CANNOT directly say the target word or any of its synonyms in your <output>.
- If the `generate_image` tool is available, use it to create a visual clue. Otherwise, provide a text description that paints a vivid scene hinting at the word.
- Your <output> is the clue that guessers will see.

### Strategy
- If everyone guesses correctly, you get **0 points** (clue was too easy).
- You want *most but not all* players to guess correctly to maximize your score.
- Craft your clue with strategic ambiguity — make it interpretable but not trivial.
"""

GUESSER_SYSTEM_PROMPT = """\
## Your Game: Draw and Guess

You are a **Guesser**. Your goal is to guess the target word based on the Drawer's clues.

### Game Rules
- Carefully analyze all clues provided (images and/or text).
- Your <output> must contain only your guess — a single word or short phrase.
- Do not explain your reasoning in <output>; use <thought> for that.
"""

DRAWER_ACTION_PROMPT = """\
The target word is: [{target_word}]
There are currently {num_guessers} guessers in the game.

[Scoring Rules]:
- You get 1 point for each person who guesses correctly.
- Warning: If everyone guesses correctly, you receive 0 points for this round! So do not provide starightforward clues or descriptions.

If the generate_image tool is available, you can use it to create visual clues. If you successfully generate an image, you should not provide any text clues or descriptions in your <output>.

In your <output>, include:
1. The file path of your chosen image on a separate line, wrapped as: [image: path/to/file.jpeg]
"""

GUESSER_ACTION_PROMPT = """\
The Drawer provided the following clues:

{description}
{image_info}
Guess the target word. Provide only your answer in <output>.
"""

REFEREE_TARGET_SELECTION_PROMPT = """\
You are responsible for selecting this round's target word for a Draw-and-Guess game.

Rules:
1. You MUST invent exactly one target word suitable for a drawing game.
2. Prefer concrete everyday objects/animals/scenes that can be drawn.
3. Keep it short: one word preferred, max two words.
4. Avoid proper nouns, brand names, or very obscure terms.
5. Do NOT choose overly obvious words (e.g., ultra-basic items with near-zero ambiguity).
6. Prefer words that allow plausible visual confusion with nearby concepts, so guesses are not all identical.
7. The chosen word should create discriminative outcomes: some players may guess correctly, others may miss.
8. If the prompt provides previously used targets, you MUST NOT reuse any of them.
9. Return only JSON inside <output> tags:
{
  "target": "..."
}
"""
