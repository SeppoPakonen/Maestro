#include "sample_project.h"

namespace math_utils {

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
        throw std::runtime_error("Division by zero");
    }
}

} // namespace math_utils