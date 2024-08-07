# context_processors.py
def user_role(request):
    user_role = request.user.groups
    if request.user.groups.filter(name='admin').exists():
        user_role = 'admin'
    elif request.user.groups.filter(name='operator').exists():
        user_role = 'operator'
    elif request.user.groups.filter(name='user').exists():
        user_role = 'user'
    return {'user_role': user_role}
