SQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "test",
    "password": "Qwerty@123",
    "database": "bisgenSolutions",
}

BATCH_SIZE = 50  # Number of emails to fetch in each batch
CRON_INTERVAL_IN_SECONDS_SCHEDULER1 = 5  # Interval in seconds
CRON_DURATION_IN_MINUTES_SCHEDULER1 =  30

CRON_INTERVAL_IN_SECONDS_SCHEDULER2 = 5  # Interval in seconds
CRON_DURATION_IN_MINUTES_SCHEDULER2 =  30
EMAIL_PROCESS_BATCH_SIZE = 10

# JWT CONFIG 
JWT_SECRET_KEY = "H9f$mK2#pL5vR8nX@jQ4wC7yT0bN3gA6*sE1iD9uZ"
JWT_ALGORITHM = "HS256"

# Flask Secret Key
FLASK_SECRET_KEY = "xK9#mP2$vR5nL8@jW4hQ7yT0bN3gA6*sE1iD9uZ&cF2mX4"