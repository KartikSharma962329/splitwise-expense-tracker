import random
import string
import json

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.core.mail import send_mail
from .models import *


def index(request):
    return render(request, 'index.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = LoginData.objects.get(email=email, password=password)
            request.session['email'] = user.email
            request.session['usertype'] = user.usertype

            if user.usertype == 'admin':
                return HttpResponseRedirect('/admin_home/')
            else:
                return HttpResponseRedirect('/member_home/')

        except LoginData.DoesNotExist:
            return render(request, 'login.html', {'error': 'Invalid email or password'})

    return render(request, 'login.html')


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        if not LoginData.objects.filter(email=email).exists():
            return render(request, 'forgot_password.html', {'error': 'No account found with that email'})

        otp = generate_otp()

        request.session['reset_email'] = email
        request.session['reset_otp'] = otp
        request.session['otp_created_at'] = timezone.now().isoformat()

        send_mail(
            subject='Settlé - Password Reset OTP',
            message=f'Your OTP to reset your Settlé password is: {otp}\nThis code expires in 5 minutes.',
            from_email=None,
            recipient_list=[email],
        )

        return HttpResponseRedirect('/verify_otp/')

    return render(request, 'forgot_password.html')


def verify_otp_view(request):
    email = request.session.get('reset_email')
    if not email:
        return HttpResponseRedirect('/forgot_password/')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        correct_otp = request.session.get('reset_otp')
        created_at_str = request.session.get('otp_created_at')

        if not correct_otp or not created_at_str:
            return HttpResponseRedirect('/forgot_password/')

        created_at = timezone.datetime.fromisoformat(created_at_str)
        is_expired = (timezone.now() - created_at).total_seconds() > 300

        if is_expired:
            return render(request, 'verify_otp.html', {'error': 'OTP expired. Please request a new one'})

        if entered_otp != correct_otp:
            return render(request, 'verify_otp.html', {'error': 'Invalid OTP'})

        # clear the OTP so it can't be reused
        del request.session['reset_otp']
        del request.session['otp_created_at']
        request.session['otp_verified'] = True

        return HttpResponseRedirect('/reset_password/')

    return render(request, 'verify_otp.html')


def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email or not request.session.get('otp_verified'):
        return HttpResponseRedirect('/forgot_password/')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            return render(request, 'reset_password.html', {'error': "Passwords don't match"})

        try:
            user = LoginData.objects.get(email=email)
        except LoginData.DoesNotExist:
            return HttpResponseRedirect('/forgot_password/')

        user.password = new_password
        user.save()

        del request.session['reset_email']
        del request.session['otp_verified']

        return render(request, 'login.html', {'error': 'Password reset successful. Please log in.'})

    return render(request, 'reset_password.html')


def userprofile_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        nickname = request.POST.get('nickname')
        phone = request.POST.get('phone')
        gender = request.POST.get('gender')
        upi_id = request.POST.get('upi_id')
        bio = request.POST.get('bio')

        if LoginData.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already registered'})

        LoginData.objects.create(email=email, password=password, usertype='member')
        UserProfile.objects.create(
            email=email, name=name, nickname=nickname,
            phone=phone, gender=gender, upi_id=upi_id, bio=bio
        )

        request.session['email'] = email
        request.session['usertype'] = 'member'

        return HttpResponseRedirect('/member_home/')

    return render(request, 'signup.html')


def member_home(request):
    email = request.session.get('email')

    if not email:
        return HttpResponseRedirect('/login/')

    try:
        profile = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return render(request, 'no_profile.html')

    memberships = Members.objects.filter(email=email)

    groups = []
    for m in memberships:
        try:
            group = Group.objects.get(group_id=int(m.group_id))
            groups.append(group)
        except (Group.DoesNotExist, ValueError):
            continue

    context = {
        'profile': profile,
        'groups': groups,
    }
    return render(request, 'member_home.html', context)


def generate_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def create_group(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    if request.method == 'POST':
        group_name = request.POST.get('group_name')
        description = request.POST.get('description')

        invite_code = generate_invite_code()
        while Group.objects.filter(invite_code=invite_code).exists():
            invite_code = generate_invite_code()

        group = Group.objects.create(
            group_name=group_name,
            description=description,
            created_by=email,
            invite_code=invite_code
        )

        Members.objects.create(
            group_id=str(group.group_id),
            email=email,
            role='leader'
        )

        request.session['current_group_id'] = str(group.group_id)
        return HttpResponseRedirect('/group_home/')

    return render(request, 'create_group.html')


def join_group(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    if request.method == 'POST':
        invite_code = request.POST.get('invite_code')

        try:
            group = Group.objects.get(invite_code=invite_code)
        except Group.DoesNotExist:
            return render(request, 'join_group.html', {'error': 'Invalid invite code'})

        already_member = Members.objects.filter(group_id=str(group.group_id), email=email).exists()
        if already_member:
            return render(request, 'join_group.html', {'error': 'You are already in this group'})

        Members.objects.create(
            group_id=str(group.group_id),
            email=email,
            role='member'
        )

        request.session['current_group_id'] = str(group.group_id)
        return HttpResponseRedirect('/group_home/')

    return render(request, 'join_group.html')


def admin_home(request):
    email = request.session.get('email')
    usertype = request.session.get('usertype')

    if not email:
        return HttpResponseRedirect('/login/')

    if usertype != 'admin':
        return HttpResponseRedirect('/member_home/')

    groups = Group.objects.all()
    context = {'groups': groups}
    return render(request, 'admin_home.html', context)


def calculate_pending_between(group_id, from_email, to_email):
    """
    Returns net amount (in paise) from_email still owes to_email in this group,
    after netting out approved payments. Positive = from_email owes to_email.
    """
    owed = 0

    approved_expenses = Expense.objects.filter(
        group_id=str(group_id), paid_by=to_email, status='approved'
    )
    for expense in approved_expenses:
        try:
            split_data = json.loads(expense.split_data)
        except (ValueError, TypeError):
            split_data = {}
        owed += split_data.get(from_email, 0)

    payments = Payment.objects.filter(
        group_id=str(group_id),
        payer_email=from_email,
        receiver_email=to_email,
        status='approved'
    )
    already_paid = sum(p.amount_paise for p in payments)

    return owed - already_paid


def get_fee_summary(group_id, email):
    """
    Full two-sided fee summary for a user in a group:
    - total_owed_by_me: sum of my shares in expenses others paid for
    - total_paid_by_me: approved payments I've made to others
    - remaining_i_owe: what I still need to pay
    - total_owed_to_me: sum of others' shares in expenses I paid for
    - total_received_by_me: approved payments others have made to me
    - remaining_others_owe: what others still need to pay me
    """
    total_owed_by_me = 0
    total_owed_to_me = 0

    approved_expenses = Expense.objects.filter(group_id=str(group_id), status='approved')
    for expense in approved_expenses:
        try:
            split_data = json.loads(expense.split_data)
        except (ValueError, TypeError):
            split_data = {}

        if expense.paid_by == email:
            # I paid this expense — everyone else's share is owed to me
            for member_email, share_paise in split_data.items():
                if member_email != email:
                    total_owed_to_me += share_paise
        else:
            # someone else paid — my share is owed by me
            total_owed_by_me += split_data.get(email, 0)

    paid_by_me = Payment.objects.filter(
        group_id=str(group_id), payer_email=email, status='approved'
    )
    total_paid_by_me = sum(p.amount_paise for p in paid_by_me)

    received_by_me = Payment.objects.filter(
        group_id=str(group_id), receiver_email=email, status='approved'
    )
    total_received_by_me = sum(p.amount_paise for p in received_by_me)

    remaining_i_owe = total_owed_by_me - total_paid_by_me
    if remaining_i_owe < 0:
        remaining_i_owe = 0

    remaining_others_owe = total_owed_to_me - total_received_by_me
    if remaining_others_owe < 0:
        remaining_others_owe = 0

    return {
        'total_owed_by_me': total_owed_by_me,
        'total_paid_by_me': total_paid_by_me,
        'remaining_i_owe': remaining_i_owe,
        'total_owed_to_me': total_owed_to_me,
        'total_received_by_me': total_received_by_me,
        'remaining_others_owe': remaining_others_owe,
    }


def group_home(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        request.session['current_group_id'] = group_id
    else:
        group_id = request.session.get('current_group_id')

    if not group_id:
        return HttpResponseRedirect('/member_home/')

    try:
        group = Group.objects.get(group_id=group_id)
    except Group.DoesNotExist:
        return HttpResponseRedirect('/member_home/')

    is_member = Members.objects.filter(group_id=str(group_id), email=email).exists()
    if not is_member:
        return HttpResponseRedirect('/member_home/')

    member_rows = Members.objects.filter(group_id=str(group_id))

    members_list = []
    for m in member_rows:
        try:
            profile = UserProfile.objects.get(email=m.email)
            members_list.append({'profile': profile, 'member': m})
        except UserProfile.DoesNotExist:
            continue

    # expenses still waiting on approvals
    pending_expenses = Expense.objects.filter(
        group_id=str(group_id), status='pending'
    ).order_by('-expense_date')

    # transaction history - only expenses every member has approved
    # includes the parsed split breakdown for each expense
    approved_expenses_raw = Expense.objects.filter(
        group_id=str(group_id), status='approved'
    ).order_by('-expense_date')

    approved_expenses = []
    for exp in approved_expenses_raw:
        try:
            split_data = json.loads(exp.split_data)
        except (ValueError, TypeError):
            split_data = {}

        # turn the split dict into a list so the template can loop it easily
        split_list = []
        for member_email, share_paise in split_data.items():
            split_list.append({'email': member_email, 'share_paise': share_paise})

        approved_expenses.append({
            'expense': exp,
            'split_list': split_list,
        })

    # group chat messages
    messages = GroupMessage.objects.filter(group_id=str(group_id)).order_by('sent_at')

    # payments waiting on me to approve/reject
    payments_for_me_to_approve = Payment.objects.filter(
        group_id=str(group_id), receiver_email=email, status='pending'
    ).order_by('-created_at')

    # confirmed payments, visible to the whole group
    approved_payments = Payment.objects.filter(
        group_id=str(group_id), status='approved'
    ).order_by('-approved_at')

    # payments I've submitted, whatever their status
    payments_i_made = Payment.objects.filter(
        group_id=str(group_id), payer_email=email
    ).order_by('-created_at')

    # two-sided fee counter for this user in this group
    fee_summary = get_fee_summary(group_id, email)

    context = {
        'group': group,
        'members_list': members_list,
        'approved_expenses': approved_expenses,
        'pending_expenses': pending_expenses,
        'messages': messages,
        'my_email': email,
        'payments_for_me_to_approve': payments_for_me_to_approve,
        'approved_payments': approved_payments,
        'payments_i_made': payments_i_made,
        'fee_summary': fee_summary,
    }
    return render(request, 'group_home.html', context)


def toggle_dues(request, member_id):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    try:
        member_row = Members.objects.get(member_id=member_id)
    except Members.DoesNotExist:
        return HttpResponseRedirect('/group_home/')

    # only allow a member to toggle their own dues-cleared status
    if member_row.email != email:
        return HttpResponseRedirect('/group_home/')

    member_row.dues_cleared = not member_row.dues_cleared
    member_row.save()

    return HttpResponseRedirect('/group_home/')


def post_group_message(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    if request.method != 'POST':
        return HttpResponseRedirect('/group_home/')

    group_id = request.session.get('current_group_id')
    if not group_id:
        return HttpResponseRedirect('/member_home/')

    is_member = Members.objects.filter(group_id=str(group_id), email=email).exists()
    if not is_member:
        return HttpResponseRedirect('/member_home/')

    message_text = request.POST.get('message_text')
    if message_text:
        GroupMessage.objects.create(
            group_id=str(group_id),
            email=email,
            message_text=message_text
        )

    return HttpResponseRedirect('/group_home/')


def edit_profile(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    try:
        profile = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return HttpResponseRedirect('/member_home/')

    if request.method == 'POST':
        profile.name = request.POST.get('name')
        profile.nickname = request.POST.get('nickname')
        profile.phone = request.POST.get('phone')
        profile.gender = request.POST.get('gender')
        profile.upi_id = request.POST.get('upi_id')
        profile.bio = request.POST.get('bio')
        profile.save()

        return HttpResponseRedirect('/member_home/')

    context = {'profile': profile}
    return render(request, 'edit_profile.html', context)


def add_expense(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    group_id = request.session.get('current_group_id')
    if not group_id:
        return HttpResponseRedirect('/member_home/')

    try:
        group = Group.objects.get(group_id=group_id)
    except Group.DoesNotExist:
        return HttpResponseRedirect('/member_home/')

    member_rows = Members.objects.filter(group_id=str(group_id))
    members_list = []
    for one_row in member_rows:
        try:
            one_profile = UserProfile.objects.get(email=one_row.email)
            members_list.append(one_profile)
        except UserProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        description = request.POST.get('description')
        amount_typed = request.POST.get('amount')

        try:
            amount_in_paise = int(float(amount_typed) * 100)
        except (TypeError, ValueError):
            context = {'group': group, 'members_list': members_list, 'error': 'Enter a valid amount'}
            return render(request, 'add_expense.html', context)

        split_type = request.POST.get('split_type')
        expense_date_input = request.POST.get('expense_date')

        split_data = {}

        if not members_list:
            context = {'group': group, 'members_list': members_list, 'error': 'No members to split with'}
            return render(request, 'add_expense.html', context)

        if split_type == 'custom':
            # go through each person and read what they typed
            for one_profile in members_list:
                box_name = "contribution_" + str(one_profile.profile_id)
                typed_value = request.POST.get(box_name)
                try:
                    money_in_paise = int(float(typed_value) * 100) if typed_value else 0
                except ValueError:
                    money_in_paise = 0
                split_data[one_profile.email] = money_in_paise

        else:
            # equal split - simple version

            # step 1: how many people are sharing the bill
            total_people = len(members_list)

            # step 2: divide the total money equally
            share_for_each_person = amount_in_paise // total_people

            # step 3: give every single person the same share
            for one_profile in members_list:
                split_data[one_profile.email] = share_for_each_person

            # step 4: sometimes a few coins are left over after dividing
            # (example: 100 paise shared between 3 people leaves 1 paise extra)
            coins_left_over = amount_in_paise - (share_for_each_person * total_people)

            # step 5: give those extra leftover coins to the first person in the list
            first_person = members_list[0]
            split_data[first_person.email] = split_data[first_person.email] + coins_left_over

        expense = Expense.objects.create(
            group_id=str(group_id),
            paid_by=email,
            description=description,
            amount=amount_in_paise,
            split_type=split_type,
            split_data=json.dumps(split_data),
            expense_date=expense_date_input if expense_date_input else timezone.now()
        )

        # create one approval row per member sharing this expense
        for member_email in split_data.keys():
            ExpenseApproval.objects.create(
                expense_id=str(expense.expense_id),
                email=member_email,
                approved=False
            )

        return HttpResponseRedirect('/group_home/')

    context = {'group': group, 'members_list': members_list}
    return render(request, 'add_expense.html', context)


def expense_detail(request, expense_id):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    try:
        expense = Expense.objects.get(expense_id=expense_id)
    except Expense.DoesNotExist:
        return HttpResponseRedirect('/group_home/')

    is_member = Members.objects.filter(group_id=str(expense.group_id), email=email).exists()
    if not is_member:
        return HttpResponseRedirect('/member_home/')

    split_data = json.loads(expense.split_data)

    approvals = ExpenseApproval.objects.filter(expense_id=str(expense_id))
    approval_list = []
    my_approval = None
    for a in approvals:
        approval_list.append(a)
        if a.email == email:
            my_approval = a

    context = {
        'expense': expense,
        'split_data': split_data,
        'approval_list': approval_list,
        'my_approval': my_approval,
    }
    return render(request, 'expense_detail.html', context)


def toggle_expense_approval(request, expense_id):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    try:
        approval = ExpenseApproval.objects.get(expense_id=str(expense_id), email=email)
    except ExpenseApproval.DoesNotExist:
        return HttpResponseRedirect('/group_home/')

    approval.approved = not approval.approved
    approval.save()

    # if everyone sharing this expense has approved, flip the expense status
    all_approvals = ExpenseApproval.objects.filter(expense_id=str(expense_id))
    all_approved = all(a.approved for a in all_approvals)

    try:
        expense = Expense.objects.get(expense_id=expense_id)
        expense.status = 'approved' if all_approved else 'pending'
        expense.save()
    except Expense.DoesNotExist:
        pass

    return HttpResponseRedirect(f'/expense_detail/{expense_id}/')


def record_payment(request):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    group_id = request.session.get('current_group_id')
    if not group_id:
        return HttpResponseRedirect('/member_home/')

    try:
        group = Group.objects.get(group_id=group_id)
    except Group.DoesNotExist:
        return HttpResponseRedirect('/member_home/')

    is_member = Members.objects.filter(group_id=str(group_id), email=email).exists()
    if not is_member:
        return HttpResponseRedirect('/member_home/')

    if request.method == 'POST':
        receiver_email = request.POST.get('receiver_email')
        amount_typed = request.POST.get('amount')
        note = request.POST.get('note', '')
        mode = request.POST.get('mode', 'offline')

        try:
            amount_paise = int(float(amount_typed) * 100)
        except (TypeError, ValueError):
            amount_paise = 0

        if receiver_email and amount_paise > 0:
            Payment.objects.create(
                group_id=str(group_id),
                payer_email=email,
                receiver_email=receiver_email,
                amount_paise=amount_paise,
                note=note,
                mode=mode,
                status='pending'
            )

        return HttpResponseRedirect('/group_home/')

    member_rows = Members.objects.filter(group_id=str(group_id)).exclude(email=email)
    member_list = []
    for m in member_rows:
        try:
            profile = UserProfile.objects.get(email=m.email)
            pending = calculate_pending_between(group_id, email, m.email)
            member_list.append({'profile': profile, 'pending_paise': pending})
        except UserProfile.DoesNotExist:
            continue

    context = {'group': group, 'member_list': member_list}
    return render(request, 'record_payment.html', context)


def approve_payment(request, payment_id):
    email = request.session.get('email')
    if not email:
        return HttpResponseRedirect('/login/')

    try:
        payment = Payment.objects.get(payment_id=payment_id)
    except Payment.DoesNotExist:
        return HttpResponseRedirect('/group_home/')

    if payment.receiver_email != email:
        return HttpResponseRedirect('/group_home/')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            payment.status = 'approved'
            payment.approved_at = timezone.now()
        else:
            payment.status = 'rejected'
        payment.save()

    return HttpResponseRedirect('/group_home/')


def logout_view(request):
    request.session.flush()
    return HttpResponseRedirect('/login_view/')