"""Checking answers without an LLM.

Choice questions: options[0] is the right one.
Open questions: the answer is right when every stem of one `accept` group
appears at the start of a word (accents and capitals ignored). Otherwise the
student compares their answer with the key point and decides themselves.
"""

import re

from app.content.rules import strip_accents
from app.content.schema import QuestionContent

CORRECT = "Σωστά. Το βρήκες."
TRY_AGAIN = "Όχι ακόμα. Ζήτησε υπόδειξη ή δοκίμασε ξανά."
SELF_CHECK = "Αυτό είναι το βασικό σημείο. Είναι κοντά σε αυτό που έγραψες;"
SELF_CHECK_YES = "Ωραία. Το βρήκες."
SELF_CHECK_NO = "Εντάξει. Τώρα το ξέρεις για την επόμενη φορά."
EXPLAINED = "Δες την εξήγηση."
KEYPOINTS_YES = "Ωραία. Τα βασικά σημεία τα είχες."
KEYPOINTS_NO = "Εντάξει. Τώρα τα έχεις όλα μπροστά σου."
WAITING_SELF_CHECK = "Πρώτα πες μας αν είναι κοντά σε αυτό που έγραψες."


def matches_open_answer(question: QuestionContent, answer: str) -> bool:
    text = strip_accents(answer)
    return any(
        group and all(re.search(rf"(?<!\w){re.escape(strip_accents(stem))}", text) for stem in group)
        for group in question.accept
    )
