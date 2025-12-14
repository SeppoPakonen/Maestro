#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Structure definition
typedef struct {
    int id;
    char name[50];
    float value;
} Item;

// Function declarations
Item* create_item(int id, const char* name, float value);
void print_item(const Item* item);
void free_item(Item* item);
int compare_items(const void* a, const void* b);

// Main function demonstrating C features
int main() {
    printf("C to C++ Conversion Test\n");
    
    // Create an item
    Item* my_item = create_item(1, "Test Item", 42.5);
    print_item(my_item);
    
    // Array of items
    Item items[3];
    items[0] = *create_item(3, "Third", 3.0f);
    items[1] = *create_item(1, "First", 1.0f);
    items[2] = *create_item(2, "Second", 2.0f);
    
    // Sort items by ID
    qsort(items, 3, sizeof(Item), compare_items);
    
    printf("\nSorted items:\n");
    for (int i = 0; i < 3; i++) {
        print_item(&items[i]);
    }
    
    // Clean up
    free_item(my_item);
    
    return 0;
}

// Function implementations
Item* create_item(int id, const char* name, float value) {
    Item* item = malloc(sizeof(Item));
    if (item != NULL) {
        item->id = id;
        strncpy(item->name, name, sizeof(item->name) - 1);
        item->name[sizeof(item->name) - 1] = '\0';  // Ensure null termination
        item->value = value;
    }
    return item;
}

void print_item(const Item* item) {
    if (item != NULL) {
        printf("ID: %d, Name: %s, Value: %.2f\n", item->id, item->name, item->value);
    }
}

void free_item(Item* item) {
    if (item != NULL) {
        free(item);
    }
}

int compare_items(const void* a, const void* b) {
    const Item* item_a = (const Item*)a;
    const Item* item_b = (const Item*)b;
    return item_a->id - item_b->id;
}