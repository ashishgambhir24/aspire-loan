from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.forms.models import model_to_dict
from lib.common import add_months
from lib.validators import validate_nonzero
from loan_backend.config import Periodicity, LoanStatus, InstallmentStatus, CLOSED_LOAN_STATUS
from loan_backend.constants import DEFAULT_PERIODICITY, DEFAULT_INTEREST, DEFAULT_PROCESSING_FEE, DEFAULT_DECIMAL_PLACES
from loan import errors

class Loan(models.Model):
    amount = models.DecimalField(max_digits=20, decimal_places=DEFAULT_DECIMAL_PLACES)
    tenure = models.PositiveIntegerField(
        validators=[MaxValueValidator(60), validate_nonzero]
    )
    periodicity = models.CharField(
        max_length=10,
        choices=[(tag.name, tag.value) for tag in Periodicity]
    )
    status = models.CharField(
        max_length=20,
        choices=[(tag.name, tag.value) for tag in LoanStatus],
    )
    approval_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    interest = models.DecimalField(max_digits=6, decimal_places=DEFAULT_DECIMAL_PLACES, help_text='1 means 100%')
    processing_fee = models.DecimalField(max_digits=6, decimal_places=DEFAULT_DECIMAL_PLACES, help_text='1 means 100%')
    date_created = models.DateField()

    def jsonify(self):
        data = model_to_dict(self, exclude=['interest', 'processing_fee'])
        data['emis'] = self.emi_schedule()
        return data
    
    def is_active(self):
        if self.closing_date is None or self.status not in CLOSED_LOAN_STATUS or self.status != LoanStatus.PENDING.name:
            return True

        return False

    @classmethod
    def create_loan(cls, data, user):
        with transaction.atomic():
            loan = cls(
                amount=Decimal(str(round(data['amount'], DEFAULT_DECIMAL_PLACES))),
                tenure=data['tenure'],
                periodicity=data.get('periodicity', DEFAULT_PERIODICITY),
                status=LoanStatus.PENDING.name,
                interest=Decimal(str(round(data.get('interest', DEFAULT_INTEREST), DEFAULT_DECIMAL_PLACES))),
                processing_fee=Decimal(str(round(data.get('processing_fee', DEFAULT_PROCESSING_FEE), DEFAULT_DECIMAL_PLACES))),
                date_created=data.get('date_created', date.today())
            )
            loan.full_clean()
            loan.save()

            LoanShare.create_loanshare(loan, data, user)

        return loan
    
    def emi_schedule(self):
        loanshares = self.loanshare_set.all()
        emis = []
        for ls in loanshares:
            installments = Installment.objects.filter(loanshare=ls).order_by('order')
            user_emis = {
                'user': ls.user.username,
                'emis': []
            }
            if installments:
                for i in installments:
                    user_emis['emis'].append(i.jsonify())

            else:
                user_emis['emis'] = ls.calculate_emis(date.today())
            
            emis.append(user_emis)

        return emis

    def calculate_periodicity_factor(self):
        if self.periodicity == 'daily':
            periodicity_factor = 365
        elif self.periodicity == 'weekly':
            periodicity_factor = 52
        elif self.periodicity == 'monthly':
            periodicity_factor = 12
        else:
            raise errors.InvalidPeriodicity()

        return periodicity_factor      

    def effective_due_date(self, initial_date, order):
        if self.periodicity == 'daily':
            effective_due_date = initial_date + timedelta(days=order + 1)
        elif self.periodicity == 'weekly':
            effective_due_date = initial_date + timedelta(days=7 * (order + 1))
        elif self.periodicity == 'monthly':
            effective_due_date = add_months(initial_date, order + 1)
        else:
            raise errors.InvalidPeriodicity()

        return effective_due_date

    
    def approve_loan(self, approval_date):
        if self.status != LoanStatus.PENDING.name:
            raise errors.InvalidLoanApproval()

        with transaction.atomic():
            self.status = LoanStatus.APPROVED.name
            self.approval_date = approval_date
            self.full_clean()
            self.save()

            for ls in self.loanshare_set.all():
                ls.status = LoanStatus.APPROVED.name
                ls.full_clean()
                ls.save()
                ls.create_installments(approval_date)

    @property
    def amount_pending(self):
        loanshares = self.loanshare_set.all()
        amount_pending = {}
        for ls in loanshares:
            installments = Installment.objects.filter(loanshare=ls)
            user_amount_pending = sum([i.amount_remaining for i in installments])
            amount_pending[ls.user.username] = user_amount_pending

        return amount_pending
    
    def update_loan_status(self):
        loanshares = LoanShare.objects.filter(loan=self)
        if len(loanshares) == len(loanshares.filter(status=LoanStatus.COMPLETED.name)):
            self.status = LoanStatus.COMPLETED.name
            self.full_clean()
            self.save()

        return

# Loan and LoanShare are different models so as to leverage LoanShare in case of group loans
class LoanShare(models.Model):
    share = models.DecimalField(max_digits=20, decimal_places=DEFAULT_DECIMAL_PLACES)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[(tag.name, tag.value) for tag in LoanStatus],
    )
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)

    @classmethod
    def create_loanshare(cls, loan, data, user):
        loanshare = cls(
            share=Decimal(str(round(data['amount'], DEFAULT_DECIMAL_PLACES))),
            user=user,
            status=LoanStatus.PENDING.name,
            loan=loan
        )
        loanshare.full_clean()
        loanshare.save()
        return
    
    def calculate_emis(self, start_date):
        total_amount = round(
            self.share +
            (self.share * self.loan.tenure * (self.loan.interest / self.loan.calculate_periodicity_factor())) +
            (self.share * self.loan.processing_fee),
            DEFAULT_DECIMAL_PLACES
        )
        int_total_amount = total_amount * (10 ** DEFAULT_DECIMAL_PLACES)
        int_emi_amount = int_total_amount // self.loan.tenure
        rem_amount = int_total_amount - (int_emi_amount * self.loan.tenure)
        emis = []
        for t in range(self.loan.tenure):
            emi = {
                'due_date': self.loan.effective_due_date(start_date, t),
                'status': 'NOT_STARTED',
                'paid_amount': 0
            }
            if rem_amount > 0:
                suggested_emi = int_emi_amount + 1
                rem_amount -= 1
            else:
                suggested_emi = int_emi_amount

            emi['suggested_emi'] = suggested_emi / (10 ** DEFAULT_DECIMAL_PLACES)
            emis.append(emi)

        return emis
    
    def create_installments(self, start_date):
        emis_data = self.calculate_emis(start_date)
        for i, emi in enumerate(emis_data):
            Installment.create_installment(self, emi, i + 1)

    def add_payment(self, amount_paid, payment_id, payment_date):
        if not self.loan.is_active:
            raise errors.InactiveLoan()
        
        amount_paid = Decimal(str(round(amount_paid, 5)))
        with transaction.atomic():
            loan_repayment = LoanRepayment.create_loan_repayment(self, payment_id, payment_date, amount_paid)

            # fulfill remaining installments in chronological order
            installments = Installment.objects.filter(
                loanshare=self
            ).exclude(
                status=InstallmentStatus.PAID.name
            ).order_by('order')

            for i in installments:
                if amount_paid > 0:
                    amount_paid = i.fulfill_loan_amount(amount_paid, loan_repayment)

            if amount_paid > 0:
                #if any amount still left that means we got extra money
                #so we will create InstallmentDetail obj with extra amount added
                last_ins = Installment.objects.select_for_update(of=('self',)).filter(
                    loanshare=self,
                ).order_by('order').last()
                InstallmentDetail.get_or_create_installment_details(
                    last_ins,
                    loan_repayment,
                    additional_amount=amount_paid
                )

            self.update_loanshare_status()

        return

    def update_loanshare_status(self):
        installments = Installment.objects.filter(loanshare=self)
        if len(installments) == len(installments.filter(status=InstallmentStatus.PAID.name)):
            self.status = LoanStatus.COMPLETED.name
            self.full_clean()
            self.save()
            self.loan.update_loan_status()

        return

    def __str__(self):
        return f"{str(self.loan.id)} : {str(self.id)} : {str(self.user.username)}"
    
class Installment(models.Model):
    order = models.IntegerField()
    loanshare = models.ForeignKey(LoanShare, on_delete=models.CASCADE)
    due_date = models.DateField()
    suggested_emi = models.DecimalField(max_digits=20, decimal_places=DEFAULT_DECIMAL_PLACES)
    status = models.CharField(
        max_length=30,
        choices=[(x.name, x.value) for x in InstallmentStatus],
        default = InstallmentStatus.UNPAID.name
    )

    def jsonify(self):
        data = model_to_dict(self, exclude=['id', 'order', 'loanshare'])
        data['paid_amount'] = self.suggested_emi - self.amount_remaining
        return data

    @classmethod
    def create_installment(cls, loanshare, emi_data, order):
        installment = cls(
            order=order,
            loanshare=loanshare,
            due_date=emi_data['due_date'],
            suggested_emi=emi_data['suggested_emi']
        )
        installment.full_clean()
        installment.save()
        return
    
    @property
    def amount_remaining(self):
        ins_details = InstallmentDetail.objects.filter(
            installment=self
        )
        amount_paid = 0
        for ins in ins_details:
            amount_paid += ins.amount
        return self.suggested_emi - amount_paid
    
    def installment_paid(self):
        if self.status == InstallmentStatus.PAID.name:
            return True

        return False
    
    def fulfill_loan_amount(self, amount_paid, loan_repayment):
        amount_ddt = 0
        if self.installment_paid() or amount_paid <= 0:
            return amount_paid

        locked_ins = Installment.objects.select_for_update(of=('self',)).get(pk=self.pk)
        amount_remaining = locked_ins.amount_remaining
        if amount_remaining > 0:
            amount_ddt = min(amount_remaining, amount_paid)
            amount_paid -= amount_ddt

        InstallmentDetail.get_or_create_installment_details(
            locked_ins,
            loan_repayment,
            amount_ddt=amount_ddt
        )
        return amount_paid
    
    def update_installment_status(self):
        if self.amount_remaining > 0 and self.amount_remaining < self.suggested_emi:
            self.status=InstallmentStatus.PARTIALLY_PAID.name
        elif self.amount_remaining == 0:
            self.status=InstallmentStatus.PAID.name

        self.full_clean()
        self.save()
    
class LoanRepayment(models.Model):
    installments = models.ManyToManyField(Installment, through='InstallmentDetail')
    payment = models.CharField(max_length=30, unique=True)
    payment_date = models.DateField()
    loanshare = models.ForeignKey(LoanShare, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=DEFAULT_DECIMAL_PLACES)

    @classmethod
    def create_loan_repayment(cls, loanshare, payment_id, payment_date, amount):
        loan_repayment = cls(
            payment=payment_id,
            payment_date=payment_date,
            loanshare=loanshare,
            amount=amount
        )
        loan_repayment.full_clean()
        loan_repayment.save()
        return loan_repayment

class InstallmentDetail(models.Model):
    installment = models.ForeignKey(Installment, on_delete=models.CASCADE)
    loan_repayment = models.ForeignKey(LoanRepayment, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=DEFAULT_DECIMAL_PLACES, default=0)
    date_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_or_create_installment_details(
        cls,
        installment,
        loan_repayment,
        amount_ddt=None,
        additional_amount=None
    ):
        ins_detail, created = cls.objects.get_or_create(
            installment=installment,
            loan_repayment=loan_repayment,
        )
        if amount_ddt is not None:
            ins_detail.amount = amount_ddt
        if additional_amount is not None:
            ins_detail.amount = ins_detail.amount + additional_amount if ins_detail.amount else additional_amount

        ins_detail.full_clean()
        ins_detail.save()
        installment.update_installment_status()
        return
