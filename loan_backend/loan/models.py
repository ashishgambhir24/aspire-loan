from datetime import date, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.forms.models import model_to_dict
from lib.common import add_months
from lib.validators import validate_nonzero
from loan_backend.config import Periodicity, LoanStatus, InstallmentStatus
from loan_backend.constants import DEFAULT_PERIODICITY, DEFAULT_INTEREST, DEFAULT_PROCESSING_FEE, DEFAULT_DECIMAL_PLACES

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
    date_created = models.DateTimeField(auto_now_add=True)

    def jsonify(self):
        data = model_to_dict(self, exclude=['id', 'interest', 'processing_fee'])
        return data

    @classmethod
    def create_loan(cls, data, user):
        with transaction.atomic():
            loan = cls(
                amount=data['amount'],
                tenure=data['tenure'],
                periodicity=data.get('periodicity', DEFAULT_PERIODICITY),
                status=LoanStatus.PENDING.name,
                interest=data.get('interest', DEFAULT_INTEREST),
                processing_fee=data.get('processing_fee', DEFAULT_PROCESSING_FEE)
            )
            loan.full_clean()
            loan.save()

            LoanShare.create_loanshare(loan, data, user)

        loan_data = loan.jsonify()
        loan_data['emis'] = loan.emi_schedule()
        return loan_data
    
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

                emis.append(user_emis)
            else:
                user_emis['emis'] = ls.calculate_emis()

        return emis

    def calculate_periodicity_factor(self):
        if self.periodicity == 'daily':
            periodicity_factor = 365
        elif self.periodicity == 'weekly':
            periodicity_factor = 52
        elif self.periodicity == 'monthly':
            periodicity_factor = 12
        else:
            raise ValidationError

        return periodicity_factor      

    def effective_due_date(self, initial_date, order):
        if self.periodicity == 'daily':
            effective_due_date = initial_date + timedelta(days=order + 1)
        elif self.periodicity == 'weekly':
            effective_due_date = initial_date + timedelta(days=7 * (order + 1))
        elif self.periodicity == 'monthly':
            effective_due_date = add_months(initial_date, order + 1)
        else:
            raise ValidationError

        return effective_due_date

    
    def approve_loan(self):
        with transaction.atomic():
            self.status = LoanStatus.APPROVED.name
            self.approval_date = date.today()
            self.full_clean()
            self.save()

            for ls in self.loanshare_set.all():
                ls.status = LoanStatus.APPROVED.name
                ls.full_clean()
                ls.save()
                ls.create_installments()


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
            share=data['amount'],
            user=user,
            status=LoanStatus.PENDING.name,
            loan=loan
        )
        loanshare.full_clean()
        loanshare.save()
        return
    
    def calculate_emis(self):
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
                'due_date': self.loan.effective_due_date(date.today(), t),
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
    
    def create_installments(self):
        emis_data = self.calculate_emis()
        for emi in emis_data:
            Installment.create_installment(self, emi)

    def __str__(self):
        return f"{str(self.loan.id)} : {str(self.id)} : {str(self.user.username)}"
    
class Installment(models.Model):
    order = models.IntegerField()
    loanshare = models.ForeignKey(LoanShare, on_delete=models.CASCADE)
    due_date = models.DateField()
    suggested_emi = models.FloatField()
    status = models.CharField(
        max_length=30,
        choices=[(x.name, x.value) for x in InstallmentStatus],
        default = InstallmentStatus.UNPAID.name
    )

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

    def jsonify(self):
        data = model_to_dict(self, exclude=['id', 'order', 'loanshare'])
        data['paid_amount'] = "calculate paid" #TODO
        return data
