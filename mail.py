# Some variable for email
Server = 'localhost'
My_email = 'admin@localhost'
Sender = 'ADMIN@LISTSERV.LOCALHOST'
Sender_alias = 'Services'
Subject = 'New User Account'
Info_url = 'https://www.google.com'

Head = f"""From: {Sender_alias} <{Sender}>
To: <{{{{ to }}}}>
Subject: {Subject}
"""

Body = f"""
Hi {{{{ username }}}}
Your account has been set up with:

============================
User ID:  {{{{ username }}}}
============================

If you have any questions, please visit:
{Info_url}

or email at {My_email}

Cheers,
"""

Whole_mail = Head + Body
