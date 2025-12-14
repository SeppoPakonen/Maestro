"""Data models with basic structures but no type hints."""

# Basic data structures without type hints
class Person:
    def __init__(self, name, age, email):
        self.name = name
        self.age = age
        self.email = email

    def __repr__(self):
        return f'Person(name="{self.name}", age={self.age}, email="{self.email}")'


# Simple data storage
def create_person_dict(name, age, email):
    return {
        'name': name,
        'age': age,
        'email': email,
        'metadata': {
            'created_at': '2023-01-01',
            'updated_at': '2023-01-01'
        }
    }


# Configuration-like dictionary
config = {
    'database_url': 'sqlite:///example.db',
    'debug': True,
    'max_connections': 10,
    'features': {
        'logging': True,
        'caching': True,
        'monitoring': False
    }
}