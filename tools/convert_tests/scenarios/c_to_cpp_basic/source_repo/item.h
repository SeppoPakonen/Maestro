#ifndef ITEM_H
#define ITEM_H

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

#endif // ITEM_H