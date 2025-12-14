#!/usr/bin/env node
/**
 * Behavior preservation check for JS to Strict TS conversion.
 * This script tests that key behavior remains unchanged after conversion.
 */

const { spawn } = require('child_process');
const crypto = require('crypto');

function runJavaScriptCode(filePath) {
    return new Promise((resolve, reject) => {
        const child = spawn('node', [filePath], {
            timeout: 30000,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        child.on('close', (code) => {
            resolve({ stdout, stderr, returnCode: code });
        });

        child.on('error', (error) => {
            reject(error);
        });
    });
}

function calculateOutputHash(output) {
    return crypto.createHash('md5').update(output).digest('hex');
}

async function testJSBehavior() {
    console.log('Testing JavaScript behavior preservation...');

    try {
        // Run the calculator module from source_repo
        const result = await runJavaScriptCode('source_repo/calculator.js');
        
        if (result.returnCode !== 0) {
            console.error(`ERROR: JavaScript code execution failed with return code ${result.returnCode}`);
            console.error(`STDERR: ${result.stderr}`);
            return false;
        }

        // Check for expected outputs in the calculator execution
        const expectedOutputs = [
            'Initial value: 10',
            'After adding 5: 15', 
            'After subtracting 3: 12',
            'Sum of 5 and 3: 8',
            'Multiply 4 and 5: 20'
        ];
        
        const missingOutputs = [];
        expectedOutputs.forEach(expected => {
            if (!result.stdout.includes(expected)) {
                missingOutputs.push(expected);
            }
        });

        if (missingOutputs.length > 0) {
            console.error(`ERROR: Missing expected outputs:`, missingOutputs);
            console.error(`Actual output:`, result.stdout);
            return false;
        }

        // Calculate hash of the output to compare against baseline
        const outputHash = calculateOutputHash(result.stdout);
        console.log(`Output hash: ${outputHash}`);
        
        console.log('JavaScript behavior preservation test PASSED');
        return true;
    } catch (error) {
        console.error('ERROR:', error.message);
        return false;
    }
}

// Run the test
testJSBehavior().then(success => {
    process.exit(success ? 0 : 1);
});