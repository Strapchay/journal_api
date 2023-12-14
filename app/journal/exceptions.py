from rest_framework.exceptions import APIException


class RequestDenied(APIException):
    status_code = 400
    default_detail = (
        "Cannot delete only table. Add more tables to be able to delete a table"
    )
    default_code = "Bad request"
