"""The practice text and question of the start guide.

Written by hand for the guide, not taken from any course. Nothing about a practice
answer is stored: it never reaches fading, knowledge tracing or progress.
"""

from app.content.schema import Block, GlossaryEntry
from app.learning import answers

TITLE = "Τι είναι η περίληψη"

BLOCKS = [
    Block(type="text", text="Μια [[περίληψη]] λέει τα πιο σημαντικά ενός κειμένου με λίγα λόγια."),
    Block(type="text", text="Δεν λέει όλες τις λεπτομέρειες. Κρατάει μόνο τα βασικά."),
    Block(type="example", title="Παράδειγμα",
          text="Διαβάζεις 2 σελίδες για τα δέντρα. Η περίληψη μπορεί να είναι 3 προτάσεις."),
    Block(type="key", text="Περίληψη: λίγα λόγια για τα πιο σημαντικά."),
]

GLOSSARY = [GlossaryEntry(term="περίληψη", gloss="Ένα μικρό κείμενο με τα πιο σημαντικά ενός μεγαλύτερου κειμένου.")]

PROMPT = "Τι κρατάει μια περίληψη;"
RIGHT = "Μόνο τα πιο σημαντικά"
OPTIONS = ["Όλες τις λεπτομέρειες", RIGHT, "Μόνο τον τίτλο"]  # fixed order: the right one is not first

# Each hint helps a little more, but none says the answer.
HINTS = [
    "Ξαναδιάβασε την πρώτη πρόταση του κειμένου.",
    "Μια περίληψη είναι μικρή. Χωράνε όλες οι λεπτομέρειες σε λίγα λόγια;",
    "Κοίτα το πλαίσιο με το βασικό σημείο, στο τέλος του κειμένου.",
    "Το κείμενο λέει: «Κρατάει μόνο τα βασικά». Ποια επιλογή λέει το ίδιο;",
]


def check(option: str) -> tuple[bool, str]:
    correct = option.strip() == RIGHT
    return correct, answers.CORRECT if correct else answers.TRY_AGAIN
