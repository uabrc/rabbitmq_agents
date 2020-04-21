# Some variable for email
my_email = 'admin@localhost'
info_url = 'https://www.google.com'

body = f"""
Hi {{{{ username }}}}
Your account has been set up with:

============================
User ID:  {{{{ username }}}}
============================

If you have any questions, please visit:
{info_url}

or email at {my_email}

Cheers,
"""
