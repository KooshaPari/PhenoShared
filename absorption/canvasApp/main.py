import requests
from gpttools import *
from canvas import *
from gcalendar import *

import re



def main():
    # Step 1: Get the list of courses
    try:
        courses = get_courses()
        announcements = get_announcements()
        announcements2 = []
        print("\nAnnouncements:")

       
        for announcement in announcements:
            announcement['title'] = announcement['title']
            announcement['message'] = announcement['message']
            temp = announcement['title'] + " " + announcement['message']
            announcements2.append(temp)
            # print(f"Announcement: {announcement['title']}, Message: {announcement['message']}")
        print(scan_announcement(announcements2))
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
