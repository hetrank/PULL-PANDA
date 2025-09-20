import hashlib

def login(username, password):
    # UNSAFE: Plain text password comparison
    if username == "admin" and password == "admin123":
        return True
    return False

# FIXED: Use hashing
def secure_login(username, password):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    stored_hash = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # admin123
    
    if username == "admin" and hashed_password == stored_hash:
        return True
    return False