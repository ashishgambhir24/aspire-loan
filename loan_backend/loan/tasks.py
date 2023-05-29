from loan_backend.config import InstallmentStatus, LoanStatus
from loan.models import Installment

def update_penalty():
    installments = Installment.objects.filter(
        loanshare__status=LoanStatus.APPROVED.name
    ).exclude(
        status=InstallmentStatus.PAID.name
    ).exclude(
        status=InstallmentStatus.PAID_WITHOUT_PENALTY.name
    )
    for i in installments:
        i.update_penalty()
