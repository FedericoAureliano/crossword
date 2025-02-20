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

// Add event listeners to all inputs
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', checkInputs);
    });
});
