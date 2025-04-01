import os
import csv
import json
import typer
import datetime

from crossword.builder import GridBuilder
from crossword.crossword import Crossword
from crossword.constants import BLANK

# Helpers and main functions

app = typer.Typer(pretty_exceptions_enable=False, add_completion=False, help="Generate a crossword puzzle")

@app.command(short_help="Generate a mini (5x5) crossword puzzle from words and optional clues")
def mini(
    bank: str = typer.Argument(..., help="Path to a tsv file with words and clues (word, clue)"),
    output: str = typer.Argument(..., help="Output file (.html or .json)"),
    timeout: int = typer.Option(60, help="Timeout for each solver call in seconds"),
):
    assert output.endswith(".html") or output.endswith(".json"), "output file must be .html or .json"
    assert bank.endswith(".tsv"), "bank file must be tsv file"
    
    # read the bank as a csv file delimited by tabs
    with open(bank, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        words_x_clues = {row[0]: row[1] for row in reader}

    # build the crossword
    crossword = GridBuilder(words_x_clues, 5).build(timeout=timeout, max_blanks=-1)

    # fill in the clues with an llm
    crossword.auto_fill_clues()

    # write the crossword to the output file
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)


@app.command(short_help="Generate a Friday (15x15) crossword puzzle from words and optional clues (no theme)")
def friday(
    bank: str = typer.Argument(..., help="Path to a tsv file with words and clues (word, clue)"),
    output: str = typer.Argument(..., help="Output file (.html or .json)"),
    timeout: int = typer.Option(60, help="Timeout for each solver call in seconds"),
):
    assert output.endswith(".html") or output.endswith(".json"), "output file must be .html or .json"
    assert bank.endswith(".tsv"), "bank file must be tsv file"
    
    # read the bank as a csv file delimited by tabs
    with open(bank, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        words_x_clues = {row[0]: row[1] for row in reader}

    # build the crossword
    crossword = GridBuilder(words_x_clues, 15).build(timeout=timeout, max_blanks=-1)

    # fill in the clues with an llm
    crossword.auto_fill_clues()

    # write the crossword to the output file
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)


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

@app.command(short_help="Recreate a crossword puzzle from the nyt_crosswords repo")
def recreate(
    date: str = typer.Argument(..., help="Date of the puzzle in the format YYYY-MM-DD"),
    output: str = typer.Argument(..., help="Output file (.html or .json)"),
):
    download_nyt()
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")
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
    
    crossword = Crossword(grid, across, down)
    if output.endswith(".html"):
        with open(output, "w") as f:
            f.write(crossword.to_html())
    else:
        with open(output, "w") as f:
            json.dump(crossword.to_json(), f)


# https://github.com/doshea/nyt_crosswords/archive/refs/heads/master.zip
@app.command(short_help="Generate a bank of words and clues from the nyt_crosswords repo")
def bank(
    output: str = typer.Argument(..., help="Output file (.tsv)"),
    start: str = typer.Option("1976-01-01", help="Start date for the puzzles to include (inclusive)"),
    end: str = typer.Option("2018-03-09", help="End date for the puzzles to include (inclusive)"),
    day: str = typer.Option("all", help="Limit to puzzles of a certain day of the week"),
):
    assert output.endswith(".tsv"), "output file must be .tsv"
    # convert the start and end dates to dates
    start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end, "%Y-%m-%d")

    download_nyt()

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
                                clue = clean_clue(across_clues[i])
                                writer.writerow([word, clue])
                            for i, word in enumerate(down_words):
                                clue = clean_clue(down_clues[i])
                                writer.writerow([word, clue])

if __name__ == "__main__":
    app()