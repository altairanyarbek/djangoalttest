
from django.contrib import admin
from django.urls import path, include

#gffdd
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('quiz.urls'))
]
