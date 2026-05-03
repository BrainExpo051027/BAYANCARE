import random
import string

def generate_referral_code(length=8):
    """Generate a unique referral code like BRG-XXXXXX."""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(chars, k=length))
    return f"BRG-{code}"
