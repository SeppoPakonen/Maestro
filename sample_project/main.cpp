#include <iostream>
#include "sample_project.h"

int main() {
    int result1 = math_utils::add(5, 3);
    int result2 = math_utils::multiply(4, 6);
    double result3 = math_utils::divide(10.0, 2.0);
    
    std::cout << "Addition: " << result1 << std::endl;
    std::cout << "Multiplication: " << result2 << std::endl;
    std::cout << "Division: " << result3 << std::endl;
    
    return 0;
}