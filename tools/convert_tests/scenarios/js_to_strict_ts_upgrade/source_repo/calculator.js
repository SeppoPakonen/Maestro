// Basic calculator functions without TypeScript types
function calculateSum(a, b) {
    if (typeof a !== 'number' || typeof b !== 'number') {
        throw new Error('Both arguments must be numbers');
    }
    return a + b;
}

// Arrow function without types
const multiply = (x, y) => x * y;

// Class without type annotations
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

// Object manipulation function
function processUserData(users) {
    return users.filter(user => user.active)
               .map(user => ({ ...user, processed: true }));
}

// Configuration object without type
const config = {
    apiUrl: 'https://api.example.com',
    timeout: 5000,
    retries: 3,
    features: {
        caching: true,
        logging: false
    }
};

// Main execution
if (typeof window === 'undefined') { // Node.js environment
    const calc = new Calculator(10);
    console.log('Initial value:', calc.getResult());
    console.log('After adding 5:', calc.add(5).getResult());
    console.log('After subtracting 3:', calc.subtract(3).getResult());

    console.log('Sum of 5 and 3:', calculateSum(5, 3));
    console.log('Multiply 4 and 5:', multiply(4, 5));

    const users = [
        { id: 1, name: 'Alice', active: true },
        { id: 2, name: 'Bob', active: false },
        { id: 3, name: 'Charlie', active: true }
    ];
    
    const processedUsers = processUserData(users);
    console.log('Processed users:', processedUsers);
}

// Export for modules
module.exports = {
    calculateSum,
    multiply,
    Calculator,
    processUserData,
    config
};