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
                console.log("Incorrect: " + input.value.trim().toUpperCase() + " !== " + input.name.trim().toUpperCase());
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

let lastDirection = 'right'; // Track the last direction moved

// helper function to determine the next input to focus on based on the id, which is x_y
function getNextInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    let nextInput;
    if (lastDirection === 'right') {
        nextInput = document.getElementById(`${x + 1}_${y}`);
        if (!nextInput) {
            nextInput = document.getElementById(`${x}_${y + 1}`);
            lastDirection = 'down';
        }
    } else {
        nextInput = document.getElementById(`${x}_${y + 1}`);
        if (!nextInput) {
            nextInput = document.getElementById(`${x + 1}_${y}`);
            lastDirection = 'right';
        }
    }
    return nextInput || current;
}

function getPrevInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    let prevInput;
    if (lastDirection === 'left') {
        prevInput = document.getElementById(`${x - 1}_${y}`);
        if (!prevInput) {
            prevInput = document.getElementById(`${x}_${y - 1}`);
            lastDirection = 'up';
        }
    } else {
        prevInput = document.getElementById(`${x}_${y - 1}`);
        if (!prevInput) {
            prevInput = document.getElementById(`${x - 1}_${y}`);
            lastDirection = 'left';
        }
    }
    return prevInput || current;
}

// Add event listeners to all inputs
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input').forEach((input) => {
        input.addEventListener('input', (event) => {
            checkInputs();
            if (input.value.length === 1) {
                const nextInput = getNextInput(input);
                if (nextInput !== input) {
                    nextInput.focus();
                    nextInput.setSelectionRange(0, nextInput.value.length);
                }
            } else if (input.value.length === 0 && event.inputType === 'deleteContentBackward') {
                const prevInput = getPrevInput(input);
                if (prevInput !== input) {
                    prevInput.focus();
                    // make the cursor go to the end of the input
                    prevInput.setSelectionRange(prevInput.value.length, prevInput.value.length);
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
                }
            } else if (event.key === 'Enter') {
                const nextInput = getNextInput(input);
                if (nextInput !== input) {
                    nextInput.focus();
                    nextInput.setSelectionRange(0, nextInput.value.length);
                }
            }
        });

        // Add event listener to highlight all text on click
        input.addEventListener('click', () => {
            input.setSelectionRange(0, input.value.length);
        });
    });

    // Add event listeners to clues
    document.querySelectorAll('#clues li').forEach(clue => {
        clue.addEventListener('click', () => {
            const number = clue.getAttribute('data-number');
            console.log("picking clue: " + number);
            // get all the elements of class number
            const inputs = document.querySelectorAll('.number');
            // find the element with the same data-number
            const gridNumber = Array.from(inputs).find(gridNumber => gridNumber.getAttribute('data-number') === number);
            if (gridNumber) {
                console.log("focusing on: " + gridNumber.id);
                // find the input sibling of the grid number
                const input = gridNumber.nextElementSibling;
                if (input) {
                    input.focus();
                    input.setSelectionRange(0, input.value.length);
                }
            }
            // set the direction to right if we are in the across clues
            if (clue.parentElement.id === 'across') {
                lastDirection = 'right';
            } else {
                lastDirection = 'down';
            }
        });
    });
});
