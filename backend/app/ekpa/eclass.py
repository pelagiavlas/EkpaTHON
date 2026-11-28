"""EclassProvider: placeholder for the connection with Open eClass at ΕΚΠΑ.

What is needed before this can work (to be confirmed with ΕΚΠΑ and the Open eClass documentation):
  1. An API token issued by the university for this application (Open eClass 4 web services).
     It goes in backend/.env (e.g. ECLASS_TOKEN=...), never in code, never in the frontend.
  2. The student signs in with the institutional account on the university's own login page
     (single sign-on). The app receives only a token for that student.
     The app NEVER asks for and NEVER stores the student's ΕΚΠΑ password.
  3. Only what this interface needs: courses, timetable, course documents, syllabus.

We have not verified the exact Open eClass endpoints, so none are written here on purpose.
Fill in each method following the same shapes as MockEkpaProvider (app/ekpa/provider.py).
Until then, choosing this provider raises a clear error instead of calling anything.

Set EKPA_PROVIDER=eclass to use it.
"""

from datetime import date

from app.ekpa.provider import EkpaCourse, EkpaDocument, EkpaProvider, EkpaSlot, EkpaUnit

NOT_READY = "Η σύνδεση με το eClass δεν έχει γίνει ακόμα. Βάλε EKPA_PROVIDER=mock."


class EclassProvider(EkpaProvider):
    def courses(self) -> list[EkpaCourse]:
        raise NotImplementedError(NOT_READY)

    def timetable(self) -> list[EkpaSlot]:
        raise NotImplementedError(NOT_READY)

    def documents(self, course_id: str) -> list[EkpaDocument]:
        raise NotImplementedError(NOT_READY)

    def syllabus(self, course_id: str) -> list[EkpaUnit]:
        raise NotImplementedError(NOT_READY)

    def semester_start(self) -> date:
        raise NotImplementedError(NOT_READY)
