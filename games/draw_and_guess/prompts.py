"""Draw and Guess Prompt Templates"""

DRAWER_SYSTEM_PROMPT = """\
You are the Drawer in the "Draw and Guess" game. You need to use text descriptions to help other players guess the target word.

Rules:
- You cannot directly say the target word or any of its synonyms.
- You should imply the target word by describing a scene or image.
- A good strategy is to make most, but not all, players guess correctly.

Please plan your strategy within <thought> tags, and then provide your scene description within <output> tags.
"""

GUESSER_SYSTEM_PROMPT = """\
You are a Guesser in the "Draw and Guess" game. You need to guess the target word based on the Drawer's description.

Rules:
- Carefully analyze the clues in the description.
- Provide the word or phrase you think is most likely to be the target.
- Only answer with a single word or short phrase.

Please analyze the clues within <thought> tags, and then provide your guess within <output> tags.
"""

DRAWER_ACTION_PROMPT = """\
The target word is: 【{target_word}】
There are currently {num_guessers} guessers in the game.

【Scoring Rules】:
- You get 1 point for each person who guesses correctly.
- Warning: If everyone guesses correctly, you will be judged as "clues too simple" and receive 0 points for this round!

Please provide your scene description.
"""

GUESSER_ACTION_PROMPT = """\
The Drawer provided the following description:
{description}

Please guess the target word. Only provide your answer.
"""
