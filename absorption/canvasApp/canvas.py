import requests
import datetime
import json
with open("config.json") as f:
    secrets = json.load(f)


# Constants
API_URL = "https://canvas.asu.edu/api/v1"
ACCESS_TOKEN = secrets["canvas"]["api_key"]
# Headers for authentication
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# Function Defs
def get_courses():
    """Fetches a list of courses for the authenticated user."""
    url = f"{API_URL}/courses?page=2"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()


# returns an array of all courses
def get_all_courses():
    pageNumber = 1
    courses = []

    while True:
        url = f"{API_URL}/courses?page={pageNumber}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        print(response.json())
        for i in range(len(response.json())):
            courses.append(response.json()[i])

        if len(response.json()) < 10:
            break
        pageNumber += 1
    
    return courses


def get_announcements():
    """Fetches announcement."""
    # Fetch a list of all course IDs for the authenticated user's active courses
    courses_url = f"{API_URL}/courses"
    params = {"enrollment_state": "active", "include[]": "id"}
    courses_response = requests.get(courses_url, headers=HEADERS, params=params)
    courses_response.raise_for_status()
    courses = courses_response.json()

    # Extract the course IDs from the response
    course_ids = [course["id"] for course in courses]

    url = f"{API_URL}/announcements"
    params = {
        "context_codes[]": [
            f"course_{course_id}" for course_id in course_ids
        ],  # get announcements from all courses
        "start_date": (
            datetime.date.today() - datetime.timedelta(days=7)
        ).isoformat(),  # get announcements from the past week onwards
        "end_date": (
            datetime.date.today() + datetime.timedelta(days=30)
        ).isoformat(),  # get announceiments up to today
        "active_only": True,
        "per_page": 100,  # get 100 announcements per page
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_announcement(course_id):
    """Fetches announcements for a specific couse."""
    url = f"{API_URL}/announcements"
    params = {
        "context_codes[]": f"course_{course_id}",  # Specify the course ID context
        "per_page": 100,  # Optional: specify the number of results per page
    }
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_assignments(course_id):
    """Fetches assignments for a specific course."""
    url = f"{API_URL}/courses/{course_id}/assignments"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_modules(course_id):
    url = f"{API_URL}/courses/{course_id}/modules"
    response = requests.get(url, headers=HEADERS)
    return response.json()

def get_module_items(course_id, module_id):
    url = f"{API_URL}/courses/{course_id}/modules/{module_id}/items"
    response = requests.get(url, headers=HEADERS)
    return response.json()


# get_Items doens't work yet
def get_Item(course_id, module_id, item_id):
    url = f"{API_URL}/courses/{course_id}/modules/{module_id}/items/{item_id}"
    response = requests.get(url, headers=HEADERS)
    return response.json()


# courses = get_all_courses()
# print(courses)


# for i in courses:
# print(i["id"])
# print(get_announcement(courses[i]["id"]))
# print each course id
# 13920230

# print(get_module_items(192515, 2155269))

# print(get_Item(192515, 2155269, 13920249))
