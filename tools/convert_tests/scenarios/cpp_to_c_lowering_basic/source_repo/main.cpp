#include <iostream>
#include <vector>
#include <string>
#include <memory>

class Calculator {
public:
    Calculator() {
        std::cout << "Calculator created!" << std::endl;
    }
    
    ~Calculator() {
        std::cout << "Calculator destroyed!" << std::endl;
    }
    
    int add(int a, int b) {
        return a + b;
    }
    
    int multiply(int a, int b) {
        return a * b;
    }
    
    double divide(double a, double b) {
        if (b != 0) {
            return a / b;
        } else {
            std::cerr << "Error: Division by zero!" << std::endl;
            return 0.0;
        }
    }
    
    std::vector<int> getSequence(int start, int end) {
        std::vector<int> result;
        for (int i = start; i < end; i++) {
            result.push_back(i);
        }
        return result;
    }
};

int main() {
    std::cout << "C++ Calculator Example" << std::endl;
    
    Calculator calc;
    
    // Test basic operations
    std::cout << "2 + 3 = " << calc.add(2, 3) << std::endl;
    std::cout << "4 * 5 = " << calc.multiply(4, 5) << std::endl;
    std::cout << "10 / 2 = " << calc.divide(10, 2) << std::endl;
    
    // Test vector functionality
    auto sequence = calc.getSequence(1, 5);
    std::cout << "Sequence: ";
    for (auto num : sequence) {
        std::cout << num << " ";
    }
    std::cout << std::endl;
    
    // Test smart pointers
    std::unique_ptr<Calculator> calcPtr = std::make_unique<Calculator>();
    std::cout << "Smart pointer test: 7 + 8 = " << calcPtr->add(7, 8) << std::endl;
    
    return 0;
}