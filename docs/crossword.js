let facing = true; // the direction we are currently facing: true means across

// Add event listeners to all inputs
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input').forEach((input) => {
        input.addEventListener('focus', () => {
            gotoCell(input, facing);
        });

        input.addEventListener('blur', () => {
            clear();
        });

        input.addEventListener('input', (event) => {
            checkInputs();
            if (input.value.length === 1) {
                gotoNext(input)
            } else if (input.value.length === 0 && event.inputType === 'deleteContentBackward') {
                gotoPrev(input)
            }
        });

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Backspace' && input.value.length === 0) {
                gotoPrev(input);
            } else if (event.key === 'Enter') {
                gotoNext(input);
            }
            // arrow keys to navigate the grid
            if (event.key === 'ArrowUp') {
                goUp(input)
            }
            if (event.key === 'ArrowDown') {
                goDown(input)
            }
            if (event.key === 'ArrowLeft') {
                goLeft(input)
            }
            if (event.key === 'ArrowRight') {
                goRight(input)
            }
            if (event.key === 'Tab') {
                gotoNext(input);
            }
        });

        // Add event listener to highlight all text on click
        input.addEventListener('click', () => {
            input.setSelectionRange(0, input.value.length);
        });

        // Add event listener for double-click to change direction
        input.addEventListener('dblclick', () => {
            updateDirection(input);
        });
    });

    // Add event listeners to clues
    document.querySelectorAll('#clues li').forEach(clue => {
        clue.addEventListener('click', () => {
            const number = clue.getAttribute('data_number');
            const inputs = document.querySelectorAll('.number');
            const cellNumber = Array.from(inputs).find(cellNumber => cellNumber.getAttribute('data_number') === number);
            const cell = cellNumber.nextElementSibling;
            gotoCell(cell, clue.parentElement.id === "across");
        });
    });

    // add event listener to the whole screen
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Alt') {
            const inputs = document.querySelectorAll('input');
            // save all the current values
            savedValues = [];
            inputs.forEach(input => {
                savedValues.push(input.value);
            });
            // fill in all the correct values
            inputs.forEach(input => {
                if (input.value.trim().toUpperCase() !== input.name.trim().toUpperCase()) {
                    input.style.color = 'var(--selected)';
                    input.value = input.name;
                }
            });
        }
    });

    document.addEventListener('keyup', (event) => {
        if (event.key === 'Alt') {
            const inputs = document.querySelectorAll('input');
            inputs.forEach((input, index) => {
                input.value = savedValues[index];
                // remove the color
                input.style.color = '';
            });
        }
    });
});

var savedValues = [];

// helpers

function gotoCell(target, direction) {
    clear();
    facing = direction;
    target.focus();
    target.setSelectionRange(0, target.value.length)
    shade(target);
}

function clear() {
    document.querySelectorAll('input.next, input.nextnext, input.prev, input.prevprev').forEach(input => {
        input.classList.remove('next', 'nextnext', 'prev', 'prevprev');
    });
}

function shade(current) {
    const next = getNext(current, facing);
    if (next) {
        next.classList.add('next');
        const nextnext = getNext(next, facing);
        if (nextnext) {
            nextnext.classList.add('nextnext');
        }
    }
    const prev = getPrev(current, facing);
    if (prev) {
        prev.classList.add('prev');
        const prevprev = getPrev(prev, facing);
        if (prevprev) {
            prevprev.classList.add('prevprev');
        }
    }
}

function getNext(current, direction) {
    // get the id of the current cell
    const currentId = current.id;
    // split the id into row and column
    const [row, col] = currentId.split('_');
    // get the next cell in the correct direction
    if (direction) {
        return document.getElementById(`${row}_${parseInt(col) + 1}`);
    } else {
        return document.getElementById(`${parseInt(row) + 1}_${col}`);
    }
}

function getPrev(current, direction) {
    // get the id of the current cell
    const currentId = current.id;
    // split the id into row and column
    const [row, col] = currentId.split('_');
    // get the previous cell in the correct direction
    if (direction) {
        return document.getElementById(`${row}_${parseInt(col) - 1}`);
    } else {
        return document.getElementById(`${parseInt
        (row) - 1}_${col}`);
    }
}

function gotoNext(current) {
    if (facing) {
        goRight(current);
    } else {
        goDown(current);
    }
}

function gotoPrev(current) {
    if (facing) {
        goLeft(current);
    } else {
        goUp(current);
    }
}

function goUp(current) {
    const [row, col] = current.id.split('_');
    const next = document.getElementById(`${parseInt(row) - 1}_${col}`);
    if (next) {
        gotoCell(next, false);
    }
}

function goDown(current) {
    const [row, col] = current.id.split('_');
    const next = document.getElementById(`${parseInt(row) + 1}_${col}`);
    if (next) {
        gotoCell(next, false);
    }
}

function goLeft(current) {
    const [row, col] = current.id.split('_');
    const next = document.getElementById(`${row}_${parseInt(col) - 1}`);
    if (next) {
        gotoCell(next, true);
    }
}

function goRight(current) {
    const [row, col] = current.id.split('_');
    const next = document.getElementById(`${row}_${parseInt(col) + 1}`);
    if (next) {
        gotoCell(next, true);
    }
}

function updateDirection(current) {
    clear();
    if (facing && getNext(current, facing !== true)) {
        facing = false
    } else if (facing !== true && getNext(current, facing)) {
        facing = true
    }
    shade(current);
}

function checkInputs() {
    const inputs = document.querySelectorAll('input');
    let allFilled = true;
    inputs.forEach(input => {
        if (input.value.trim() === '') {
            allFilled = false;
        }
    });
    if (allFilled) {
        // check that all input values match the correct letter
        let allCorrect = true;
        inputs.forEach(input => {
            if (input.value.trim().toUpperCase() !== input.name.trim().toUpperCase()) {
                allCorrect = false;
            }
        });
        const grid = document.getElementById('grid');
        if (allCorrect) {
            // All correct, replace the grid with a success message
            const oldDisplay = grid.style.display;
            grid.style.display = 'none';
            const correct = document.createElement('h1');
            correct.textContent = 'You won! Congratulations!';
            document.body.prepend(correct);
            setTimeout(() => {
                grid.style.display = oldDisplay;
                correct.remove();
            }, 2000);
            
        } else {
            // Not all correct, hide the grid, show an error message, and return it after 10 seconds
            const oldDisplay = grid.style.display;
            grid.style.display = 'none';
            const error = document.createElement('h1');
            error.textContent = 'Incorrect! Try again.';
            document.body.prepend(error);
            setTimeout(() => {
                grid.style.display = oldDisplay;
                error.remove();
            }, 2000);
        }
    }
}