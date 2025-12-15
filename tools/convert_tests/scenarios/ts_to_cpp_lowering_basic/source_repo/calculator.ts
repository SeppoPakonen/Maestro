// Calculator with advanced features using TypeScript
interface CalculationResult {
  result: number;
  operation: string;
  timestamp: Date;
}

interface SequenceConfig {
  start: number;
  end: number;
  step?: number;
}

class Calculator {
  private history: CalculationResult[] = [];

  constructor() {
    console.log("Calculator initialized with TypeScript features");
  }

  async add(a: number, b: number): Promise<number> {
    const result = a + b;
    this.addToHistory(result, `add(${a}, ${b})`);
    return result;
  }

  multiply(a: number, b: number): number {
    const result = a * b;
    this.addToHistory(result, `multiply(${a}, ${b})`);
    return result;
  }

  divide(a: number, b: number): Promise<number> {
    return new Promise((resolve, reject) => {
      if (b !== 0) {
        const result = a / b;
        this.addToHistory(result, `divide(${a}, ${b})`);
        resolve(result);
      } else {
        reject(new Error("Division by zero"));
      }
    });
  }

  private addToHistory(result: number, operation: string): void {
    this.history.push({
      result,
      operation,
      timestamp: new Date()
    });
  }

  public getHistory(): CalculationResult[] {
    return [...this.history]; // Return a copy
  }

  public clearHistory(): void {
    this.history = [];
  }

  public getSequence(config: SequenceConfig): number[] {
    const step = config.step || 1;
    const sequence: number[] = [];
    
    for (let i = config.start; i < config.end; i += step) {
      sequence.push(i);
    }
    
    return sequence;
  }

  public async processBatch(operations: [string, number, number][]): Promise<number[]> {
    const results: number[] = [];
    
    for (const [op, a, b] of operations) {
      switch (op) {
        case 'add':
          results.push(await this.add(a, b));
          break;
        case 'multiply':
          results.push(this.multiply(a, b));
          break;
        case 'divide':
          try {
            results.push(await this.divide(a, b));
          } catch (error) {
            results.push(0); // Default on error
          }
          break;
        default:
          results.push(0);
      }
    }
    
    return results;
  }
}

// Async function to demonstrate TypeScript async/await
async function runCalculatorDemo(): Promise<void> {
  console.log("TypeScript Calculator Demo");
  
  const calc = new Calculator();
  
  // Basic operations
  console.log("2 + 3 =", await calc.add(2, 3));
  console.log("4 * 5 =", calc.multiply(4, 5));
  
  try {
    console.log("10 / 2 =", await calc.divide(10, 2));
  } catch (error) {
    console.error("Division error:", error.message);
  }
  
  // Sequence generation
  const sequence = calc.getSequence({ start: 1, end: 10, step: 2 });
  console.log("Sequence:", sequence);
  
  // Batch processing
  const batchResults = await calc.processBatch([
    ['add', 1, 2],
    ['multiply', 3, 4],
    ['divide', 20, 4]
  ]);
  
  console.log("Batch results:", batchResults);
  
  // Show history
  console.log("Calculation history:", calc.getHistory());
}

// Run the demo
runCalculatorDemo().catch(console.error);

export { Calculator, type CalculationResult, type SequenceConfig };