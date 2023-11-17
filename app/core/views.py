from rest_framework.decorators import api_view
from rest_framework.response import Response

# Create your views here.
@api_view(["GET"])
def health_check(request):
    """
    Ping the API to know if its up
    """
    return Response({"healthy": True})
