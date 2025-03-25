import os

from pydantic import BaseModel
from openai import OpenAI

from crossword.utils import cache_call, print_time


# Input is a text desciprtion of the theme, output is a dictionary of words and clues
if os.environ["OPENAI_API_KEY"]:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
else:
    raise ValueError("No OPENAI_API_KEY")

class Clue(BaseModel):
    clue: str

class WordAndClue(BaseModel):
    word: str
    clue: str

class Theme(BaseModel):
    words: list[WordAndClue]



@cache_call(".theme-calls.csv", eval)
@print_time("Generating theme words and clues with an LLM")
def llm_generate_theme(theme, size):    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are Will Shortz, the crossword puzzle editor for The New York Times, and you are excited to help me make a great crossword. "},
            {"role": "user", "content": f"Provide {size} words and clues for a crossword puzzle with the theme \"{theme}\"."},
        ],
        response_format=Theme,
    )

    event = completion.choices[0].message.parsed
    words_x_clues = {}
    for e in event.words:
        word = e.word.upper()
        if word not in words_x_clues and len(word) <= size:
            words_x_clues[word] = e.clue
    return words_x_clues

@cache_call(".clue-calls.csv", str)
@print_time("Generating a clue with an LLM")
def llm_generate_clue(word, theme):

    theme = f"Use the theme \"{theme}\", if you can." if theme else ""

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": "You are Will Shortz, the crossword puzzle editor for The New York Times, and you are excited to help me make a great crossword. "},
            {"role": "user", "content": f"Provide a clue for the word \"{word}\". {theme}"},
        ],
        response_format=Clue,
    )

    event = completion.choices[0].message.parsed
    return event.clue