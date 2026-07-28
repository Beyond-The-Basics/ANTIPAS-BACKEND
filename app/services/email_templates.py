"""Email copy, kept out of the business logic that decides *when* to send.

Localized to the recipient's `User.locale`. This is the one place user-facing text is rendered
server-side rather than by the client — an email lands in an inbox with no React app around it to
translate it, so the three locales the product ships (English, French, Darija) have to exist here
too. Falls back to English for anything unmapped.
"""

from app.models.enums import Locale

SUBJECTS: dict[Locale, str] = {
    Locale.EN: "Verify your email",
    Locale.FR: "Vérifiez votre e-mail",
    Locale.AR: "أكد الإيميل ديالك",
}

_BODIES: dict[Locale, str] = {
    Locale.EN: (
        "Hello,\n"
        "\n"
        "Your verification code is:\n"
        "\n"
        "{otp}\n"
        "\n"
        "This code expires in {minutes} minutes.\n"
        "\n"
        "If you didn't request this email, you can safely ignore it.\n"
    ),
    Locale.FR: (
        "Bonjour,\n"
        "\n"
        "Votre code de vérification est :\n"
        "\n"
        "{otp}\n"
        "\n"
        "Ce code expire dans {minutes} minutes.\n"
        "\n"
        "Si vous n'avez pas demandé cet e-mail, vous pouvez l'ignorer.\n"
    ),
    Locale.AR: (
        "السلام،\n"
        "\n"
        "كود التأكيد ديالك هو:\n"
        "\n"
        "{otp}\n"
        "\n"
        "هاد الكود كايسالي من بعد {minutes} دقايق.\n"
        "\n"
        "إلا ماطلبتيش هاد الإيميل، تقدر تتجاهلو.\n"
    ),
}


def build_verification_email(*, otp: str, minutes: int, locale: Locale = Locale.EN) -> tuple[str, str]:
    """Return `(subject, body)` for a verification email in `locale`."""
    subject = SUBJECTS.get(locale, SUBJECTS[Locale.EN])
    body = _BODIES.get(locale, _BODIES[Locale.EN])
    return subject, body.format(otp=otp, minutes=minutes)
