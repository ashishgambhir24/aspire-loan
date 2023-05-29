from enum import Enum

class Periodicity(Enum):
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'

class LoanStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    WRITTEN_OFF = 'loan written-off'
    SETTLED = 'loan settled'
    HOLD = 'hold'

CLOSED_LOAN_STATUS = [
    LoanStatus.COMPLETED.name,
    LoanStatus.WRITTEN_OFF.name,
    LoanStatus.SETTLED.name
]

class InstallmentStatus(Enum):
    UNPAID = 'unpaid'
    PARTIALLY_PAID = 'partially paid'
    PAID_WITHOUT_PENALTY = 'paid without penalty'
    PAID = 'paid'