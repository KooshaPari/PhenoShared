import datetime
from openai import OpenAI  # Correctly import the OpenAI library
from ratelimit import limits, sleep_and_retry
import requests
import json

with open("config.json") as f:
    secrets = json.load(f)


ONE_SECOND = 1
MAX_CALLS_PER_SECOND = 1
todays_date = datetime.date.today().isoformat()

# Set up your OpenAI API key
client = OpenAI(api_key=secrets["openai"]["api_key"])
# test


@sleep_and_retry
@limits(calls=MAX_CALLS_PER_SECOND, period=ONE_SECOND)
# @backoff.on_exception(backoff.expo, Exception, max_tries=8)
def scan_announcement(item):
    print("Trying Request...")
    prompt = (
        f"Check the following announcements for mentions of tasks, deadlines, "
        f"assignments, or anything similar with a date attached. Categorize it as a task, "
        f"event, assignment, deadline, or other, and return as: '#(Order Number in descending "
        f"order(first is 1, 2nd is 2) ) DUE_DATE (Day of the week, Month Day) - (DAYS_LEFT Days Left (DUE_DATE - {todays_date}))  (Category): concise "
        f"sentence of what it is'. Return as only a bullet list of such items sorted and grouped by due date first then sub-grouped by course, with headers/subheaders "
        f"denoting said groupings (dates first then courses as subheadings); if you find nothing, have no output. "
        f"Text: {item} "
    )

    # Updated method to create a completion using the new API
    response = client.chat.completions.create(
        # Print the response
        messages=[
            {
                "role": "function",
                "name": "school-planner",
                "content": prompt,
            }
        ],
        model="gpt-4o-mini",  # Updated to use the new chat-based model
        max_tokens=250,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
