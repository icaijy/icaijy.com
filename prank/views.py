from django.shortcuts import render

def vip(request):
    return render(request, "prank/vip.html")