"""Calculator module demonstrating various Python constructs without type hints."""

# Basic function without type hints
def calculate_sum(a, b):
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError('Both arguments must be numbers')
    return a + b


# Arrow-function equivalent using lambda
multiply = lambda x, y: x * y


# Class with instance variables but no type hints
class Calculator:
    def __init__(self, initial_value=0):
        self.value = initial_value

    def add(self, number):
        self.value += number
        return self

    def subtract(self, number):
        self.value -= number
        return self

    def get_result(self):
        return self.value


# Dictionary manipulation function
def process_user_data(users):
    """Process user data where each user has an 'active' status."""
    return {
        user['id']: {
            'name': user['name'],
            'email': user['email'].lower(),
            'active': user['active']
        }
        for user in users if user.get('active', False)
    }


# List processing function
def calculate_totals(items):
    """Calculate totals from a list of items."""
    total_count = 0
    total_price = 0
    
    for item in items:
        total_count += item.get('quantity', 0)
        total_price += item.get('price', 0) * item.get('quantity', 0)
    
    return {
        'count': total_count,
        'total': total_price,
        'average': total_price / total_count if total_count > 0 else 0
    }


# Async function demonstration
import asyncio

async def fetch_data_async(url):
    """Simulate async data fetching."""
    await asyncio.sleep(0.1)  # Simulate network delay
    return {'url': url, 'data': f'Data from {url}'}


# Main execution block
if __name__ == '__main__':
    calc = Calculator(10)
    print('Initial value:', calc.get_result())
    print('After adding 5:', calc.add(5).get_result())
    print('After subtracting 3:', calc.subtract(3).get_result())
    
    # Test functions
    print('Sum of 5 and 3:', calculate_sum(5, 3))
    print('Multiply 4 and 5:', multiply(4, 5))
    
    # Process sample data
    users = [
        {'id': 1, 'name': 'Alice', 'email': 'ALICE@EXAMPLE.COM', 'active': True},
        {'id': 2, 'name': 'Bob', 'email': 'BOB@EXAMPLE.COM', 'active': False},
        {'id': 3, 'name': 'Charlie', 'email': 'CHARLIE@EXAMPLE.COM', 'active': True}
    ]
    
    processed_users = process_user_data(users)
    print('Processed users:', processed_users)
    
    items = [
        {'name': 'item1', 'price': 10, 'quantity': 2},
        {'name': 'item2', 'price': 15, 'quantity': 3},
        {'name': 'item3', 'price': 8, 'quantity': 1}
    ]
    
    totals = calculate_totals(items)
    print('Totals:', totals)