"""
Example of code with "converted smell" - patterns that indicate suboptimal conversion
and could benefit from refactoring.
"""

# 1. Inconsistent naming (not following target language conventions)
def calculateTotalAmount(items):
    # Mixed naming conventions (camelCase vs snake_case)
    totalSum = 0
    for item in items:
        item_total = item['price'] * item['quantity']
        totalSum += item_total
    return totalSum

# 2. Repetitive helper functions
def validate_email_format(email):
    if not email or '@' not in email:
        return False
    return True

def validate_username_format(username):
    if not username or len(username) < 3:
        return False
    return True

def validate_password_format(password):
    if not password or len(password) < 8:
        return False
    return True

# 3. Error handling inconsistencies
class DataProcessor:
    def process_data(self, data):
        try:
            result = self._process_raw_data(data)
            return result
        except Exception as e:
            # Generic exception catching
            print(f"Error processing data: {e}")
            return None  # Returning None instead of raising proper exception
    
    def _process_raw_data(self, raw_data):
        if raw_data is None:
            raise ValueError("Raw data cannot be None")  # Proper exception
        return raw_data

# 4. Type annotations overuse of Any (if this were typed)
def generic_function(data):  # Should have proper type annotations
    # This function could benefit from proper typing
    processed = []
    for item in data:
        processed.append(str(item))
    return processed

# 5. Non-idiomatic code patterns
def filter_items(items, condition):
    # Non-idiomatic - should use list comprehension or filter
    results = []
    for item in items:
        if condition(item):
            results.append(item)
    return results

# 6. Duplicated code patterns
def process_user_data(user_data):
    # Validation step 1
    if not user_data:
        raise ValueError("User data is required")
    
    # Validation step 2  
    if 'email' not in user_data:
        raise ValueError("Email is required")
    
    # Processing
    user_data['processed'] = True
    return user_data

def process_product_data(product_data):
    # Validation step 1 - DUPLICATED CODE
    if not product_data:
        raise ValueError("Product data is required")
    
    # Validation step 2 - DUPLICATED CODE
    if 'name' not in product_data:
        raise ValueError("Name is required")
    
    # Processing
    product_data['processed'] = True
    return product_data

# 7. API clarity issues
def complex_function_with_unclear_name_that_does_multiple_things(a, b, c, d, e):
    """
    Function with unclear purpose and too many parameters
    """
    return a + b * c - d / e if e != 0 else 0

# 8. Old-style code patterns from source language
def old_style_pattern():
    # Using old-style patterns that don't leverage target language idioms
    items = [1, 2, 3, 4, 5]
    result = []
    for i in range(len(items)):
        if items[i] % 2 == 0:
            result.append(items[i])
    return result