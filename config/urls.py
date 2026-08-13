"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from invoices import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', views.upload_invoice, name='upload_invoice'),
    path('review/', views.review_queue, name='review_queue'),
    path('review/<int:invoice_id>/', views.review_decision, name='review_decision'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('upload/confirm/', views.confirm_upload, name='confirm_upload'),
    path('upload/cancel/', views.cancel_upload, name='cancel_upload'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)