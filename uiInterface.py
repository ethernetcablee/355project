from medicine_core import ReminderService, ValidationError
import NoAPP

service = ReminderService()

# Fill these in for your account
NoAPP.SENDER_EMAIL = ""
NoAPP.APP_PASSWORD = ""  # your app password (no spaces)
NoAPP.RECIPIENT_EMAIL = ""
NoAPP.NAME_USER = ""

# Start scheduler + Flask once
NoAPP.start_scheduler_background()
NoAPP.start_flask_background()


# SCHEDULE REMINDER INTO NoAPP
def schedule_in_NoAPP(reminder):
    weekday_str = reminder.when.strftime("%A").lower()
    time_24 = reminder.when.strftime("%H:%M")

    NoAPP.schedule_reminder(
        reminder.medicine_name,
        weekday_str,
        time_24,
        NoAPP.NAME_USER
    )


# ADD REMINDER
def add_new_reminder():
    print("\n--- Add New Reminder ---")
    med = input("Medicine name: ").strip()
    dosage = input("Dosage: ").strip()
    date_str = input("Date (MM/DD/YYYY): ").strip()
    time_str = input("Time (HH.MM AM/PM): ").strip()

    try:
        reminder = service.add_reminder(
            medicine_name=med,
            dosage=dosage,
            date_str=date_str,
            time_str=time_str
        )
    except ValidationError as e:
        print(f"Error: {e}")
        return

    print("Reminder added successfully.")
    schedule_in_NoAPP(reminder)


# SHOW REMINDERS
def show_reminders():
    print("\n--- Current Reminders ---")
    reminders = service.list_reminders()
    if not reminders:
        print("No reminders saved.")
        return

    visible = []

    for r in reminders:
        weekday_str = r.when.strftime("%A").lower()
        time_24 = r.when.strftime("%H:%M")

        # Check if this reminder is already marked as taken
        taken = False
        for entry in NoAPP.taken_history:
            if (
                entry["medicine"] == r.medicine_name
                and entry["day"] == weekday_str
                and entry["time"] == time_24
            ):
                taken = True
                break

        if not taken:
            visible.append(r)

    if not visible:
        print("No upcoming reminders (all taken).")
        return

    for i, r in enumerate(visible):
        print(f"{i+1}. {r.medicine_name} - {r.dosage} - {r.when}")


# DELETE REMINDER
def delete_reminder():
    reminders = service.list_reminders()

    if not reminders:
        print("No reminders to delete.")
        return

    print("\n--- Delete Reminder ---")
    for i, r in enumerate(reminders):
        print(f"{i+1}. {r.medicine_name} - {r.dosage} - {r.when}")

    try:
        choice = int(input("Enter reminder number to delete: "))
        index = choice - 1
    except ValueError:
        print("Invalid input.")
        return

    if index < 0 or index >= len(reminders):
        print("Invalid selection.")
        return

    # Get reminder info BEFORE deletion
    r = reminders[index]
    weekday_str = r.when.strftime("%A").lower()
    time_24 = r.when.strftime("%H:%M")

    # Remove from core storage
    service.delete_reminder(index)
    print("Reminder deleted from saved list.")

    # Cancel NoAPP’s scheduled jobs
    NoAPP.cancel_reminder(r.medicine_name, weekday_str, time_24)


# MODIFY REMINDER
def modify_reminder():
    reminders = service.list_reminders()
    if not reminders:
        print("No reminders to modify.")
        return

    print("\n--- Modify Reminder ---")
    for i, r in enumerate(reminders):
        print(f"{i+1}. {r.medicine_name} - {r.dosage} - {r.when}")

    try:
        choice = int(input("Enter the number of the reminder to modify: "))
        index = choice - 1
    except ValueError:
        print("Invalid input.")
        return

    if index < 0 or index >= len(reminders):
        print("Invalid selection.")
        return

    old = reminders[index]
    old_day = old.when.strftime("%A").lower()
    old_time = old.when.strftime("%H:%M")

    # cancel old schedule
    NoAPP.cancel_reminder(old.medicine_name, old_day, old_time)

    # delete from core
    service.delete_reminder(index)
    print("Old reminder removed. Please enter new values.\n")

    # ask user for new values
    med = input("New medicine name: ").strip()
    dosage = input("New dosage: ").strip()
    date_str = input("New date (MM/DD/YYYY): ").strip()
    time_str = input("New time (HH.MM AM/PM): ").strip()

    try:
        new_reminder = service.add_reminder(
            medicine_name=med,
            dosage=dosage,
            date_str=date_str,
            time_str=time_str
        )
    except ValidationError as e:
        print(f"Error: {e}")
        return

    # schedule new reminder
    schedule_in_NoAPP(new_reminder)

    print("Reminder successfully modified.")


# VIEW TAKEN HISTORY
def view_taken_history():
    print("\n--- Taken History ---")
    if not NoAPP.taken_history:
        print("No doses have been marked as taken yet.")
        return

    for entry in NoAPP.taken_history:
        print(
            f"{entry['taken_at']}: {entry['medicine']} "
            f"({entry['day']} at {entry['time']})"
        )


# MENU LOOP
def menu():
    while True:
        print(
            "\n(1) Add new reminder"
            "\n(2) Delete reminder"
            "\n(3) Modify reminder"
            "\n(4) Show reminders"
            "\n(5) View taken history"
            "\n(6) Exit"
        )
        x = input("Choose: ").strip()

        match x:
            case "1":
                add_new_reminder()
            case "2":
                delete_reminder()
            case "3":
                modify_reminder()
            case "4":
                show_reminders()
            case "5":
                view_taken_history()
            case "6":
                print("Goodbye.")
                break
            case _:
                print("Invalid option.")


if __name__ == "__main__":
    menu()
