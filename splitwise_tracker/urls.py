"""
URL configuration for splitwise_tracker project.

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
from django.urls import path
from tracker.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('login_view/', login_view, name='login_view'),
    path('userprofile_add/', userprofile_add, name='userprofile_add'),
    path('member_home/', member_home, name='member_home'),
    path('admin_home/', admin_home, name='admin_home'),
    path('create_group/', create_group, name='create_group'),
    path('join_group/', join_group, name='join_group'),
    path('group_home/', group_home, name='group_home'),
    path('edit_profile/', edit_profile, name='edit_profile'),
    path('add_expense/', add_expense, name='add_expense'),
    path('expense_detail/<int:expense_id>/', expense_detail, name='expense_detail'),
    path('toggle_expense_approval/<int:expense_id>/', toggle_expense_approval, name='toggle_expense_approval'),
    path('toggle_dues/<int:member_id>/', toggle_dues, name='toggle_dues'),
    path('post_group_message/', post_group_message, name='post_group_message'),
    path('record_payment/', record_payment, name='record_payment'),
    path('approve_payment/<int:payment_id>/', approve_payment, name='approve_payment'),
    path('logout/', logout_view, name='logout_view'),
]