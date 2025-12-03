from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


TIME_MASK = "%I.%M %p"   # e.g., "10.00 AM"; "09.00 PM"
DATE_MASK = "%m/%d/%Y"


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class Reminder:
    medicine_name: str
    dosage: str
    when: datetime
    option: Optional[str] = None  # stored for UI/teammate; not validated here


class ReminderService:
    def __init__(self) -> None:
        self._reminders: List[Reminder] = []

    def _parse_when(self, date_str: str, time_str: str) -> datetime:
        try:
            d = datetime.strptime(date_str, DATE_MASK).date()
        except ValueError:
            raise ValidationError("Date must be MM/DD/YYYY")
        try:
            t = datetime.strptime(time_str, TIME_MASK).time()
        except ValueError:
            raise ValidationError("Time must match x.xx AM/PM (e.g., 10.00 AM, 09.00 PM)")
        return datetime.combine(d, t)

    def add_reminder(
        self,
        *,
        medicine_name: str,
        dosage: str,
        date_str: str,
        time_str: str,
        option: str | None = None
    ) -> Reminder:
        # Only the required-fields rule for TC02
        if not medicine_name or not dosage or not time_str:
            raise ValidationError("Required: medicine name, dosage, time")
        when = self._parse_when(date_str, time_str)

        # Save (no duplicate logic here)
        r = Reminder(
            medicine_name=medicine_name.strip(),
            dosage=dosage.strip(),
            when=when,
            option=option
        )
        self._reminders.append(r)
        return r

    def delete_reminder(self, index: int) -> bool:
        if 0 <= index < len(self._reminders):
            del self._reminders[index]
            return True
        return False

    def list_reminders(self) -> List[Reminder]:
        return list(self._reminders)

