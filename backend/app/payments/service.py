from app.payments.models import PaymentOutcome, PaymentStatus


def simulate_payment(outcome: PaymentOutcome) -> PaymentStatus:
    """Return a deterministic status so success and failure paths are reproducible."""
    return {
        PaymentOutcome.SUCCESS: PaymentStatus.SUCCEEDED,
        PaymentOutcome.FAILURE: PaymentStatus.FAILED,
        PaymentOutcome.TIMEOUT: PaymentStatus.TIMED_OUT,
    }[outcome]
