from django.urls import path
from loan import views


urlpatterns = [
    path('loan/', views.LoanView.as_view(), name='loan_view'),
    path('approve/', views.ApproveLoan.as_view(), name='approve_loan_view'),
    path('add-payment/', views.AddPayment.as_view(), name='add_payment_view'),
]