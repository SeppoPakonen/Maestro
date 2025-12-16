# C++ to C Conversion Examples

## RAII Conversion Examples

### Before (C++)
```cpp
class FileHandler {
private:
    std::ifstream file;
public:
    FileHandler(const std::string& filename) : file(filename) {}
    ~FileHandler() { if (file.is_open()) file.close(); }
    std::string readLine() { std::string line; std::getline(file, line); return line; }
};
```

### After (C)
```c
typedef struct {
    FILE* file;
} FileHandler;

int file_handler_init(FileHandler* handler, const char* filename) {
    handler->file = fopen(filename, "r");
    return handler->file != NULL ? 0 : -1;
}

void file_handler_cleanup(FileHandler* handler) {
    if (handler->file) {
        fclose(handler->file);
        handler->file = NULL;
    }
}

char* file_handler_read_line(FileHandler* handler) {
    // Implementation here
    return NULL;
}
```

## Exception Conversion Examples

### Before (C++)
```cpp
try {
    risky_operation();
} catch (const std::exception& e) {
    handle_error(e.what());
}
```

### After (C)
```c
int result = risky_operation();
if (result != 0) {
    handle_error(result);
}
```

## Template Conversion Examples

### Before (C++)
```cpp
template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}
```

### After (C)
```c
#define MAX(type, a, b) ((a) > (b) ? (a) : (b))

// Or for type safety:
int int_max(int a, int b) { return (a > b) ? a : b; }
double double_max(double a, double b) { return (a > b) ? a : b; }
```