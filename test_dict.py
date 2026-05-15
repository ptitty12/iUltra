import json

f = r"\\amznfsxzfj3dk8a.gad.schneider-electric.com\share\SPAnalytics\NAM\Projects\2026 PST\sch\project\04_oppReadout\email.json"

with open(f, "r") as file:
    emails_raw = json.load(file)
emails = json.loads(emails_raw[0]['json_out'])
print(emails.keys())
#emails_dict = {item['id']: item for item in emails}

#[print(k,v) for k,v in data.items()]