from security.authToken import AuthToken
from flask import redirect,session

def auth_required():
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'authToken' in session:
                try:
                    user = AuthToken().decode(session['authToken'])
                    if user:
                        # Pass the user data to the decorated function
                        return func(current_user=user, *args, **kwargs)
                except Exception as e:
                    print(f"Auth Error: {str(e)}")
                    return redirect("/signin")
            return redirect("/signin")
        return wrapper
    return decorator

def allowed_user_type(allowed_roles=[]):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'authToken' in session:
                try:
                    user = AuthToken().decode(session['authToken'])
                    if user and user.get('user_type') in allowed_roles:
                        return func(current_user=user, *args, **kwargs)
                    return redirect("/signin")
                except Exception as e:
                    print(f"Auth Error: {str(e)}")
                    return redirect("/signin")
            return redirect("/signin")
        return wrapper
    return decorator