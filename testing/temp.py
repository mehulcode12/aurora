import requests

url = "http://localhost:5000/api/workers"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJUMVIySGc3MFRCYkgzcXRoRkJ3Qk5aZXdsejUzIiwiZW1haWwiOiJvbXN2ZXJpMDE0M0BnbWFpbC5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU5NjIwMzM1LCJpYXQiOjE3NTk1MzM5MzV9.atI54kHiF1G-4C1X7lFtyHfXPNGCD8-oje4RohdMtEE"
}
response = requests.get(url, headers=headers)

print(response.status_code)
print(response.json())
