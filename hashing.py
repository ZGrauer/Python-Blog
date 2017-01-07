import os
import re
import string
import random
import hashlib
import hmac

SECRET = "LVFuBg9EM8Bq3cd992Tb5g01Uh30GCV2"

def make_salt():
    '''Makes random string of letters for password salts

    Args:
        None

    Returns:
        String of 5 random letters
    '''
    return "".join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
    '''Hash password with SHA256 using name & salt

    Args:
        name: String username
        pw: String cleartext password
        salt: String, optional. If none one is generated.

    Returns:
        String of hashed password with salt, seperated by comma
    '''
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (h, salt)

def valid_pw(name, pw, h):
    '''Checks if a password matches a hash

    Args:
        name: String username
        pw: String cleartext password
        h: String, hash of password

    Returns:
        True if cleartext password equals the hashed password
    '''
    salt = h.split(",")[1]
    if h==make_pw_hash(name, pw, salt):
        return True

def hash_str(s):
    '''Hash a string using HMAC

    Used for cookies.  Uses SECRET value at top

    Args:
        s: String to be hashed

    Returns:
        hash digest for HMAC on string
    '''
    return hmac.new(SECRET,s).hexdigest()

def make_secure_val(s):
    '''Add a HMAC hash digest to string

    Used for cookies

    Args:
        s: String to have hash added

    Returns:
        String with HMAC of string.  Seperated by pipe "|"
    '''
    return "%s|%s" % (s, hash_str(s))

def check_secure_val(h):
    '''Verifies cookie is valid using HMAC

    Used for cookies

    Args:
        h: String cookie value.  "string|hash"

    Returns:
        String cookie value without hash
    '''
    val = h.split("|")[0]
    if h == make_secure_val(val):
        return val
