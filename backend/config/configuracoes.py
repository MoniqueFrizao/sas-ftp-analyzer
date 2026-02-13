# Centralized Configuration for SAS FTP Analyzer

## FTP Settings
ftp_settings = {
    'host': 'ftp.example.com',
    'port': 21,
    'username': 'ftp_user',
    'password': 'ftp_password',
    'timeout': 30
}

## Batch Groups
batch_groups = [
    {
        'name': 'group1',
        'schedule': 'daily',
        'time': '02:00:00'
    },
    {
        'name': 'group2',
        'schedule': 'weekly',
        'time': '03:00:00'
    }
]

## Regex Patterns
regex_patterns = {
    'pattern1': r'^[a-zA-Z0-9_-]{3,15}$',  # Example pattern for usernames
    'pattern2': r'^[A-Za-z0-9]+@[A-Za-z0-9]+\.com$'  # Example pattern for emails
}

## Business Rules
business_rules = {
    'rule1': 'All usernames must be unique.',
    'rule2': 'Passwords must be at least 8 characters long and include a number.',
    'rule3': 'Email must follow a valid format.'
}