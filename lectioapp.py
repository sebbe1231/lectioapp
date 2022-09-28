from lectio import Lectio, exceptions
from lectio import UserType
from datetime import datetime, timedelta
import click
import cooltables

lect = Lectio("inst_id")
try:
    lect.authenticate("username", "password", save_creds=True)
    print("Authenticated!")
except exceptions.IncorrectCredentialsError:
    print("Not authenticated!")
    exit(1)


@click.group()
def lectioapp():
    pass

def user_table(user_item) -> None:
    """Generates a user table based on user list"""
    print(cooltables.create_table([
        ["Navn", "Klasse", "Initialer", "Skole", "Type", "Lectio ID"],
        *[[str(i.name), str(i.class_name), str(i.initials), lect.school().name, i.type.get_str(), str(i.id)] for i in user_item]
    ], theme=cooltables.ROUNDED_THEME))

def schedule_table(sched_item) -> None:
    """Generates a schedule table based on schedule list"""
    
    # Status codes
    status = ["Unchanged", "Changed", "cancelled"]

    print(cooltables.create_table([
        ["Fag", "Lokale", "Lærer", "Start", "Slut", "Status"],
        *[[str(i.subject), str(i.room)[:5], str(i.teacher), str(i.start_time), str(i.end_time), status[int(i.status)]] for i in sched_item]
    ], theme=cooltables.ROUNDED_THEME))

@lectioapp.command()
def now():
    """Get the current ongoing class"""
    print(f"Current time: {str(datetime.now())[:-7]} \n")
    try:
        x = lect.me().get_schedule(start_date=datetime.now(),
                                   end_date=datetime.now()+timedelta(seconds=1), strip_time=False)
    except AttributeError:
        print("No ongoing modules. Use \"lectioapp next\" to see the next module")
        exit(1)

    schedule_table(x)

@lectioapp.command()
@click.argument('date', required=False)
def day(date):
    """Get all the modules of a day, if no date is given the date will be set to today
    \b

    Costume date in format {year}-{month}-{day}
    """

    # Set datetime date
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except:
            print("Not valid time/date")
            exit(1)
    else:
        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if there are any classes for that day
    try:
        x = lect.me().get_schedule(start_date=date, end_date=date +
                                   timedelta(days=1), strip_time=False)
    except AttributeError:
        print(f"No modules on the date {str(date)[:-8]}")
        exit(1)

    schedule_table(x)

@lectioapp.command()
def next():
    """Get the next class in line"""
    
    # h is hours to add to date
    h = 1
    while True:
        # If the last class in the list has already been started, the loop will repeat, adding an extra hour  
        x = lect.me().get_schedule(start_date=datetime.now(),
                                   end_date=datetime.now()+timedelta(hours=h), strip_time=False)
        if x[-1].start_time <= datetime.now():
            h += 1
        else:
            break

    status = ["Unchanged", "Changed", "Cancelled"]

    print(cooltables.create_table([
        ["Fag", "Lokale", "Lærer", "Start", "Slut", "Status"],
        [str(x[-1].subject), str(x[-1].room)[:5], str(x[-1].teacher),
         str(x[-1].start_time), str(x[-1].end_time), status[int(x[-1].status)]]
    ], theme=cooltables.ROUNDED_THEME))


@lectioapp.command()
@click.argument("user_id", required=False)
@click.option("-n", "--now", help="Get the current class for the student", is_flag=True)
@click.option("-d", "--day", help="Get the schedual of the student, for the day", is_flag=True)
@click.option("-w", "--week", help="Get the schedual of the student, for the week", is_flag=True)
def user(user_id: str, now: bool, day: bool, week: bool):
    """Search for users with ID, if no user id entered, your own profile will be displayed"""
    
    # defining the user (u)
    u = lect.me()
    if user_id:
        # If an id is given, check look for related student or teacher id
        try:
            u = lect.school().get_user_by_id(user_id, UserType.STUDENT)
        except exceptions.UserDoesNotExistError:
            try:
                u = lect.school().get_user_by_id(user_id, UserType.TEACHER)
            except exceptions.UserDoesNotExistError:
                print("No user with such id!")
                exit(1)

    user_table(u)
    print(f"Lectio billede:\n{u.image}\n")

    # Set start and end date for if student or teachers schedule is asked for
    if now:
        start = datetime.now()
        end = datetime.now()+timedelta(seconds=1)
    elif day:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start+timedelta(days=1)
    elif week:
        start = datetime.now() - timedelta(days=datetime.now().weekday())
        end = start + timedelta(days=6)

    x = u.get_schedule(start_date=start, end_date=end, strip_time=False)

    schedule_table(x)

@lectioapp.command()
@click.argument('term')
@click.option("-s", "--student", help="Only search for students", is_flag=True)
@click.option("-t", "--teacher", help="Only search for teachers", is_flag=True)
def search(term, student: bool, teacher: bool):
    """Search for students for teachers"""
    users = []

    if student and not teacher:
        users = lect.school().search_for_students(query=term)
    elif teacher and not student:
        users = lect.school().search_for_teachers(query=term)
    else:
        users = lect.school().search_for_users(term)
    
    user_table(users)


if __name__ == '__main__':
    lectioapp()
