from functools import wraps
from flask import redirect, session
from security.authToken import AuthToken

def is_authenticated():
    if 'authToken' in session:
        try:
            user = AuthToken().decode(session['authToken'])
            if user:
                return user
        except Exception as e:
            print(f"Auth Error: {str(e)}")
    return None

def auth_required():
    def decorator(func):
        @wraps(func)  # This preserves the original function's metadata, including its name
        def wrapper(*args, **kwargs):
            user = is_authenticated()
            if not user:
                return redirect("/signin")
            return func(current_user=user, *args, **kwargs)
        return wrapper
    return decorator

def allowed_user_type(allowed_roles=[]):
    def decorator(func):
        @wraps(func)  # This ensures Flask recognizes the original function's name
        def wrapper(*args, **kwargs):
            user = is_authenticated()
            if not user or user.get("user_type") not in allowed_roles:
                return redirect("/signin")
            return func(current_user=user, *args, **kwargs)
        return wrapper
    return decorator
