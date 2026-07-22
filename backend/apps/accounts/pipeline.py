def assign_default_role(strategy, details, user=None, *args, **kwargs):
    if user:
        if not user.role:
            user.role = 'STANDARD'
            user.save()
    return {'is_new': False}
