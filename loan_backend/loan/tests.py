from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from loan_backend.config import LoanStatus, InstallmentStatus
from loan import errors
from loan.models import Loan, LoanShare, Installment, LoanRepayment

class LoanTestCase(TestCase):
    def setUp(self):
        # create a concrete instance of Loan
        data = {
            'amount': 1000,
            'tenure': 4,
            'interest': 0,
            'processing_fee': 0,
        }
        self.user = User.objects.create_user(username='dummy1', password='testpass')
        self.loan = Loan.create_loan(data, self.user)

    # Test create loan
    def test_create_loan(self):
        emis = self.loan.emi_schedule()
        self.assertEqual(len(emis), 1)
        user_emis = emis[0]['emis']
        self.assertEqual(len(user_emis), self.loan.tenure)
        for emi in user_emis:
            self.assertEqual(emi['suggested_emi'], self.loan.amount / self.loan.tenure)

    # Test case when approved loan is approved again
    def test_approve_loan_failure(self):
        self.loan.status = LoanStatus.APPROVED.name
        self.loan.save()
        with self.assertRaises(errors.InvalidLoanApproval):
            self.loan.approve_loan(date.today())

    # Test case when loan with weekly repayment schedule approved successfully
    def test_approve_loan_success(self):
        approval_date = date.today()
        self.loan.approve_loan(approval_date)
        installments = Installment.objects.filter(loanshare__loan=self.loan)
        self.assertEqual(self.loan.status, LoanStatus.APPROVED.name)
        self.assertEqual(len(installments), 4)
        for i, installment in enumerate(installments):
            self.assertEqual(installment.due_date, self.loan.effective_due_date(approval_date, i))
            self.assertEqual(installment.status, InstallmentStatus.UNPAID.name)
            self.assertEqual(installment.amount_remaining, installment.suggested_emi)
            
    # Test case when payment is made.
    def test_add_payment(self):
        approval_date = date.today()
        self.loan.approve_loan(approval_date)
        loanshare = LoanShare.objects.get(loan=self.loan, user=self.user)
        first_installment_due_date = Installment.objects.get(loanshare=loanshare, order=1).due_date
        amount_paid = 400.00001
        loanshare.add_payment(amount_paid, 'PAYMENT1', first_installment_due_date)
        installments = Installment.objects.filter(loanshare=loanshare).order_by('order')
        self.assertEqual(installments[0].status, InstallmentStatus.PAID.name)
        self.assertEqual(installments[0].amount_remaining, 0)
        self.assertEqual(installments[1].status, InstallmentStatus.PARTIALLY_PAID.name)
        self.assertEqual(installments[1].amount_remaining, installments[0].suggested_emi + installments[1].suggested_emi - Decimal(str(round(amount_paid, 5))))
        for i in range(2, self.loan.tenure):
            self.assertEqual(installments[i].status, InstallmentStatus.UNPAID.name)
            self.assertEqual(installments[i].amount_remaining, installments[i].suggested_emi)

        self.assertEqual(self.loan.status, LoanStatus.APPROVED.name)

    # Test case when loan is completed.
    def test_complete_loan(self):
        approval_date = date.today()
        self.loan.approve_loan(approval_date)
        loanshare = LoanShare.objects.get(loan=self.loan, user=self.user)
        first_installment_due_date = Installment.objects.get(loanshare=loanshare, order=1).due_date
        first_amount_paid = 400
        second_amount_paid = 700
        loanshare.add_payment(first_amount_paid, 'PAYMENT2.0', first_installment_due_date)
        loanshare.add_payment(second_amount_paid, 'PAYMENT2.1', first_installment_due_date)
        installments = Installment.objects.filter(loanshare=loanshare).order_by('order')
        for i in range(self.loan.tenure):
            self.assertEqual(installments[i].status, InstallmentStatus.PAID.name)
            
            if i == self.loan.tenure - 1:
                # negative value represent extra amount paid
                self.assertEqual(installments[i].amount_remaining, -100)
            else:
                self.assertEqual(installments[i].amount_remaining, 0)

        loan = Loan.objects.get(pk=self.loan.pk)
        self.assertEqual(loan.status, LoanStatus.COMPLETED.name)
