from rest_framework.exceptions import APIException

class InvalidPeriodicity(APIException):
    status_code = 400
    default_detail = "given periodicity is invalid"
    default_code = "invalid_periodicity"

class InvalidLoanApproval(APIException):
    status_code = 400
    default_detail = "given loan cannot be approved"
    default_code = "invalid_loan_approval"

class InactiveLoan(APIException):
    status_code = 400
    default_detail = "cannot perform this operation on inactive loan"
    default_code = "inactive_loan"

class LoanInvalidDetails(APIException):
    status_code = 400
    default_detail = "invalid details provided to create loan:"
    default_code = "invalid_loan_details"

    def __init__(self, err):
        super().__init__(f"invalid details provided to create loan: {err}")

class InvalidLoanID(APIException):
    status_code = 400
    default_detail = "invalid loan id provided:"
    default_code = "invalid_loan_id"

    def __init__(self, msg, id):
        super().__init__(f"invalid loan id provided: {msg}: {id}")

class InvalidPayment(APIException):
    status_code = 400
    default_detail = "invalid payment details provided:"
    default_code = "invalid_payment_details"

    def __init__(self, err):
        super().__init__(f"iinvalid payment details provided: {err}")
