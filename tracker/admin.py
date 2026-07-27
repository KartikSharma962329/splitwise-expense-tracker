from django.contrib import admin
from .models import *

admin.site.register(Admin)
admin.site.register(LoginData)
admin.site.register(UserProfile)
admin.site.register(Group)
admin.site.register(Members)
admin.site.register(Expense)
admin.site.register(ExpenseApproval)
admin.site.register(GroupMessage)
admin.site.register(Payment)

