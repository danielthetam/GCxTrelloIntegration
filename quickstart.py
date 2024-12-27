import os
import os.path
from datetime import datetime as dt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from trello import TrelloClient
from dotenv import load_dotenv

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.coursework.me']

load_dotenv()

client = TrelloClient(
    api_key = os.getenv("API_KEY"),
    api_secret = os.getenv("API_SECRET"),
    token = os.getenv("TOKEN"),
)

def get_api():
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("classroom", "v1", credentials=creds)

    return service


  except HttpError as error:
    print(f"An error occurred: {error}")

def get_course(identifier, service) -> dict:
    results = service.courses().list().execute()
    courses = results.get("courses", [])

    for course in courses:
      if course['name'] == identifier or course['id'] == identifier:
        return course
    return


def get_assignments(course_id, service) -> list:
    assignments = service.courses().courseWork().list(courseId=course_id).execute()
    return assignments['courseWork']


def add_to_trello(board_name, list_name, title, description, due_date):
    boards = client.list_boards()
    board = None
    for i in boards:
        if i.name == board_name:
            board = i
    lists = board.all_lists()

    duty_list = None  # the list we should be storing the assignment cards in
    for l in lists:
        if l.name == list_name:
            duty_list = l

    # Checking if the card is already present in the list
    list_of_cards = duty_list.list_cards()
    list_of_card_names = []
    for card in list_of_cards:
        list_of_card_names.append(str(card.name))

    if title in list_of_card_names:
        print("Card " + "\"" + title + "\" already exists.")
    
    # If it's not already present, add a new card
    elif title not in list_of_card_names:
        new_card = duty_list.add_card(title, description, None, None, None, 1, None, None)
        new_card.set_due(due_date)

      

# Returns a list of assignments as a list of lists. 
# Each list in the outer list stores details about the assignment (title, description, its due date as a datetime object)
def process_assignments(course_id, service) -> list:
    assignments = get_assignments(course_id, service)
    processed_assignments = []
    for assignment in assignments:
        try:
            dd = assignment['dueDate']
            due_time = assignment['dueTime']
            year = dd['year']
            month = dd['month']
            day = dd['day']
            if month < 10:
                month = "0" + str(month)
            elif day < 10:
                day = "0" + str(day)
            elif day < 10 and month < 10:
                day = "0" + str(day)
                month = "0" + str(month)
            else:
                pass
            dueDate = f"{year}{month}{day}"
            dueDate = dt(year=int(dueDate[0:4]), month=int(dueDate[4:6]), day=int(dueDate[6:8]), hour=due_time['hours'], minute=due_time['minutes'])
            currentDate = dt.now()
            if dueDate >= currentDate:
                processed_assignments.append([assignment['title'], assignment['description'], dueDate])
        except KeyError as e:
            if dueDate >= currentDate:
                processed_assignments.append([assignment['title'], "", dueDate])

    return processed_assignments

if __name__ == "__main__":
    api = get_api()
    course_identifier = input("Course Name or ID: ")
    board = input("Board Name: ")
    list_name = input("List Name: ")

    course = get_course(course_identifier, api)
    assignments = process_assignments(course['id'], api)

    for assignment in assignments:
        add_to_trello(board, list_name, assignment[0], assignment[1], assignment[2])
    print("Operation Completed")