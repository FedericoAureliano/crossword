import os

from pydantic import BaseModel
from openai import OpenAI

from crossword.utils import cache_call, print_time

if os.environ["OPENAI_API_KEY"]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
else:
    raise ValueError("No OPENAI_API_KEY")

class ClueAndAnswer(BaseModel):
    clue: str
    answer: str

class Theme(BaseModel):
    pairs: list[ClueAndAnswer]

@cache_call(".theme-cache.tsv", eval)
@print_time("Generating theme words and clues with an LLM")
def llm_generate_theme(theme, size):    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": f"You are the greatest crossword constructor in the world and you love \"{theme}\"."},
            {"role": "user", "content": f"Give me clues and answers for a crossword puzzle with the theme \"{theme}\". Pick answers that are 3 to {size} characters long. Give me at least {size*4} clues and answers. Make sure the clues are clever and not too easy. Do not include the answers in the clues. Do not include the length of the answers in the clues."},
        ],
        response_format=Theme,
    )

    event = completion.choices[0].message.parsed
    words_x_clues = {}
    for e in event.pairs:
        word = e.answer.upper()
        words_x_clues[word] = e.clue
    return words_x_clues