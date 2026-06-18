from django.shortcuts import render
from .models import Region


def region_list(request):
    regions = Region.objects.filter(is_active=True)

    return render(request, "regions/region_list.html", {
        "regions": regions,
    })