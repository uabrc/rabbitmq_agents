# Some variable for email
Server = 'localhost'
Admin_email = 'root@localhost'
Sender = 'ROOT@LOCALHOST'
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

or email at {Admin_email}

Cheers,
"""

Whole_mail = Head + Body

UserReportHead = f"""From: {Sender_alias} <{Sender}>
To: <{Admin_email}>
Subject: RC Account Creation Report: {{{{ fullname  }}}}, {{{{ username }}}}
"""

