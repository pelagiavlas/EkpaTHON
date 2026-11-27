"""LLMProvider: placeholder with the same interface as MockProvider.

To connect an LLM later:
  1. Set CONTENT_PROVIDER=llm and ANTHROPIC_API_KEY in backend/.env (never in code, never in the frontend).
  2. Fill in the three methods below. In each one:
     - send ONLY the course text of the section (SectionInput) and general parameters
       (support level, "Easy-to-Read"). Never a name, a setting about the person or a diagnosis;
     - ask for JSON in the shape of the Pydantic models in app/content/schema.py;
     - validate the reply with those models (e.g. EasyRead.model_validate_json(reply));
       if it is invalid, retry ONCE, then raise an error;
     - for simplify(): check that every formula of the original is still in the reply,
       unchanged (see app/pdf/sections.is_verbatim).
  3. Keep the prompts in this file, next to the calls, so the team can review them.

Until then, choosing this provider raises a clear error instead of calling anything.
"""

from app.content.provider import ContentProvider, SectionInput
from app.content.schema import EasyRead, Hint, QuestionContent

NOT_READY = "Η σύνδεση με LLM δεν έχει γίνει ακόμα. Βάλε CONTENT_PROVIDER=mock."


class LLMProvider(ContentProvider):
    def simplify(self, section: SectionInput) -> EasyRead:
        # Here: call the LLM API with the section text and the Easy-to-Read rules
        # (max 10-12 words per sentence, one idea per paragraph, keep every academic
        # term with a simple gloss, keep formulas exactly, add one everyday example).
        raise NotImplementedError(NOT_READY)

    def make_questions(self, section: SectionInput, level: int) -> list[QuestionContent]:
        # Here: ask for comprehension questions; options[0] must be the right answer,
        # 2-3 short options, plus `accept` stems and a `key_point` shown only after trying.
        raise NotImplementedError(NOT_READY)

    def make_hints(self, question: QuestionContent) -> list[Hint]:
        # Here: ask for the 4 hint steps (where to look, guiding question, two choices,
        # the same idea with ANOTHER everyday example - never the answer itself).
        raise NotImplementedError(NOT_READY)
