from django.db import models
from django.utils import timezone


class Admin(models.Model):
    admin_id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=100, unique=True)  # links back to LoginData; existence = admin status
    admin_name = models.CharField(max_length=100)

    def __str__(self):
        return self.admin_name


class LoginData(models.Model):
    USERTYPE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    login_id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)  # hash this before saving, in production
    usertype = models.CharField(max_length=10, choices=USERTYPE_CHOICES, default='member')

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=100, unique=True)  # links back to LoginData by email
    name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=50, blank=True)  # shown on member cards; falls back to name if blank
    phone = models.CharField(max_length=15, blank=True)
    gender = models.CharField(
        max_length=10,
        blank=True,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    )
    upi_id = models.CharField(max_length=100, blank=True)  # for later settlement/UPI QR flow
    bio = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class Group(models.Model):
    group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    created_by = models.CharField(max_length=100)  # email of the user who created the group
    invite_code = models.CharField(max_length=10, unique=True)  # shareable code for joining
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.group_name


class Members(models.Model):
    ROLE_CHOICES = [
        ('leader', 'Leader'),
        ('member', 'Member'),
    ]

    member_id = models.AutoField(primary_key=True)
    group_id = models.CharField(max_length=20)  # links to Group.group_id
    email = models.CharField(max_length=100)  # links to UserProfile.email
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    dues_cleared = models.BooleanField(default=False)  # true = "my dues are cleared, I got my pending amount"
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} in group {self.group_id}"


class Expense(models.Model):
    SPLIT_TYPE_CHOICES = [
        ('equal', 'Equal'),
        ('custom', 'Custom'),
    ]

    PAYMENT_MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ]

    expense_id = models.AutoField(primary_key=True)
    group_id = models.CharField(max_length=20)
    paid_by = models.CharField(max_length=100)
    description = models.CharField(max_length=150)
    amount = models.IntegerField()
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPE_CHOICES, default='equal')
    split_data = models.TextField()
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='online')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    expense_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - ₹{self.amount / 100}"


class ExpenseApproval(models.Model):
    approval_id = models.AutoField(primary_key=True)
    expense_id = models.CharField(max_length=20)  # links to Expense.expense_id
    email = models.CharField(max_length=100)  # which member this approval belongs to
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.email} - expense {self.expense_id} - {self.approved}"


class GroupMessage(models.Model):
    message_id = models.AutoField(primary_key=True)
    group_id = models.CharField(max_length=20)  # links to Group.group_id
    email = models.CharField(max_length=100)  # who sent it
    message_text = models.CharField(max_length=500)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email}: {self.message_text}"


class Payment(models.Model):
    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    payment_id = models.AutoField(primary_key=True)
    group_id = models.CharField(max_length=20)  # links to Group.group_id
    payer_email = models.CharField(max_length=100)  # links to UserProfile.email
    receiver_email = models.CharField(max_length=100)  # links to UserProfile.email
    amount_paise = models.IntegerField()
    note = models.CharField(max_length=255, blank=True)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='offline')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.payer_email} -> {self.receiver_email} - ₹{self.amount_paise / 100} - {self.status}"