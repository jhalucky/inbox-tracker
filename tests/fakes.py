from app.providers.base import Classification, EmailInput


class FakeProvider:
    def __init__(self, results: dict[str, Classification] | None = None) -> None:
        self.results = results or {}
        self.calls: list[EmailInput] = []

    def classify(self, email: EmailInput) -> Classification:
        self.calls.append(email)
        if email.subject in self.results:
            return self.results[email.subject]
        needs = "?" in email.body or "please" in email.body.lower()
        return Classification(
            needs_reply=needs,
            urgency=4 if needs else 1,
            category="lead" if needs else "other",
            deadline=None,
            reason="fake classification",
            summary=email.subject[:200],
            prompt_tokens=10,
            completion_tokens=5,
        )
