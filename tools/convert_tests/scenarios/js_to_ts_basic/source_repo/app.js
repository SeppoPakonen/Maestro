// Main application file demonstrating various JavaScript features
const express = require('express');
const app = express();
const port = 3000;

// Basic function with various JavaScript patterns
function calculateSum(a, b) {
    if (typeof a !== 'number' || typeof b !== 'number') {
        throw new Error('Both arguments must be numbers');
    }
    return a + b;
}

// Arrow function
const multiply = (x, y) => x * y;

// Class declaration
class Calculator {
    constructor(initialValue = 0) {
        this.value = initialValue;
    }

    add(number) {
        this.value += number;
        return this;
    }

    subtract(number) {
        this.value -= number;
        return this;
    }

    getResult() {
        return this.value;
    }
}

// Module exports
module.exports = {
    calculateSum,
    multiply,
    Calculator
};

// For standalone execution
if (require.main === module) {
    const calc = new Calculator(10);
    console.log('Initial value:', calc.getResult());
    console.log('After adding 5:', calc.add(5).getResult());
    console.log('After subtracting 3:', calc.subtract(3).getResult());
    
    app.get('/', (req, res) => {
        res.send('Hello World!');
    });

    app.listen(port, () => {
        console.log(`Server running at http://localhost:${port}`);
    });
}