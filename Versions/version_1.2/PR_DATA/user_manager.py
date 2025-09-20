# OLD: Monolithic function
def process_user_data(users):
    results = []
    for user in users:
        if user['age'] >= 18:
            user['status'] = 'adult'
            if user['score'] > 80:
                user['category'] = 'premium'
            else:
                user['category'] = 'standard'
        else:
            user['status'] = 'minor'
            user['category'] = 'standard'
        
        if user['active']:
            results.append(user)
    return results

# NEW: Refactored with helper functions
def is_adult(user):
    return user['age'] >= 18

def get_user_category(user):
    if user['score'] > 80:
        return 'premium'
    return 'standard'

def process_user_data_refactored(users):
    return [
        {
            **user,
            'status': 'adult' if is_adult(user) else 'minor',
            'category': get_user_category(user) if is_adult(user) else 'standard'
        }
        for user in users
        if user['active']
    ]