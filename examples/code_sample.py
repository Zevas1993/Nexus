"""
Sample Python code with intentional issues to demonstrate Codiga analysis
and opportunities for Tabnine suggestions
"""
import os
import sys
import json
import random
import time
import numpy  # Potentially unused import

# SQL Injection vulnerability example
def get_user_by_id(cursor, user_id):
    # Insecure: String formatting in SQL query
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    return cursor.fetchone()

# Command injection vulnerability
def backup_data(filename):
    # Insecure: User input directly in system command
    os.system("tar -czf /tmp/backup.tar.gz " + filename)
    return True

# Inefficient list operation
def process_items(items):
    results = []
    # Could use list comprehension instead
    for item in items:
        results.append(item.transform())
    return results

# Repeated calculation in loop
def calculate_distances(points):
    total = 0
    # The length calculation is repeated in each iteration
    for i in range(len(points)):
        # Repeated call to points.center() that could be cached
        distance = points[i].distance(points.center())
        total += distance
        # Another call to the same method
        if points[i].distance(points.center()) > 100:
            print("Point is far from center")
    return total

# Too many function arguments
def create_user(first_name, last_name, email, phone, address, city, state, country, postal_code, company, position, department, start_date, salary, manager_id, is_admin, status):
    # Function has too many parameters
    user = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        # ... many more fields
    }
    return user

# Nested loops that could be improved
def find_pairs(items):
    results = []
    # Deeply nested loops
    for i in range(len(items)):
        for j in range(len(items)):
            if i == j:
                continue
            for k in range(len(items[i])):
                if items[i][k] == items[j][k]:
                    results.append((i, j, k))
    return results

# Insecure deserialization
def load_config(config_file):
    with open(config_file, 'rb') as f:
        # Insecure: pickle.loads with untrusted data
        import pickle
        return pickle.loads(f.read())

# Long line example
def some_function():
    # This line is too long and should be broken into multiple lines according to PEP 8 guidelines
    result = calculate_something_complex(first_parameter, second_parameter, third_parameter) + calculate_something_else(fourth_parameter, fifth_parameter) + final_calculation(sixth_parameter)
    return result

# Function that could benefit from type hints
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

# Class that could benefit from proper docstrings
class DataProcessor:
    def __init__(self, source):
        self.source = source
        self.processed = False
        
    def process(self):
        # Complex processing logic
        self.processed = True
        return {"status": "success"}
        
    def save(self, destination):
        if not self.processed:
            raise ValueError("Must process data before saving")
        # Save logic here
        return True
