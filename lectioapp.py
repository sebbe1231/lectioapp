from lectio import Lectio, exceptions
from lectio import UserType, ModuleStatus
from datetime import datetime, timedelta
import click
from beautifultable import BeautifulTable
import os
from re import match

try:
    lect = Lectio(<inst_id>, "<username>", "<password>")
    print("Authenticated!")
except exceptions.IncorrectCredentialsError:
    print("Not authenticated!")
    exit(1)


@click.group()
def lectioapp():
    pass


def room_table(room_item: list) -> BeautifulTable:
    """Generates a room table based on room list"""

    table = BeautifulTable(maxwidth=os.get_terminal_size()[0])
    table.columns.header = ["Lokale", "Navn", "ID"]
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)

    # Only works for my school, due to regex looking for how my school formats classes
    # For it to work for other schools, simply edit the regex
    for room in room_item:
        m = match(r"^(.+?) (\(.+)$", room.name)

        try:
            room_num = m.group(1)
            room_name = m.group(2)
        except AttributeError:
            continue

        table.rows.append([
            room_num,
            room_name,
            str(room.id)
        ])

    return table


def user_table(user_item: list) -> BeautifulTable:
    """Generates a user table based on user list"""
    table = BeautifulTable(maxwidth=os.get_terminal_size()[0])
    table.columns.header = ["Navn", "Klasse", "Initialer", "Type", "Lectio ID"]
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)

    for i in user_item:
        table.rows.append([
            str(i.name),
            str(i.class_name),
            str(i.initials),
            str(i.type.get_str()),
            str(i.id)
        ])

    return table


def schedule_table(sched_item: list) -> BeautifulTable:
    """Generates a schedule table based on schedule list"""

    # Status codes
    status = ["Unchanged", "Changed", "cancelled"]

    table = BeautifulTable(maxwidth=os.get_terminal_size()[0])
    table.columns.header = ["Fag", "Titel", "Lokale",
                            "Lærer", "Start", "Slut", "Længde", "Status"]
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)

    for i in sched_item:
        teacher = i.teacher

        # Look for teacher names with initials, and only show the initials
        # I do this to shorten the table
        if teacher:
            t = match(r".*\((.+)\)$", teacher)
            if t:
                teacher = str(t.group(1))
            else:
                if len(teacher.split(", ")) > 2:
                    teacher = ", ".join(teacher.split(", ")[0:2])+", ..."
        else:
            # If teacher is none
            teacher = "?"

        # Adds a row that displays date of module, as to not do it in start and endtime columns
        if not str(i.start_time.date()) in table.rows and len(sched_item) > 1:
            table.rows.append([
                "---"
            ]*8, header=str(i.start_time.date()))

        table.rows.append([
            (str(i.subject) if len(str(i.subject))
             <= 18 else f"{str(i.subject)[:18]}..."),
            (str(i.title) if len(str(i.title)) <=
             16 else f"{str(i.title)[:16]}..."),
            str(i.room)[:5],
            teacher,
            f"{str(i.start_time)[11:-3]}",
            f"{str(i.end_time)[11:-3]}",
            str(i.end_time-i.start_time),
            i.status
        ])

    return table


@lectioapp.command()
def now():
    """Get the current ongoing class"""
    print(f"Current time: {str(datetime.now())[:-7]} \n")
    x = lect.me().get_schedule(start_date=datetime.now(),
                               end_date=datetime.now()+timedelta(seconds=1), strip_time=False)
    if len(x) == 0:
        print("No ongoing modules. Use \"lectioapp next\" to see the next module")
        exit(1)

    print(schedule_table(x))

    print(f"Total school hours:\n{x[0].end_time-x[0].start_time}")


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
        date = datetime.now()

    # Check if there are any classes for that day
    x = lect.me().get_schedule(start_date=date, end_date=date, strip_time=True)
    if len(x) == 0:
        print(f"No modules on the date {str(date)[:-8]}")
        exit(1)

    print(schedule_table(x))

    print(f"Total school hours:\n{x[-1].end_time-x[0].start_time}")


@lectioapp.command()
def next():
    """Get the next class of the day"""

    now = datetime.now()
    sched = lect.me().get_schedule(now, now+timedelta(days=5), False)

    if len(sched) == 0:
        print("No modules found in your schedule!")
        return

    for i in sched:
        if i.start_time > now:
            print(schedule_table([i]))
            print(f"Total school hours:\n{i.end_time-i.start_time}")
            return
    else:
        print("No future modules found in your schedule, for the next 5 days!")
        return


@lectioapp.command()
@click.argument('date', required=False)
def week(date):
    """Get the all the classes for the whole week that a given date is within. 
    \b
    If no date is specified, the current week will be used
    \b

    Costume date in format {year}-{month}-{day}"""

    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except:
            print("Not valid time/date")
            exit(1)
    else:
        date = datetime.now()

    # Define start and end to make it easier to look at
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    # Same as in user -w
    x = lect.me().get_schedule(start_date=start, end_date=end, strip_time=True)

    # Check if there are actually modules in the list
    if len(x) == 0:
        print(f"No modules on the date {str(date)[:-8]}")
        exit(1)

    print(schedule_table(x))

    # I have to use this way, by adding each module length to eachother
    # Or else the wrong length will be displayed
    i = 0
    for m in x:
        if i == 0:
            i = m.end_time - m.start_time
        else:
            i = i + (m.end_time - m.start_time)
    print(i)


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
            u = lect.get_school().get_user_by_id(user_id)
        except exceptions.UserDoesNotExistError:
            print("No user with such id!")
            exit(1)

    print(user_table([u]))

    print(u.image)

    # Set start and end date for if student or teachers schedule is asked for
    if now:
        start = datetime.now()
        end = datetime.now()+timedelta(seconds=1)
        strip = False
    elif day:
        start = datetime.now()
        end = start
        strip = True
    elif week:
        start = datetime.now() - timedelta(days=datetime.now().weekday())
        end = start + timedelta(days=6)
        strip = True
    else:
        exit(1)

    x = u.get_schedule(start_date=start, end_date=end, strip_time=strip)

    print(schedule_table(x))

    # Incase of the week flag, a forloop will get a better result of total hours than simply doing first and last module
    i = 0
    for m in x:
        if i == 0:
            i = m.end_time - m.start_time
        else:
            i = i + (m.end_time - m.start_time)

    print(f"Total school hours:\n{i}")


@lectioapp.command()
def overview():
    """Get an overview of the current day"""
    sched = lect.me().get_schedule(datetime.now(), datetime.now(), True)

    # The cache is a dictionary of all the classes of the day, plus the amount of times they show up
    cache = {}
    for c in sched:
        count = cache.get(c.subject)
        if not count:
            cache[c.subject] = len(
                list(filter(lambda i: i.subject == c.subject, sched)))
            count = cache.get(c.subject)

    print(schedule_table(sched))
    print(
        f"Time untill school is over:\n{str(sched[-1].end_time-datetime.now())[:-7]}")

    print(f"\nThe distribution of classes for the day:")

    table = BeautifulTable(maxwidth=os.get_terminal_size()[0])
    table.columns.header = ["Fag", "Moduler", "Procent"]
    table.set_style(BeautifulTable.STYLE_BOX_ROUNDED)

    for subject, times in cache.items():
        table.rows.append([
            str(subject),
            str(times),
            f"{times / sum(cache.values()) * 100}%"
        ])
    print(table)


@lectioapp.command()
@click.argument('term')
@click.option("-s", "--student", help="Only search for students", is_flag=True)
@click.option("-t", "--teacher", help="Only search for teachers. Used to search for initials", is_flag=True)
def search(term, student: bool, teacher: bool):
    """Search for students for teachers"""
    users = []

    if student and not teacher:
        users = lect.get_school().search_for_students(query=term)
    elif teacher and not student:
        users = lect.get_school().search_for_teachers(
            query_name=term, query_initials=term)
    else:
        users = lect.get_school().search_for_users(term)

    print(user_table(users))


@lectioapp.command()
@click.argument('room', required = False)
def rooms(room: str):
    """Look at or search for rooms.
    \b
    If room arguement is empty, all rooms will be displayed"""
    if not room:
        print(room_table(lect.get_school().rooms))
    else:
        print(room_table(lect.get_school().search_for_rooms(room)))

@lectioapp.command()
@click.argument('id')
@click.argument('time', required=False)
@click.option("-n", "--now", help="Get current activity in room", is_flag=True)
@click.option("-d", "--day", help="Get all activities in the room for the day", is_flag=True)
@click.option("-w", "--week", help="Get all activities in the room for the day", is_flag=True)
def get_room(id: int, time: str, now: bool, day: bool, week: bool):
    """Get information about a room.
    \b

    Get availability of room based on defined time, if no time is defined, it will show for the current time.
    \b
    Time must be inserted with format [year]-[month]-[day]-[hour]-[minute]
    """

    # Check if time is defined
    if time:
        try:
            # I should add custom formatting
            time = datetime.strptime(time, "%Y-%m-%d-%H-%M")
        except:
            print("Not valid time/date")
            exit(1)
    else:
        time = datetime.now()
    
    try:
        room = lect.get_school().get_room_by_id(id)
        table = room_table([lect.get_school().get_room_by_id(id)])
        table.columns.insert(
            -1, 
            # If room available, add ✓, else add ✘
            [("✓" if room.is_available(time) == 1 else "✘")], 
            header="Is available")
        print(table)

        # If room is not available, show activity during that time
        if table.columns["Is available"] == "✘":
            print(f"Activity in room at {time}")
            print(schedule_table(room.get_schedule(time, time+timedelta(seconds=1), False)), "\n")

    except exceptions.RoomDoesNotExistError:
        print("This room does not exist!")
        exit(1)

    # Check if flag is added
    if now:
        start = time
        end = time+timedelta(seconds=1)
        strip = False
    elif day:
        start = time
        end = time
        strip = True
    elif week:
        start = time - timedelta(days=datetime.now().weekday())
        end = start + timedelta(days=6)
        strip = True
    else:
        exit(1)
    
    # Print schedule for the timeframe defined by the flag
    print(schedule_table(room.get_schedule(start, end, strip)))

if __name__ == '__main__':
    lectioapp()
