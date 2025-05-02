import csv
import os
import subprocess

from datetime import date, timedelta
from timeit import default_timer as timer
from typing import List

# Decorator for tracking progress and runtime
def print_time(msg):
    def decorator(f):
        def wrapper(*args, **kwargs):
            print(f'{msg} ... ', end='', flush=True)
            start = timer()
            res = f(*args, **kwargs)
            print('{:.2f}s'.format(timer() - start))
            return res
        return wrapper
    return decorator

def cache_call(filename, post):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with open(filename, "a+"):
                # create the file if it doesn't exist
                pass
            with open(filename, "r+") as f:
                cache = csv.reader(f, delimiter="\t")
                # find the row with the inputs
                for row in cache:
                    old_args = list(map(str, row[:-1]))
                    new_args = ["" if a is None else str(a) for a in args]
                    if old_args == new_args:
                        print(f"Cache hit! {old_args} -> \"{row[-1]}\"")
                        f.close()
                        return post(row[-1])
                res = func(*args, **kwargs)
                cache = csv.writer(f, delimiter="\t")
                cache.writerow(list(args) + [res])
            return res
        return wrapper
    return decorator


def reject_impossible_themes(words: List[str], size: int) -> bool:
    """
    Returns True if the theme can't be immediately rejected, False if it can
    """
    print(f"Checking theme {words}")

    # if there are no words, it is impossible
    if len(words) == 0:
        return False

    # if there are more words than the size of the crossword, it is impossible
    if len(words) > size:
        return False
    
    # if any word is longer than the size of the crossword, it is impossible
    if any([len(word) > size for word in words]):
        return False
    
    # count the lengths of the words
    lengths = [len(word) for word in words]
    counts = [(length, lengths.count(length)) for length in set(lengths)]

    # remove all the counts with an even number of occurrences
    counts = [(length, count % 2) for length, count in counts if count % 2 == 1]

    # if counts is empty, it is possible
    if len(counts) == 0:
        return True

    # if the puzzle is even, and counts is not empty, it is impossible
    if size % 2 == 0:
        return False
    
    # if the puzzle is odd, and counts has more than one element, it is impossible
    if len(counts) > 1:
        return False
    
    last_length = counts[0][0]
    if (size - last_length) % 2 != 0:
        return False
    
    return True

def pull_crossword_data(out_directory_path: str, num_examples: int=None, mini=False):
    """
    Pulls NYT crossword data using the provided bash command into the specified directory.
    If num_examples is None, it will pull all examples.
    If mini is 
    """
    # if the directory does not exist, create it
    if not os.path.exists(out_directory_path):
        os.makedirs(out_directory_path)
    if mini:
        data_start = date(2019, 1, 2)
        data_end = date(2021, 3, 7)
    else:
        data_start = date(1977, 1, 1)
        data_end = date(2017, 12, 3)
    delta = timedelta(days=1)
    succ_count = 0
    
    while data_start <= data_end:
        if mini:
            result = subprocess.run(f'crossword recreate {data_start.strftime("%Y-%m-%d")} {out_directory_path}/mini{data_start.strftime("%Y%m%d")}.md --repo nyt-mini-crosswords', shell=True)
        else:
            result = subprocess.run(f'crossword recreate {data_start.strftime("%Y-%m-%d")} {out_directory_path}/nyt{data_start.strftime("%Y%m%d")}.md', shell=True)
        data_start += delta
        if result.returncode == 0:
            # correctly pulled down so increment
            succ_count += 1
        if num_examples is not None:
            if succ_count == num_examples:
                break
    print(f"All data pulled into {out_directory_path}")