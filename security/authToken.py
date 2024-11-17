import jwt
import datetime
import config

class AuthToken() : 

    def __init__(self) -> None:
        
        self.secretKey = config.JWT_SECRET_KEY
        self.algorithm = config.JWT_ALGORITHM

    def encode(self, user: dict, expires_in=8766): 
        payload = user.copy()
        tokenExpiryTime = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours = expires_in)
        payload['exp'] = tokenExpiryTime
        authToken = jwt.encode(payload, self.secretKey, algorithm=self.algorithm)
        return authToken, tokenExpiryTime
    
    def decode(self,token):
        try:
            user = jwt.decode(token, self.secretKey, algorithms=[self.algorithm])
            return user
        except jwt.ExpiredSignatureError:
            print("Token Expired")
            return None
        except jwt.InvalidTokenError:
            print("Invalid token")
            return None
        except jwt.InvalidKeyError:
            print('Invalid Key Error')
            return None
        except Exception as e:
            print(e)
            return None
        



