import os
import csv
import json
import typer
import datetime
import gdown
import math

from crossword.builder import GridBuilder
from crossword.crossword import Crossword
from crossword.constants import BLANK
from crossword.gemini import prepare_finetuning_data, prepare_prompt_minis, run_finetuning_job, sample_from_finetuned_model
from crossword.llm import llm_generate_theme, llm_generate_crossword
from crossword.parser import parse_markdown, parse_json, find_word

def download_nyt():
    # if the nyt folder does not exist
    if not os.path.exists('nyt_crosswords'):
        print("nyt_crosswords folder does not exist")
        # if the zip has not been downloaded, download it
        if not os.path.exists('nyt_crosswords.zip'):
            print("download the zip")
            os.system('wget https://github.com/doshea/nyt_crosswords/archive/refs/heads/master.zip')
            # move thh zip to the correct location
            os.system('mv master.zip nyt_crosswords.zip')
        # if the zip has been downloaded, unzip it
        if os.path.exists('nyt_crosswords.zip'):
            print("unzip the zip")
            os.system('unzip nyt_crosswords.zip')

def download_nyt_mini():
    # if the chris nunes file does not exist
    if not os.path.exists('nyt_mini.json'):
        print("nyt_mini.json file does not exist")
        # download the file with wdget
        os.system('wget https://raw.githubusercontent.com/chrisnunes57/nyt-mini-crosswords/refs/heads/main/data.json')
        # move the file to the correct location
        os.system('mv data.json nyt_mini.json')

def download_spreadthewordlist():
    # if the spreadthewordlist file does not exist
    if not os.path.exists('spreadthewordlist.dict'):
        print("spreadthewordlist.dict file does not exist")
        gdown.download('https://drive.google.com/uc?export=download&id=1G5nzDnXiNkSk2Za2M19n0g8QXxv7mDV5')


app = typer.Typer(pretty_exceptions_enable=False, add_completion=False, help="Generate a crossword puzzle")

@app.command(short_help="Generate a crossword puzzle from a bank of words and clues with an optional theme (LLM generates some of the words and clues based on the theme)")
def construct(
    bank: str = typer.Argument(..., help="Path to a tsv file with words and clues (word, clue)"),
    output: str = typer.Argument(..., help="Output file (.html, .json, or .md)"),
    theme: str = typer.Option(None, help="Theme of the crossword puzzle"),
    timeout: int = typer.Option(60, help="Timeout for each solver call in seconds"),
    size: int = typer.Option(5, help="Size of the crossword puzzle (number of rows and columns)"),
    max_blanks: int = typer.Option(-1, help="Maximum number of blanks in the crossword puzzle (-1 for minimization)"),
    symmetry: bool = typer.Option(True, help="Whether to force the crossword puzzle to be rotationally symmetry or not"),
):
    assert output.endswith(".html") or output.endswith(".json") or output.endswith(".md"), "output file must be .html, .json, or .md"
    assert size > 0, "size must be greater than 0"
    assert max_blanks >= -1, "max_blanks must be greater than or equal to -1"
    assert bank.endswith(".tsv"), "bank file must be tsv file"
    
    # read the bank as a csv file delimited by tabs
    with open(bank, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        words_x_clues = {row[0]: row[1] for row in reader}

    if theme is not None:
        theme_words_x_clues = llm_generate_theme(theme, size)
    else:
        theme_words_x_clues = {}

    for word, clue in theme_words_x_clues.items():
        words_x_clues[word] = clue

    # build the crossword
    crossword = GridBuilder(words_x_clues, size).build(key_words=theme_words_x_clues.keys(), prompt=theme, timeout=timeout, max_blanks=max_blanks, symmetry=symmetry)

    # write the crossword to the output file
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    elif output.endswith(".md"):
        with open(output, "w") as f:
            f.write(crossword.to_markdown())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)


@app.command(short_help="Ask an LLM to generate a crossword puzzle with a theme")
def auto(
    output: str = typer.Argument(..., help="Output file (.html, .json, or .md)"),
    theme: str = typer.Option(None, help="Theme of the crossword puzzle"),
    size: int = typer.Option(5, help="Size of the crossword puzzle (number of rows and columns)"),
):
    assert output.endswith(".html") or output.endswith(".json") or output.endswith(".md"), "output file must be .html, .json, or .md"
    assert size > 0, "size must be greater than 0"

    # generate the crossword
    llm_crossword = llm_generate_crossword(theme, size)
    grid = llm_crossword["grid"]
    clues = llm_crossword["clues"]

    def get(i, j):
        if i < 0 or i >= size or j < 0 or j >= size:
            return BLANK
        return grid[i][j]
    
    def next(i, j, orientation, k):
        if orientation == "ACROSS":
            return get(i, j+k)
        else:
            return get(i+k, j)
        
    def prev(i, j, orientation, k):
        if orientation == "ACROSS":
            return get(i, j-k)
        else:
            return get(i-k, j)

    # find the starting positions of every word in the grid
    across = []
    down = []
    for i in range(size):
        for j in range(size):
            # if the previous cell is blank and the current cell is not blank, it is the start of a word
            if prev(i, j, "ACROSS", 1) == BLANK and get(i, j) != BLANK:
                # find the end of the word
                k = 1
                while next(i, j, "ACROSS", k) != BLANK:
                    k += 1
                # add the word to the list of across words
                word = "".join([get(i, j+l) for l in range(k)])
                clue = clues[word] if word in clues else ""
                across.append((word, i, j, clue))
            # if the previous cell is blank and the current cell is not blank, it is the start of a word
            if prev(i, j, "DOWN", 1) == BLANK and get(i, j) != BLANK:
                # find the end of the word
                k = 1
                while next(i, j, "DOWN", k) != BLANK:
                    k += 1
                # add the word to the list of down words
                word = "".join([get(i+l, j) for l in range(k)])
                clue = clues[word] if word in clues else ""
                down.append((word, i, j, clue))

    crossword = Crossword(grid, across, down, check=False, prompt=theme)

    # write the crossword to the output file
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    elif output.endswith(".md"):
        with open(output, "w") as f:
            f.write(crossword.to_markdown())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)

@app.command(short_help="Recreate a crossword puzzle from the nyt_crosswords or nyt-mini-crosswords repos")
def recreate(
    date: str = typer.Argument(..., help="Date of the puzzle in the format YYYY-MM-DD"),
    repo: str = typer.Option("nyt_crosswords", help="Repository to use (nyt_crosswords or nyt-mini-crosswords)"),
    output: str = typer.Argument(..., help="Output file (.html, .json, or .md)"),
):
    assert output.endswith(".html") or output.endswith(".json") or output.endswith(".md"), "output file must be .html, .json, or .md"
    assert repo in ["nyt_crosswords", "nyt-mini-crosswords"], "repo must be nyt_crosswords or nyt-mini-crosswords"
    assert date.count("-") == 2, "date must be in the format YYYY-MM-DD"

    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")

    if repo == "nyt-mini-crosswords":
        download_nyt_mini()
        with open("nyt_mini.json", "r") as f:
            data = json.load(f)
            # find the date in the data
            for puzzle in data:
                if puzzle["print_date"] == date.strftime("%Y-%m-%d"):
                    board = puzzle["board"]["cells"]
                    #assert len(board) == 25, "board must be 5x5"
                    size = int(math.sqrt(len(board)))
                    # convert the board to a grid
                    grid = []
                    for i in range(size):
                        grid.append([])
                        for j in range(size):
                            if "guess" in board[i * size + j]:
                                grid[i].append(board[i * size + j]["guess"])
                            else:
                                grid[i].append(BLANK)
                    # get all the words from the grid
                    across = []
                    down = []
                    for i in range(5):
                        for j in range(5):
                            if grid[i][j] != BLANK and j == 0:
                                across_word = find_word(grid, i, j, "across")
                                across.append((across_word, i, j, ""))
                            elif grid[i][j] != BLANK and grid[i][j - 1] == BLANK:
                                across_word = find_word(grid, i, j, "across")
                                across.append((across_word, i, j, ""))
                            if grid[i][j] != BLANK and i == 0:
                                down_word = find_word(grid, i, j, "down")
                                down.append((down_word, i, j, ""))
                            elif grid[i][j] != BLANK and grid[i - 1][j] == BLANK:
                                down_word = find_word(grid, i, j, "down")
                                down.append((down_word, i, j, ""))
                    break
            else:
                raise ValueError(f"No puzzle found for {date.strftime('%Y-%m-%d')}")
    else:
        download_nyt()
        with open(f"nyt_crosswords/{year}/{month}/{day}.json", "r") as f:
            data = json.load(f)
            rows = data["size"]["rows"]
            cols = data["size"]["cols"]
            gridnums = data["gridnums"]
            def num_to_cell(num):
                # find the index of the num in gridnums
                index = gridnums.index(num)
                # convert the index to a row and col
                # (row * cols) + col = index
                col = index % cols
                row = (index - col)//cols
                return (row, col)

            flat_grid = data["grid"]
            grid = [[flat_grid[(row*cols)+col] if flat_grid[(row*cols)+col] != "." else BLANK for col in range(cols)] for row in range(rows)]

            across_words = data["answers"]["across"]
            across_clues = data["clues"]["across"]
            across_positions = []
            for i in range(len(across_clues)):
                dot = across_clues[i].find(".")
                number = int(across_clues[i][:dot])
                across_clues[i] = across_clues[i][dot+2:]
                across_positions.append(num_to_cell(number))

            down_words = data["answers"]["down"]
            down_clues = data["clues"]["down"]
            down_positions = []
            for i in range(len(down_clues)):
                dot = down_clues[i].find(".")
                number = int(down_clues[i][:dot])
                down_clues[i] = down_clues[i][dot+2:]
                down_positions.append(num_to_cell(number))

            across = [(word, pos[0], pos[1], clue) for (word, pos, clue) in zip(across_words, across_positions, across_clues)]
            down = [(word, pos[0], pos[1], clue) for (word, pos, clue) in zip(down_words, down_positions, down_clues)]
    
    crossword = Crossword(grid, across, down, check=False)

    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    elif output.endswith(".md"):
        with open(output, "w") as f:
            f.write(crossword.to_markdown(words_instead_of_clues=(repo == "nyt-mini-crosswords")))
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)


# https://github.com/doshea/nyt_crosswords/archive/refs/heads/master.zip
@app.command(short_help="Generate a bank of words and clues from the nyt_crosswords repo")
def bank(
    output: str = typer.Argument(..., help="Output file (.tsv)"),
    start: str = typer.Option("1976-01-01", help="Start date for the puzzles to include (inclusive)"),
    end: str = typer.Option("2018-03-09", help="End date for the puzzles to include (inclusive)"),
    day: str = typer.Option("all", help="Limit to puzzles of a certain day of the week (monday, tuesday, wednesday, thursday, friday, saturday, sunday, or all)"),
    quality: int = typer.Option(50, help="Quality of the answers to include based on spread the wordlist"),
):
    assert output.endswith(".tsv"), "output file must be .tsv"
    # check if the day is valid
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "all"]
    day = day.lower()
    assert day in days, f"day must be one of {days}"
    # convert the start and end dates to dates
    start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end, "%Y-%m-%d")

    download_nyt()

    if quality > 0:
        download_spreadthewordlist()
        # parse "spreadthewordlist.dict" as a csv into a dictionary
        with open("spreadthewordlist.dict", "r") as f:
            reader = csv.reader(f, delimiter=";")
            word_quality = {row[0]: int(row[1]) for row in reader}

    def clean_clue(clue):
        clue = clue[clue.find(".")+2:]
        # remove """
        clue = clue.replace('"""', "")
        # remove all tabs
        clue = clue.replace("\t", " ")
        # strip leading and trailing whitespace
        clue = clue.strip()
        return clue

    # open the output file
    with open(output, "w") as f:
        writer = csv.writer(f, delimiter="\t", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        # get the list of files in the nyt folder
        for year in os.listdir("nyt_crosswords"):
            if not os.path.isdir(f"nyt_crosswords/{year}"):
                continue
            for month in os.listdir(f"nyt_crosswords/{year}"):
                if not os.listdir(f"nyt_crosswords/{year}/{month}"):
                    continue
                for given_day in os.listdir(f"nyt_crosswords/{year}/{month}"):
                    date = f"{year}-{month}-{given_day}"[:-5] # remove the .json extension
                    date = datetime.datetime.strptime(date, "%Y-%m-%d")
                    day_of_week = date.strftime("%A").lower()
                    if start_date <= date <= end_date and (day == "all" or day_of_week == day):
                        # open the json file to get the words and clues
                        with open(f"nyt_crosswords/{year}/{month}/{given_day}", "r") as f2:
                            data = json.load(f2)
                            across_words = data["answers"]["across"]
                            down_words = data["answers"]["down"]
                            across_clues = data["clues"]["across"]
                            down_clues = data["clues"]["down"]
                            # write the words and clues to the output file
                            for i, word in enumerate(across_words):
                                if quality > 0 and (word.lower() not in word_quality or word_quality[word.lower()] < quality):
                                    print(f"Removing {word} due to quality")
                                    continue
                                clue = clean_clue(across_clues[i])
                                writer.writerow([word, clue])
                            for i, word in enumerate(down_words):
                                if quality > 0 and (word.lower() not in word_quality or word_quality[word.lower()] < quality):
                                    print(f"Removing {word} due to quality")
                                    continue
                                clue = clean_clue(down_clues[i])
                                writer.writerow([word, clue])


@app.command(short_help="Translate a crossword file")
def translate(
    input: str = typer.Argument(..., help="Path to a crossword file (.json or .md)"),
    output: str = typer.Argument(..., help="Output file (.html, .json, or .md)"),
):
    assert output.endswith(".html") or output.endswith(".json") or output.endswith(".md"), "output file must be .html, .json, or .md"
    assert input.endswith(".md") or input.endswith(".json"), "input file must be .md or .json"

    if input.endswith(".md"):
        # read the markdown file
        with open(input, "r") as f:
            contents = f.read()
        # parse the markdown file
        crossword = parse_markdown(contents, check=False)
    elif input.endswith(".json"):
        # read the json file
        with open(input, "r") as f:
            contents = f.read()
        # parse the json file
        crossword = parse_json(contents, check=False)

    # write the crossword to the output file
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    elif output.endswith(".md"):
        with open(output, "w") as f:
            f.write(crossword.to_markdown())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)

@app.command(short_help="Finetune on mini data")
def finetune(
    input: str = typer.Argument(..., help="Path to a directory of crossword markdown files"),
    gcs_filename: str = typer.Option("minis_markdown", help="Name of GCS blob within bucket to save to"),
):
    finetune_uri = prepare_finetuning_data(input, prepare_prompt_minis, gcs_filename)
    run_finetuning_job(finetune_uri)

@app.command(short_help="Sample from a finetuned model")
def samplefinetuned(
    input: str = typer.Argument(..., help="Path to a FineTuningJob on Vertex AI"),
    size: str = typer.Option("5", help="Size of the crossword puzzle (number of rows and columns)"),
):
    sample_from_finetuned_model(input, size)

if __name__ == "__main__":
    app()