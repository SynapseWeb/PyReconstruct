developers_data = [
    {"name": "Julian Falco", "email": "julian.falco@utexas.edu"},
    {"name": "Michael Chirillo", "email": "m.chirillo@utexas.edu"}
]

developers_names = [person["name"] for person in developers_data]

developers_emails = [person["email"] for person in developers_data]

developers_mailto_str = "mailto:" + ",".join(developers_emails)

