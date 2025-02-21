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

let lastDirection = 'horizontal'; // Track the last direction moved

// helper function to determine the next input to focus on based on the id, which is x_y
function getNextInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    let nextInput;
    if (lastDirection === 'horizontal') {
        nextInput = document.getElementById(`${x + 1}_${y}`);
        if (!nextInput) {
            nextInput = document.getElementById(`${x}_${y + 1}`);
        }
    } else {
        nextInput = document.getElementById(`${x}_${y + 1}`);
        if (!nextInput) {
            nextInput = document.getElementById(`${x + 1}_${y}`);
        }
    }
    return nextInput || current;
}

function getPrevInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    let prevInput;
    if (lastDirection === 'horizontal') {
        prevInput = document.getElementById(`${x - 1}_${y}`);
        if (!prevInput) {
            prevInput = document.getElementById(`${x}_${y - 1}`);
        }
    } else {
        prevInput = document.getElementById(`${x}_${y - 1}`);
        if (!prevInput) {
            prevInput = document.getElementById(`${x - 1}_${y}`);
        }
    }
    return prevInput || current;
}

function getNextNextInput(current) {
    const nextInput = getNextInput(current);
    return getNextInput(nextInput);
}

function shadeNextGrid(current) {
    const nextInput = getNextInput(current);
    if (nextInput !== current) {
        nextInput.classList.add('next');
    }
}

function shadeNextNextGrid(current) {
    const nextNextInput = getNextNextInput(current);
    if (nextNextInput !== current) {
        nextNextInput.classList.add('nextnext');
    }
}

function unshadeGrid() {
    document.querySelectorAll('input.next, input.nextnext').forEach(input => {
        input.classList.remove('next', 'nextnext');
    });
}

function updateDirection(prev, next) {
    const [x1, y1] = prev.id.split('_').map(Number);
    const [x2, y2] = next.id.split('_').map(Number);
    if (x1 !== x2) {
        lastDirection = 'horizontal';
    } else {
        lastDirection = 'vertical';
    }
}

// Add event listeners to all inputs
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input').forEach((input) => {
        input.addEventListener('focus', () => {
            unshadeGrid();
            shadeNextGrid(input);
            shadeNextNextGrid(input);
        });

        input.addEventListener('blur', () => {
            unshadeGrid();
        });

        input.addEventListener('input', (event) => {
            checkInputs();
            if (input.value.length === 1) {
                const nextInput = getNextInput(input);
                if (nextInput !== input) {
                    nextInput.focus();
                    nextInput.setSelectionRange(0, nextInput.value.length);
                    // set the direction to horizontal if we moved horizontally
                    updateDirection(input, nextInput);
                }
            } else if (input.value.length === 0 && event.inputType === 'deleteContentBackward') {
                const prevInput = getPrevInput(input);
                if (prevInput !== input) {
                    prevInput.focus();
                    // make the cursor go to the end of the input
                    prevInput.setSelectionRange(prevInput.value.length, prevInput.value.length);
                    // set the direction to horizontal if we moved horizontally
                    updateDirection(prevInput, input);
                }
            }
        });

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Backspace' && input.value.length === 0) {
                const prevInput = getPrevInput(input);
                if (prevInput !== input) {
                    prevInput.focus();
                    // make the cursor go to the end of the input
                    prevInput.setSelectionRange(prevInput.value.length, prevInput.value.length);
                    // set the direction to horizontal if we moved horizontally
                    updateDirection(prevInput, input);
                }
            } else if (event.key === 'Enter') {
                const nextInput = getNextInput(input);
                if (nextInput !== input) {
                    nextInput.focus();
                    nextInput.setSelectionRange(0, nextInput.value.length);
                    // set the direction to horizontal if we moved horizontally
                    updateDirection(input, nextInput);
                }
            }
        });

        // Add event listener to highlight all text on click
        input.addEventListener('click', () => {
            input.setSelectionRange(0, input.value.length);
        });

        // Add event listener for double-click to change direction
        input.addEventListener('dblclick', () => {
            const old_direction = lastDirection
            lastDirection = lastDirection === 'horizontal' ? 'vertical' : 'horizontal';
            // update the highlights for the next and nextnext cells
            unshadeGrid();
            shadeNextGrid(input);
            shadeNextNextGrid(input);
        });
    });

    // Add event listeners to clues
    document.querySelectorAll('#clues li').forEach(clue => {
        clue.addEventListener('click', () => {
            const number = clue.getAttribute('data-number');
            // get all the elements of class number
            const inputs = document.querySelectorAll('.number');
            // find the element with the same data-number
            const gridNumber = Array.from(inputs).find(gridNumber => gridNumber.getAttribute('data-number') === number);
            if (gridNumber) {
                // find the input sibling of the grid number
                const input = gridNumber.nextElementSibling;
                if (input) {
                    input.focus();
                    input.setSelectionRange(0, input.value.length);
                }
            }
            // set the direction to right if we are in the across clues
            if (clue.parentElement.id === 'across') {
                lastDirection = 'horizontal';
            } else {
                lastDirection = 'vertical';
            }
        });
    });
});
