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

class InstallmentStatus(Enum):
    UNPAID = 'unpaid'
    PARTIALLY_PAID = 'partially paid'
    PAID = 'paid'