// More complex JavaScript code that will need strict typing
const fs = require('fs');
const path = require('path');

// Function with complex object manipulation
function handleComplexData(data) {
    // Process nested objects without type checking
    const result = {};
    
    for (const key in data) {
        if (data.hasOwnProperty(key)) {
            if (typeof data[key] === 'object' && data[key] !== null) {
                result[key] = handleComplexData(data[key]); // recursive processing
            } else {
                result[key] = data[key];
            }
        }
    }
    
    return result;
}

// Async function with promise
async function fetchDataFromApi(url) {
    // Simulate API call without type safety
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                url: url,
                data: 'Sample data',
                timestamp: Date.now()
            });
        }, 100);
    });
}

// Generic array processing
function processDataArray(items) {
    return items.map(item => {
        // Dynamic property access without type checking
        return {
            id: item.id,
            processed: true,
            original: item
        };
    }).filter(processedItem => processedItem.id);
}

// Export functions
module.exports = {
    handleComplexData,
    fetchDataFromApi,
    processDataArray
};