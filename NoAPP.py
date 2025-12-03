import schedule
import time
import threading
from plyer import notification
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request
from datetime import datetime
import urllib.parse
import uuid

# Set by uiInterface.py
SENDER_EMAIL = ""
APP_PASSWORD = ""
RECIPIENT_EMAIL = ""
NAME_USER = ""

# Store all scheduled jobs so we can cancel them
# Each entry: (id, medicine, day, time, job1, job2)
scheduled_jobs = []

# History of taken reminders
# Each entry: {"id": ..., "medicine": ..., "day": ..., "time": ..., "taken_at": ...}
taken_history = []

# Track which ids have already been used so old links don't work
taken_ids = set()

app = Flask(__name__)


# --------------------------
#    EMAIL NOTIFICATION
# --------------------------
def send_email(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)


# --------------------------
# DESKTOP NOTIFICATION
# --------------------------
def remind(title: str, message: str, timeout: int):
    notification.notify(
        title=title,
        message=message,
        timeout=timeout,
    )


# --------------------------
#   SCHEDULE A REMINDER
# --------------------------
def schedule_reminder(medicine, day, time, user_name):
    """
    day: 'monday', 'tuesday', ...
    time: 'HH:MM' (24-hour)
    """
    # Unique id for this reminder instance
    rid = str(uuid.uuid4())

    # Popup notification job
    job1 = schedule.every().__getattribute__(day).at(time).do(
        remind,
        "Medication Reminder",
        f"Take your {medicine}",
        10
    )

    # Email body includes link to mark as taken by id
    link = f"http://127.0.0.1:5000/taken?med={urllib.parse.quote(medicine)}&day={day}&time={time}"
    body = (
        f"Hi {user_name},\n\n"
        f"It's time to take your {medicine}.\n\n"
        f"After you take it, click this link to mark it as taken:\n"
        f"{link}\n\n"
        f"— Your Reminder App"
    )

    job2 = schedule.every().__getattribute__(day).at(time).do(
        send_email,
        "Medication Reminder",
        body
    )

    scheduled_jobs.append((rid, medicine, day, time, job1, job2))

    print(f"[NoAPP] Scheduled {medicine} on {day} at {time} with id={rid}")
    return rid


# --------------------------
#   CANCEL BY MED/DAY/TIME
#   (used by delete/modify in UI)
# --------------------------
def cancel_reminder(medicine, day, time):
    for entry in list(scheduled_jobs):
        rid, med, d, t, job1, job2 = entry
        if med == medicine and d == day and t == time:
            schedule.cancel_job(job1)
            schedule.cancel_job(job2)
            scheduled_jobs.remove(entry)
            print(f"[NoAPP] CANCELLED reminder: {medicine} on {day} at {time}")
            return True
    print(f"[NoAPP] No matching reminder to cancel ({medicine}, {day}, {time}).")
    return False


# --------------------------
#   CANCEL BY ID
#   (used by /taken link)
# --------------------------
def cancel_reminder_by_id(rid):
    for entry in list(scheduled_jobs):
        stored_id, med, d, t, job1, job2 = entry
        if stored_id == rid:
            schedule.cancel_job(job1)
            schedule.cancel_job(job2)
            scheduled_jobs.remove(entry)
            print(f"[NoAPP] CANCELLED reminder id={rid} ({med}, {d}, {t})")
            return med, d, t
    print(f"[NoAPP] No matching reminder for id={rid}")
    return None


# --------------------------
#   FLASK ROUTE: MARK TAKEN
# --------------------------
@app.route("/taken")
def mark_taken():
    med = request.args.get("med")
    day = request.args.get("day")
    time_str = request.args.get("time")

    # 1. Validate query params
    if not med or not day or not time_str:
        return "Invalid link: missing data.", 400

    # 2. Make sure this exact (med, day, time) wasn't already recorded
    for entry in taken_history:
        if (
            entry["medicine"] == med and
            entry["day"] == day and
            entry["time"] == time_str
        ):
            return "This dose was already marked as taken.", 200

    # 3. Record taken history
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    taken_history.append({
        "medicine": med,
        "day": day,
        "time": time_str,
        "taken_at": ts,
    })

    # 4. Unschedule the notification + email for this reminder
    cancel_reminder(med, day, time_str)

    # 5. Remove matching reminder from the Show Reminders list
    try:
        # Import here to avoid circular import at startup
        from uiInterface import service
    except Exception:
        service = None

    if service:
        all_reminders = service.list_reminders()
        for i, r in enumerate(all_reminders):
            # normalize to match how we scheduled
            check_day = r.when.strftime("%A").lower()
            check_time = r.when.strftime("%H:%M")

            if (
                r.medicine_name == med and
                check_day == day and
                check_time == time_str
            ):
                service.delete_reminder(i)
                break  # stop after deleting first match

    return "Dose marked as taken. You can close this tab.", 200


# --------------------------
#   START SCHEDULER THREAD
# --------------------------
def start_scheduler_background():
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(1)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


# --------------------------
#   START FLASK THREAD
# --------------------------
def start_flask_background():
    def run():
        # debug=False, use_reloader=False so it doesn't spawn extra processes
        app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

    t = threading.Thread(target=run, daemon=True)
    t.start()

