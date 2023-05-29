from datetime import date, datetime
from loan import errors
from loan.models import Loan, LoanShare
from loan.permissions import IsStaffUser
from loan_backend.config import LoanStatus, CLOSED_LOAN_STATUS
from rest_framework.views import APIView
from rest_framework.response import Response

class LoanView(APIView):
    def post(self, request):
        data = request.data
        user = request.user
        try:
            loan = Loan.create_loan(data, user)
        except Exception as e:
            raise errors.LoanInvalidDetails(e)

        return Response(loan.jsonify())
    
    def get(self, request):
        loans = Loan.objects.filter(loanshare__user=request.user)
        approved_loans = loans.filter(status__in=[LoanStatus.APPROVED.name, LoanStatus.HOLD.name])
        completed_loans = loans.filter(status__in=CLOSED_LOAN_STATUS)
        pending_loans = loans.filter(status=LoanStatus.PENDING.name)
        rejected_loans = loans.filter(status=LoanStatus.REJECTED.name)

        all_loans = []
        for loans in [approved_loans, pending_loans, completed_loans, rejected_loans]:
            for loan in loans:
                all_loans.append(loan.jsonify())

        return Response(all_loans)
    
class ApproveLoan(APIView):
    permission_classes=[IsStaffUser]
    def post(self, request):
        data = request.data
        try:
            loan = Loan.objects.get(id=data['loan_id'])
        except Loan.DoesNotExist:
            raise errors.InvalidLoanID("approve loan", data['loan_id'])
        
        loan.approve_loan(data.get('approval_date', date.today()))
        return Response(f"loan {loan.id} approved")
    
class AddPayment(APIView):
    def post(self, request):
        data=request.data
        try:
            loanshare = LoanShare.objects.get(id=data['loan_id'], user=request.user)
        except LoanShare.DoesNotExist:
            raise errors.InvalidLoanID("add payment", data['loan_id'])
        
        if data.get('payment_date', None):
            payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d')
        else:
            payment_date = date.today()

        try:
            loanshare.add_payment(
                data['amount'],
                data['payment_id'],
                payment_date
            )
        except Exception as e:
            raise errors.InvalidPayment(e)
        return Response("payment added")
