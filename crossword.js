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
            correct.textContent = 'Success! You did it.';
            document.body.prepend(correct);
            setTimeout(() => {
                grid.style.display = oldDisplay;
                correct.remove();
            }, 5000);
            
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
            }, 5000);
        }
    }
}

// helper function to determine the next input to focus on based on the id, which is x_y
function getNextInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    // the next one could be on the right or below
    const right = document.getElementById(`${x + 1}_${y}`);
    if (right) {
        return right;
    }
    const below = document.getElementById(`${x}_${y + 1}`);
    if (below) {
        return below;
    }
    return current;
}

function getPrevInput(current) {
    const id = current.id;
    const [x, y] = id.split('_').map(Number);
    // the previous one could be on the left or above
    const left = document.getElementById(`${x - 1}_${y}`);
    if (left) {
        return left;
    }
    const above = document.getElementById(`${x}_${y - 1}`);
    if (above) {
        return above;
    }
    return current;
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
                }
            }
        });
    });
});
