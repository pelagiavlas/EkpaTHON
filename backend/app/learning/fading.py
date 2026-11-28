"""Support levels and fading rules, per SECTION (never a label for the person).

Four support levels. They change only the learning support, never the
accessibility settings (font, spacing, contrast, voice, motion):
  1 Πλήρης βοήθεια     - Easy-to-Read in small parts, a picture and an example for every idea,
                         terms explained in the text, questions with 2 choices
  2 Καθοδηγούμενη      - Easy-to-Read in bigger parts, pictures only for hard ideas,
                         a term is explained when tapped, questions with 3 choices
  3 Ψάχνω στο κείμενο  - the original first (Easy-to-Read one tap away), glossary on request,
                         open questions, hints that point into the original text
  4 Αυτονομία          - the original without additions; the student writes the key points
                         or an own question; help only on request

The rules only PROPOSE a change. The student decides.
"""

from dataclasses import dataclass

from app.config import FadingConfig

MIN_LEVEL = 1
MAX_LEVEL = 4
SEARCH_FROM_LEVEL = 3  # from this level on, hints send the student into the original text
LEVEL_NAMES = {
    1: "Με πολλή υποστήριξη",
    2: "Με λιγότερη υποστήριξη",
    3: "Από το πρωτότυπο",
    4: "Αυτόνομα",
}


@dataclass
class Outcome:
    hints_used: int  # hints that explain (levels 1-2, or after falling back)
    correct: bool
    wrong_tries: int = 0
    search: bool = False  # answered at level 3-4
    fell_back: bool = False  # needed the explaining hints after searching


def is_success(o: Outcome, cfg: FadingConfig) -> bool:
    if not o.correct or o.wrong_tries:
        return False
    if o.search:
        return not o.fell_back
    return o.hints_used <= cfg.success_max_hints


def is_struggle(o: Outcome, cfg: FadingConfig) -> bool:
    if not o.correct or o.wrong_tries:
        return True
    if o.search:
        return o.fell_back
    return o.hints_used >= cfg.struggle_min_hints


def propose(level: int, outcomes: list[Outcome], cfg: FadingConfig) -> str | None:
    """'up' (less help), 'down' (more help) or None. `outcomes` oldest first,
    only those of this section since the last level decision."""
    recent = outcomes[-cfg.up_after_successes:]
    if level < MAX_LEVEL and len(recent) == cfg.up_after_successes and all(is_success(o, cfg) for o in recent):
        return "up"
    window = outcomes[-cfg.down_window:]
    if level > MIN_LEVEL and len(window) == cfg.down_window:
        if sum(is_struggle(o, cfg) for o in window) >= cfg.down_struggles:
            return "down"
    return None


def easy_text_proposal(level: int, visits_used_easy: list[bool], cfg: FadingConfig) -> bool:
    """Levels 3-4: the Easy-to-Read text was opened in most recent visits -> offer one level back."""
    if level < SEARCH_FROM_LEVEL:
        return False
    recent = visits_used_easy[-cfg.easy_window:]
    return len(recent) == cfg.easy_window and sum(recent) >= cfg.easy_down


PROPOSAL_MESSAGES = {
    "fading_up": "Σε αυτή την ενότητα τα καταφέρνεις όλο και πιο πολύ χωρίς βοήθεια. Θες να δοκιμάσεις με λιγότερη υποστήριξη;",
    "fading_down": "Αυτή η ενότητα θέλει τώρα λίγο περισσότερη βοήθεια. Θες περισσότερη υποστήριξη;",
    "easy_use": "Φαίνεται ότι σε βοηθά το Εύκολο κείμενο. Θες να το βλέπεις από την αρχή;",
    "known_up": "Τις έννοιες αυτής της ενότητας φαίνεται ότι τις ξέρεις. Θες να δοκιμάσεις με λιγότερη υποστήριξη;",
    "concept_down": "Μια έννοια αυτής της ενότητας θέλει λίγη ακόμα δουλειά. Θες περισσότερη υποστήριξη;",
    "known_start": "Ξέρεις ήδη τις έννοιες αυτής της ενότητας από προηγούμενα κεφάλαια. Θες να ξεκινήσεις με λιγότερη υποστήριξη;",
}
