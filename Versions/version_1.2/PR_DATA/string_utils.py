def reverse_string(s):
    # BUG: This doesn't work for empty strings
    return s[::-1]

def count_vowels(s):
    # BUG: Counts 'y' as vowel incorrectly
    vowels = "aeiouy"
    return sum(1 for char in s.lower() if char in vowels)

def is_palindrome(s):
    # BUG: Doesn't handle case sensitivity
    return s == s[::-1]

def capitalize_words(s):
    # BUG: Multiple spaces cause issues
    words = s.split()
    return ' '.join(word.capitalize() for word in words)