from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse
from loan.models import Loan, LoanShare, Installment, InstallmentDetail, LoanRepayment

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_filter = ('status',)
    list_display = ('id', 'amount', 'tenure', 'users', 'status')
    readonly_fields = ('link_to_installments', 'users')

    def users(self, loan):
        users = []
        loanshares = LoanShare.objects.filter(loan=loan)
        for ls in loanshares:
            users.append(ls.user.username)

        return ", ".join(users)
    users.short_description = 'Users Liable'

    def link_to_installments(self, loan):
        links = []
        for i in Installment.objects.filter(loanshare__loan=loan).order_by('order'):
            url = reverse("admin:loan_installment_change", args=[i.id])
            link = '<a href="%s">%s</a>' % (url, f"{str(i.due_date)} : {i.suggested_emi} : {i.loanshare.user.username} : {i.status}")
            links.append(link)

        return mark_safe(' || '.join(links))
    link_to_installments.short_description = 'Installments'

@admin.register(LoanShare)
class LoanShareAdmin(admin.ModelAdmin):
    pass

@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_filter = ('status',)
    list_display = ('id', 'suggested_emi', 'loan_id', 'amount_remaining', 'status')
    readonly_fields = ('amount_remaining', 'penalty_remaining')

    def loan_id(self, installment):
        return installment.loanshare.loan.id
    loan_id.short_description = 'Loan ID'

@admin.register(InstallmentDetail)
class InstallmentDetailAdmin(admin.ModelAdmin):
    pass

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    pass
