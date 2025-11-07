import string
import secrets

# --- Generate a secure random code ---
def generate_random_code(length: int = 8) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))