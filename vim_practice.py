"""
Vim Navigation Practice File
=============================
This file has multiple sections, functions, and patterns
to practice moving around efficiently.
"""

import math
import random
from collections import defaultdict


# ── Section 1: Data Structures ──

COLORS = [
    "red", "blue", "green", "yellow", "purple",
    "orange", "pink", "cyan", "magenta", "teal",
]

SCORES = {
    "alice": 92,
    "bob": 87,
    "charlie": 95,
    "diana": 78,
    "eve": 99,
    "frank": 64,
    "grace": 88,
    "heidi": 91,
}


# ── Section 2: Basic Functions ──

def greet(name):
    """Return a greeting string."""
    return f"Hello, {name}! Welcome to the practice file."


def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    total = sum(numbers)
    count = len(numbers)
    average = total / count
    return round(average, 2)


def fibonacci(n):
    """Generate the first n Fibonacci numbers."""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    sequence = [0, 1]
    for i in range(2, n):
        next_val = sequence[i - 1] + sequence[i - 2]
        sequence.append(next_val)
    return sequence


def is_prime(num):
    """Check if a number is prime."""
    if num < 2:
        return False
    if num == 2:
        return True
    if num % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(num)) + 1, 2):
        if num % i == 0:
            return False
    return True


# ── Section 3: String Processing ──

def reverse_words(sentence):
    """Reverse each word in a sentence."""
    words = sentence.split()
    reversed_words = [word[::-1] for word in words]
    return " ".join(reversed_words)


def count_vowels(text):
    """Count vowels in a string."""
    vowels = "aeiouAEIOU"
    count = 0
    for char in text:
        if char in vowels:
            count += 1
    return count


def caesar_cipher(text, shift):
    """Apply a Caesar cipher to the text."""
    result = []
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            shifted = (ord(char) - base + shift) % 26 + base
            result.append(chr(shifted))
        else:
            result.append(char)
    return "".join(result)


# ── Section 4: Data Analysis ──

def find_outliers(data, threshold=2.0):
    """Find outliers using standard deviation."""
    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / len(data)
    std_dev = math.sqrt(variance)
    outliers = []
    for value in data:
        z_score = abs(value - mean) / std_dev if std_dev > 0 else 0
        if z_score > threshold:
            outliers.append(value)
    return outliers


def build_histogram(data, bins=10):
    """Build a simple text histogram."""
    min_val = min(data)
    max_val = max(data)
    bin_width = (max_val - min_val) / bins
    histogram = defaultdict(int)
    for value in data:
        bin_index = int((value - min_val) / bin_width)
        bin_index = min(bin_index, bins - 1)
        histogram[bin_index] += 1
    return dict(histogram)


def moving_average(data, window=3):
    """Calculate the moving average of a dataset."""
    if len(data) < window:
        return data[:]
    result = []
    for i in range(len(data) - window + 1):
        window_slice = data[i:i + window]
        avg = sum(window_slice) / window
        result.append(round(avg, 2))
    return result


# ── Section 5: Matrix Operations ──

def create_matrix(rows, cols, fill=0):
    """Create a matrix filled with a default value."""
    return [[fill for _ in range(cols)] for _ in range(rows)]


def multiply_matrices(a, b):
    """Multiply two matrices."""
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    if cols_a != rows_b:
        raise ValueError("Incompatible matrix dimensions")
    result = create_matrix(rows_a, cols_b)
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]
    return result


def transpose(matrix):
    """Transpose a matrix."""
    rows = len(matrix)
    cols = len(matrix[0])
    result = create_matrix(cols, rows)
    for i in range(rows):
        for j in range(cols):
            result[j][i] = matrix[i][j]
    return result


# ── Section 6: Error-Prone Code (find the bugs!) ──

def buggy_sort(arr):
    """A sorting function with a subtle bug."""
    sorted_arr = arr[:]
    for i in range(len(sorted_arr)):
        for j in range(i + 1, len(sorted_arr)):
            if sorted_arr[i] > sorted_arr[j]:
                sorted_arr[i], sorted_arr[j] = sorted_arr[j], sorted_arr[i]
    return sorted_arr


def buggy_search(arr, target):
    """Binary search with an off-by-one error."""
    low = 0
    high = len(arr)
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


# ── Section 7: Main ──

if __name__ == "__main__":
    print("=== Greeting ===")
    print(greet("Sujai"))

    print("\n=== Fibonacci ===")
    fib = fibonacci(15)
    print(f"First 15: {fib}")

    print("\n=== Primes ===")
    primes = [n for n in range(2, 50) if is_prime(n)]
    print(f"Primes under 50: {primes}")

    print("\n=== Caesar Cipher ===")
    secret = caesar_cipher("Hello World", 3)
    print(f"Encrypted: {secret}")
    print(f"Decrypted: {caesar_cipher(secret, -3)}")

    print("\n=== Scores ===")
    avg = calculate_average(list(SCORES.values()))
    print(f"Average score: {avg}")

    print("\n=== Moving Average ===")
    data = [random.randint(1, 100) for _ in range(20)]
    print(f"Data: {data}")
    print(f"Moving avg (window=5): {moving_average(data, 5)}")
