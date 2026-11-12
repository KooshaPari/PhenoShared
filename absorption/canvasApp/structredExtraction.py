from pydantic import BaseModel
from openai import OpenAI
from toDoistAddTask import add_todoist_task
from mainIEE380Orchestrator import get_all_courses, get_module_items, get_Item, getPageText
from typing import List, Optional

# Define data models
class Assignment(BaseModel):
    title: str
    due_date: Optional[str]  # Due date if specified
    description: Optional[str]  # Additional details about the assignment
    resources: List[str]  # Links or references related to the assignment

class DailyTask(BaseModel):
    date: str
    tasks: List[Assignment]

class WeeklyToDo(BaseModel):
    week_range: str
    daily_tasks: List[DailyTask]

# Function to initialize the OpenAI client
def initialize_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)

# Function to parse course tasks and add them to Todoist
def parse_and_add_tasks_to_todoist(
    client: OpenAI, 
    course_id: int, 
    module_id: int, 
    todoist_label: str = "IEE 380"
):
    module_items = get_module_items(course_id, module_id)

    for item in module_items:
        full_text = getPageText(course_id, item["page_url"])
        
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "Extract the event information."},
                {"role": "user", "content": full_text},
            ],
            response_format=WeeklyToDo,
        )
        
        event = completion.choices[0].message.parsed

        for daily_task in event.daily_tasks:
            for task in daily_task.tasks:
                add_todoist_task(
                    content=str(task.title),
                    due_string=str(task.due_date),
                    description=str(task.description),
                    labels=[todoist_label]
                )

# Example usage
def main():
    # Initialize OpenAI client with your API key
    api_key = "sk-REDACTED-ROTATE-KEY"
    client = initialize_openai_client(api_key)
    
    # Add a sample task to Todoist
    add_todoist_task("Hello", "9/1", "He", ["IEE 380"])
    
    # Process course module items and add tasks to Todoist
    parse_and_add_tasks_to_todoist(client, course_id=192515, module_id=2155269)

if __name__ == "__main__":
    main()
