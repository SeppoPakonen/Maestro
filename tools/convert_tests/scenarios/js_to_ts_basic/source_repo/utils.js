// Utility functions demonstrating common JavaScript patterns
const fs = require('fs');
const path = require('path');

// Array methods
function processArray(items) {
    return items
        .filter(item => item.active)
        .map(item => ({ ...item, processed: true }))
        .reduce((acc, curr) => {
            acc[curr.id] = curr;
            return acc;
        }, {});
}

// Object destructuring
function handleUserData({ name, email, age }) {
    return {
        name: name.toUpperCase(),
        email: email.toLowerCase(),
        isAdult: age >= 18
    };
}

// Promise and async/await
async function fetchData(url) {
    try {
        // Simulated fetch
        const data = await new Promise(resolve => {
            setTimeout(() => {
                resolve({ url, timestamp: Date.now() });
            }, 100);
        });
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw error;
    }
}

// Export utilities
module.exports = {
    processArray,
    handleUserData,
    fetchData
};