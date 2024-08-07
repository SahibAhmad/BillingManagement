import datetime
import json
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from .models import (Room, Meter, MeterToRoom, MeterRateToRoom, FlatRateToRoom, QuarterType,
                     UserDetails, Department, UsersToDepartment, UsersToRoom,
                     MeterRate, MeterRateRange, FlatRate, FlatRateRange, FlatRateAdditional, Reading, MeteredBill, UnmeteredBill)
from django import template
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.models import Group
import ast
import random
import string
from django.core.mail import send_mail
from mysite.settings import EMAIL_HOST_USER
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.http import HttpResponse

# user functions
def is_user(user):
    return user.is_authenticated and user.groups.filter(name='user').exists()
def is_admin(user):
    return user.is_authenticated and user.groups.filter(name='admin').exists()
def is_operator(user):
    return user.is_authenticated and user.groups.filter(name='operator').exists()
def is_admin_or_operator(user):
    return user.is_authenticated and (user.groups.filter(name='operator').exists() or user.groups.filter(name='admin').exists())

# Rest of your view code remains unchanged.


def loginpage(request, message=None):
    context = {'segment': 'index'}
    if message is not None:
        context[message[0]] = message[1]
    html_template = loader.get_template('accounts/login.html')
    return HttpResponse(html_template.render(context, request))


def loginuser(request):
    msg = None  # Initialize msg to None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login Successful")
            msg = ["success_message", "Login Successful"]

            if user.groups.filter(name='user').exists():
                return userDetails(request)
            else:
                return index(request, message=msg)

        else:
            messages.error(request, "Invalid username or password")
            msg = ["error_message", "Invalid username or password"]
            return loginpage(request, message=msg)
    else:
        return loginpage(request, message=msg)


@login_required(login_url='login.html')
@csrf_protect
def logoutuser(request):
    msg = []
    logout(request)
    messages.success(request, "Logged Out Successfully")
    msg = ["success_message", "Logged Out Successfully"]
    return loginpage(request, message=msg)

def passwordresetpage(request,message=None):
    context = {'segment': 'index'}
    if message is not None:
        context[message[0]] = message[1]
    html_template = loader.get_template('accounts/password_reset.html')
    return HttpResponse(html_template.render(context, request))

def password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_details = get_object_or_404(UserDetails, email=email)
        user = user_details.django_user
        
        if user is not None:
            current_site = get_current_site(request)
            subject = 'Password Reset Request'
            message = render_to_string('accounts/password_reset_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            send_mail(subject, message, EMAIL_HOST_USER, [email])
            return redirect('password_reset_done')
        else:
            messages.error(request, 'No user found with this email.')
            return redirect('password_reset')
    return render(request, 'accounts/password_reset.html')

def password_reset_done(request):
    return render(request, 'accounts/password_reset_done.html')

def password_reset_confirm(request, uidb64, token,message=None):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if(new_password!=confirm_password):
                messages.error(request, "Password Does Not Match")
                msg = ['error_message', "Password Does Not Match."]
                return render(request, 'accounts/password_reset_confirm.html', {'user': user})
            user.set_password(new_password)
            user.save()
            return redirect('password_reset_complete')

        return render(request, 'accounts/password_reset_confirm.html', {'user': user})
    else:
        return HttpResponse('Invalid password reset link.')

def password_reset_complete(request):
    return render(request, 'accounts/password_reset_complete.html')


@user_passes_test(is_user)
@login_required
@csrf_protect  
def changepasswordpage(request,message=None):
    context = {'segment': 'index'}
    if message is not None:
        context[message[0]] = message[1]
    html_template = loader.get_template('accounts/change_password.html')
    return HttpResponse(html_template.render(context, request))

@user_passes_test(is_user)
@login_required
@csrf_protect  
def change_password(request):
    msg = []
    if request.method == 'POST':
        old_password = request.POST.get('password')
        new_password = request.POST.get('newpassword')
        confirmpassword = request.POST.get('confirmpassword')
        user = request.user
        if not user.check_password(old_password):
            messages.error(request, "Your Old Password is Incorrect.")
            msg = ['error_message', "Old Password is Incorrect."]
        elif user.check_password(new_password):
            messages.error(request, "Your Old Password is Matching New Password.")
            msg = ['error_message', "Your Old Password is Matching New Password."]
        elif confirmpassword != new_password:
            messages.error(request, " Password Does not match.")
            msg = ['error_message', "Password Does not match"]
        elif user.check_password(old_password) and confirmpassword == new_password:
            user.set_password(new_password)
            user.save()
            messages.success(request, " Password Changed Successfully.")
            msg = ['success_message', "Password Changed Successfully"]
        else:
            return page_not_found(request)
    return changepasswordpage(request, message=msg)


@login_required
@csrf_protect  
def user_home(request):
    if request.user.groups.filter(name='user').exists():
        return redirect('user_profile') 
    elif request.user.groups.filter(name='admin').exists():
        return index(request,message=None)
    elif request.user.groups.filter(name='operator').exists():
        return index(request,message=None)
    else:
        return loginpage(request, message=None)


@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_user)
def userDetails(request):
    user=request.user
    context = {}
    # user_id = int(user.pk)
    username = user.username
    user = User.objects.get(username=username)
    user_details = UserDetails.objects.get(django_user=user)
    user_id = user_details.user_id
    # user_id = UserDetails.objects.get(username=username).user_id
    
    # username = UserDetails.objects.get(usser_id = user_id).django_user.username

    user_details = UserDetails.objects.get(user_id=user_id)
    user_department = UsersToDepartment.objects.get(
        user_id=user_id).department_id.department_name
    room_id = None
    room_details = None
    quarter_type = None
    if UsersToRoom.objects.filter(user_id=user_id).exists():
        room_id = UsersToRoom.objects.get(user_id=user_id).room_id.room_id
        room_details = Room.objects.get(room_id=room_id)
        quarter_type = room_details.quarter_type_id.quarter_name

    context = {'user_details': user_details, 'user_department': user_department,
               'room_details': room_details, 'quarter_type': quarter_type}
    return render(request, 'home/user_profile.html', context)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_user)
def get_user_bills(request):
    # username = request.POST.get('username')
    # user_id = 1
    user=request.user
    username = user.username
    user = User.objects.get(username=username)
    user_details = UserDetails.objects.get(django_user=user)
    user_id = user_details.user_id
    # username = UserDetails.objects.get(user_id = user_id).django_user.username

    metered_bills = MeteredBill.objects.filter(user_name=username)
    quarterType_data = QuarterType.objects.all()

    context = {}
    
    #context['quarterType'] = quarterType_data
    #if metered_bills:
    #    context['metered_bills'] = metered_bills
        
        # context['metered_bills'] = metered_bills
    unmetered_bills = UnmeteredBill.objects.filter(user_name=username)
    #if unmetered_bills:
    #    context['unmetered_bills'] = unmetered_bills,
        # context['unmetered_bills'] = unmetered_bills

    context = {
        'metered_bills': metered_bills,
        'unmetered_bills': unmetered_bills,
        'quarterType': quarterType_data,
    }
    return render(request, 'home/user_bills.html', context)

# renders home page
@user_passes_test(is_admin_or_operator)
@login_required(login_url='login.html')
@csrf_protect
def index(request,message=None):
    context = {'segment': 'index'}

    today = datetime.datetime.now()
    from_month = today.month;
    to_month = today.month-1;
    u_bills = [0]*13
    m_bills = [0]*13
    u_bills_p = [0]*13
    m_bills_p = [0]*13
    bills = [0]*13
    bills_p = [0]*13
    data = [0]*12
    m_data = [0]*12
    u_data = [0]*12
    month = [0]*12
    year = [0]*12
    units_cur=[0]*13
    units_pre=[0]*13
    units =[0]*12
    metered_bills = MeteredBill.objects.filter(year=today.year)
    Unmetered_bills = UnmeteredBill.objects.filter(year=today.year)
    metered_bills_p = MeteredBill.objects.filter(year=today.year-1)
    Unmetered_bills_p = UnmeteredBill.objects.filter(year=today.year-1)
    context['metered_bills'] = metered_bills
    context['unmetered_bills'] = Unmetered_bills
    for i in metered_bills:
        m_bills[i.month]+=i.total_bill
        units_cur[i.month]+=i.units_consumed
    for i in Unmetered_bills:
        u_bills[i.month]+=i.total_bill
    for i in metered_bills_p:
        m_bills_p[i.month]+=i.total_bill
        untis_pre[i.month]+=i.units_consumed
    for i in Unmetered_bills_p:
        u_bills_p[i.month]+=i.total_bill
    for i in range(1,13):
        bills[i] = m_bills[i]+u_bills[i]
        bills_p[i] = m_bills_p[i]+u_bills_p[i]
    for i in range(from_month,13) :
        data[i-from_month] = bills_p[i]
        m_data[i-from_month] = m_bills_p[i]
        u_data[i-from_month] = u_bills_p[i]
        month[i-from_month] = i
        year[i-from_month] = today.year-1
        units[i-from_month] = units_pre[i]
    for i in range(1,to_month+1) :
        data[i+(12-from_month)] = bills[i]
        m_data[i+(12-from_month)] = m_bills[i]
        u_data[i+(12-from_month)] = u_bills[i]
        month[i+(12-from_month)] = i
        year[i+(12-from_month)] = today.year
        units[i+(12-from_month)] = units_cur[i]
        
    context['bills'] = data
    context['month'] = month
    context['year'] = year
    context['u_bills'] = u_data
    context['m_bills'] = m_data
    context['units'] = units
    
    if message is not None:
        context[message[0]] = message[1]

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)

def calculate_bill(request):
    try:
        due_date = request.POST.get('due_date')
        issue_date = request.POST.get('issue_date')
        year = request.POST.get('selected_year')
        month = int(request.POST.get('selected_month'))
        bill_type = request.POST.get('bill_type')
        if bill_type == 'bulk-bill':
            fetch_bulk_bills(month, year, due_date, issue_date)
        else:
            room_number = request.POST.get('room_number')
            quarter_type = request.POST.get('quarter_type')
            fetch_single_bill(month, year, room_number,
                              quarter_type, due_date, issue_date)
        return render(request, 'home/fetch_bill.html', {'success': 'Bill Generated Successfully'})
    except Exception as e:
        return render(request, 'home/fetch_bill.html', {'error': e})

@transaction.atomic
def get_bill(room_id, month, year, due_date, issue_date):
    try:
        Room_obj = Room.objects.get(room_id=room_id)
        bill = Room_obj.calculate_amount(year, month)
        db_user = UsersToRoom.objects.get(room_id=room_id).user_id
        username = UserDetails.objects.get(
            user_id=db_user.user_id).django_user.username
        # username = db_user.username
        full_name = db_user.full_name
        email = db_user.email
        user_department = UsersToDepartment.objects.get(
            user_id=db_user).department_id.department_name
        room_number = Room_obj.room_number
        quarter_type = Room_obj.quarter_type_id.quarter_name
        sanctioned_load = Room_obj.sanctioned_load
        
        if UnmeteredBill.objects.filter(room_number=room_number, quarter_type=quarter_type, month=month, year=year).exists():
            return
        
        if MeteredBill.objects.filter(room_number=room_number, quarter_type=quarter_type, month=month, year=year).exists():
            return
        
        if bill.get('duty_charges') != None and MeteredBill.objects.filter(room_number=room_number, quarter_type=quarter_type, month=month, year=year).exists():
            return
        if bill.get('duty_charges') == None and UnmeteredBill.objects.filter(room_number=room_number, quarter_type=quarter_type, month=month, year=year).exists():
            return
        if (db_user.user_type == 'outsource'):
            db_user.balance += bill.get('total')
            db_user.save()
        opening_balance = db_user.balance
        db_user_x = UsersToRoom.objects.get(room_id=room_id).user_id

        if bill.get('duty_charges') != None:
            db_meter_to_room = MeterToRoom.objects.get(
                room_id=room_id).meter_id

            units_consumed = Reading.objects.get(
                meter_id=db_meter_to_room, month=month, year=year).units_consumed
            meter_rate_name = MeterRateToRoom.objects.get(
                room_id=room_id).meter_rate_id.name
            energy_charges = bill.get('energy_cost')
            demand_charges = bill.get('demand_charges')
            duty_charges = bill.get('duty_charges')
            meter_id = MeterToRoom.objects.get(room_id=room_id).meter_id
            sum_units_consumed = 0

            sum_units_consumed = Reading.objects.filter(Q(meter_id=meter_id), Q(year__lt=year) | Q(
                year=year, month__lt=month)).aggregate(Sum('units_consumed'))['units_consumed__sum']

            sum_units_consumed = 0 if sum_units_consumed == None else sum_units_consumed
            db_meter = Meter.objects.get(meter_id=db_meter_to_room.meter_id)
            sum_units_consumed += db_meter.initial_reading
            MeteredBill.objects.create(user_name=username, full_name=full_name, email=email, user_department=user_department, opening_balance=opening_balance, room_number=room_number, quarter_type=quarter_type, sanctioned_load=sanctioned_load, meter_rate_name=meter_rate_name,
                                       units_consumed=units_consumed, energy_charges=energy_charges, demand_charges=demand_charges, duty_charges=duty_charges, month=month, year=year, due_date=due_date, issued_date=issue_date, current_reading=sum_units_consumed + units_consumed, previous_reading=sum_units_consumed)
        else:
            flat_rate_name = FlatRateToRoom.objects.get(
                room_id=room_id).flat_rate_id.name
            energy_charges = bill.get('energy_charges')
            demand_charges = bill.get('demand_charges') if bill.get(
                'demand_charges') is not None else 0
            UnmeteredBill.objects.create(user_name=username, full_name=full_name, email=email, user_department=user_department, opening_balance=opening_balance, room_number=room_number, quarter_type=quarter_type,
                                         sanctioned_load=sanctioned_load, flat_rate_name=flat_rate_name, energy_charges=energy_charges, demand_charges=demand_charges, month=month, year=year, due_date=due_date, issued_date=issue_date)
    except Exception as e:
        print(e)


def fetch_bulk_bills(month, year, due_date, issue_date):
    rooms = UsersToRoom.objects.all().values_list('room_id', flat=True)
    for room in rooms:
        get_bill(room, month, year, due_date, issue_date)


def fetch_single_bill(month, year, room_number, quarter_type, due_date, issue_date):
    quarter_type_obj = QuarterType.objects.get(quarter_name=quarter_type)
    quarter_type_id = quarter_type_obj.quarter_id
    room_id = Room.objects.get(
        room_number=room_number, quarter_type_id=quarter_type_id).room_id
    get_bill(room_id, month, year, due_date, issue_date)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def fetchBill_page(request):
    context = {}
    try:
        quarterType_data = QuarterType.objects.all()
        context = {
            'segment': 'fetchBill',
            'quarterType': quarterType_data,
        }
        load_template = 'fetch_bill.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


# renders create Room page
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def readBills_page(request):
    context = {}
    # try:
    meteredBill_data = MeteredBill.objects.all()
    unmeteredBill_data = UnmeteredBill.objects.all()
    quarterType_data = QuarterType.objects.all()
    rooms = Room.objects.all()
    context = {
        "segment": "readBill",
        'meteredBill': meteredBill_data,
        'unmeteredBill': unmeteredBill_data,
        'quarterType': quarterType_data,
        'rooms': rooms,


    }
    load_template = 'read_bills.html'
    html_template = loader.get_template('home/' + load_template)
    return HttpResponse(html_template.render(context, request))

#    except template.TemplateDoesNotExist:
#        html_template = loader.get_template('home/page-404.html')
#        return HttpResponse(html_template.render(context, request))
#
#    except:
#        html_template = loader.get_template('home/page-500.html')
#        return HttpResponse(html_template.render(context, request))
#

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def read_rooms(request, msg=None):  # also pass id
    context = {}
    try:
        rooms = Room.objects.all()
        quarterType_data = QuarterType.objects.all()
        context = {
            'segment': 'readRooms',
            'rooms': rooms,
            'quarterType': quarterType_data,
        }
        if msg:
            arr = ast.literal_eval(msg)
            context[arr[0]] = arr[1]
        for room in rooms:
            if room.is_metered:
                meter_rate_to_room = MeterRateToRoom.objects.filter(
                    room_id=room).first()
                if meter_rate_to_room:
                    room.meter_rate_name = meter_rate_to_room.meter_rate_id.name
            else:
                flat_rate_to_room = FlatRateToRoom.objects.filter(
                    room_id=room).first()
                if flat_rate_to_room:
                    room.flat_rate_name = flat_rate_to_room.flat_rate_id.name

            room.quarter_type_name = room.quarter_type_id.quarter_name
    except Exception as e:
        messages.error(request, f"Error while getting room: {str(e)}")
    return render(request, 'home/read_rooms.html', context)

# renders create Room page

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def createRoom_page(request, message=None):
    context = {}
    try:
        quarterType_data = QuarterType.objects.all()
        meterRate_data = MeterRate.objects.all()
        flatRate_data = FlatRate.objects.all()
        context = {
            'segment': 'createRoom',
            'quarterType': quarterType_data,
            'meterRate': meterRate_data,
            'flatRate': flatRate_data,
        }
        if message is not None:
            context[message[0]] = message[1]
        load_template = 'create_room.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# renders Set Readings Page

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def setReadings_page(request, message=None):
    context = {}
    try:
        quarterType_data = QuarterType.objects.all()
        context = {
            'segment': 'setReadings',
            'quarterType': quarterType_data,
        }
        if message is not None:
            context[message[0]] = message[1]
        load_template = 'set_readings.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# download bills


@login_required(login_url='login.html')
@csrf_protect
def metered_bill_page(request, bill_id):
        metered_bill = MeteredBill.objects.filter(metered_bill_id=bill_id).exists()
        context = {}
        if metered_bill:
            context = {"bill_type": "Metered",
                    "bill": MeteredBill.objects.get(metered_bill_id=bill_id)}

        try:
            load_template = 'bill.html'
            html_template = loader.get_template('home/' + load_template)
            return HttpResponse(html_template.render(context, request))

        except template.TemplateDoesNotExist:
            html_template = loader.get_template('home/page-404.html')
            return HttpResponse(html_template.render(context, request))

        except:
            html_template = loader.get_template('home/page-500.html')
            return HttpResponse(html_template.render(context, request))


@login_required(login_url='login.html')
@csrf_protect
def unmetered_bill_page(request, bill_id):

        unmetered_bill = UnmeteredBill.objects.filter(
            unmetered_bill_id=bill_id).exists()
        context = {}
        if unmetered_bill:
            context = {"bill_type": "Unmetered",
                    "bill": UnmeteredBill.objects.get(unmetered_bill_id=bill_id)}
        try:
            load_template = 'bill.html'
            html_template = loader.get_template('home/' + load_template)
            return HttpResponse(html_template.render(context, request))

        except template.TemplateDoesNotExist:
            html_template = loader.get_template('home/page-404.html')
            return HttpResponse(html_template.render(context, request))

        except:
            html_template = loader.get_template('home/page-500.html')
            return HttpResponse(html_template.render(context, request))

# renders create meter rate page
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def createMeterRate_page(request):
    if request.method == "POST":
        try:
            req = request.POST
            rate_name = req.get('rate_name')
            fixed_charges = req.get('fixed_charges')
            electricity_duty = req.get('electricity_duty')
            unit_range = []
            i = 0
            while True:
                rate = req.get(f'rate_{i}')
                upto = req.get(f'to_{i}')
                try:
                    rate = float(rate)
                    try:
                        upto = float(upto)
                    except (TypeError, ValueError):
                        unit_range.append((None, rate))
                        break
                    unit_range.append((upto, rate))
                    i += 1
                except (TypeError, ValueError):
                    return HttpResponse('Unknown Error!')
        except (TypeError, ValueError):
            return HttpResponse('Unknown Error!')

        with transaction.atomic():
            meter_rate = MeterRate.objects.create(
                name=rate_name, fixed_charges=fixed_charges, electricity_duty=electricity_duty)
            for upto, rate in unit_range:
                if upto == None:
                    upto = -1
                MeterRateRange.objects.create(
                    upto=upto, rate=rate, meter_rate=meter_rate)

        return redirect(reverse('create_meter_rate'))

    context = {'segment': 'createMeterRate'}
    try:
        load_template = 'create_meter_rate.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


# renders create flat rate page
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def createFlatRate_page(request):
    if request.method == "POST":
        try:
            req = request.POST
            rate_name = req.get('rate_name')
            load_range = []
            i = 0
            while True:
                rate = req.get(f'rate_{i}')
                additional = req.get(f'additional_{i}')
                upto = req.get(f'to_{i}')
                try:
                    rate = float(rate)
                    if additional:
                        every_additional = req.get(f'every_additional_{i}')
                        additional_rate = req.get(f'additional_rate_{i}')
                        try:
                            every_additional = float(every_additional)
                            additional_rate = float(additional_rate)
                            additional_params = (
                                every_additional, additional_rate)
                        except (TypeError, ValueError):
                            return HttpResponse('Unknown Error!')
                    else:
                        additional_params = (None, None)
                    try:
                        upto = float(upto)
                    except (TypeError, ValueError):
                        load_range.append((None, rate, additional_params))
                        break
                    load_range.append((upto, rate, additional_params))
                    i += 1
                except (TypeError, ValueError):
                    return HttpResponse('Unknown Error!')
        except (TypeError, ValueError):
            return HttpResponse('Unknown Error!')

        with transaction.atomic():
            flat_rate = FlatRate.objects.create(name=rate_name)
            for upto, rate, (every_additional, additional_rate) in load_range:
                if upto == None:
                    upto = -1
                flat_rate_range = FlatRateRange.objects.create(
                    upto=upto, rate=rate, flat_rate=flat_rate)
                if every_additional and additional_rate:
                    FlatRateAdditional.objects.create(
                        additional=every_additional, rate=additional_rate, flat_rate_range=flat_rate_range)

        return redirect(reverse('create_flat_rate'))

    context = {'segment': 'createFlatRate'}
    try:
        load_template = 'create_flat_rate.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


# renders read rates page
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def read_rates(request):
    if request.method == "POST":
        try:
            req = request.POST
            post_action = req.get('action')
            post_id = int(req.get('id'))
            if post_action == 'mr-delete':
                instance = MeterRate.objects.get(id=post_id)
                mrtr = MeterRateToRoom.objects.filter(meter_rate_id=instance.id)
                if mrtr.exists():
                    return HttpResponse('Error: Rooms with this Meter Rate exist!')
                instance.delete()
            elif post_action == 'fr-delete':
                instance = FlatRate.objects.get(id=post_id)
                frtr = FlatRateToRoom.objects.filter(flat_rate_id=instance.id)
                if frtr.exists():
                    return HttpResponse('Error: Rooms with this Flat Rate exist!')
                instance.delete()
            else:
                return HttpResponse('Unknown Error!')
        except:
            return HttpResponse('Unknown Error!')

        return redirect(reverse('read_rates'))

    context = {'segment': 'readRates'}
    try:
        load_template = 'read_rates.html'
        html_template = loader.get_template('home/' + load_template)

        meter_rates = MeterRate.objects.all()
        meter_rates_objs = []
        for meter_rate in meter_rates:
            obj = {}
            obj['id'] = meter_rate.id
            obj['name'] = meter_rate.name
            obj['fixed_charges'] = meter_rate.fixed_charges
            obj['electricity_duty'] = meter_rate.electricity_duty
            obj['rates'] = []
            prev = 0
            for rate in meter_rate.unit_range():
                rate_obj = {}
                rate_obj['id'] = rate.id
                rate_obj['from'] = prev
                if rate.upto == -1:
                    rate_obj['to'] = 'Max'
                else:
                    rate_obj['to'] = rate.upto
                    prev = rate.upto
                rate_obj['rate'] = rate.rate
                obj['rates'].append(rate_obj)
            meter_rates_objs.append(obj)
        context['meter_rates'] = meter_rates_objs

        flat_rates = FlatRate.objects.all()
        flat_rates_objs = []
        for flat_rate in flat_rates:
            obj = {}
            obj['id'] = flat_rate.id
            obj['name'] = flat_rate.name
            obj['rates'] = []
            prev = 0
            for rate in flat_rate.load_range():
                rate_obj = {}
                rate_obj['id'] = rate.id
                rate_obj['from'] = prev
                if rate.upto == -1:
                    rate_obj['to'] = 'Max'
                else:
                    rate_obj['to'] = rate.upto
                    prev = rate.upto
                rate_obj['rate'] = rate.rate
                additional = rate.additional()
                if additional:
                    rate_obj['additional'] = additional.additional
                    rate_obj['additional_rate'] = additional.rate
                else:
                    rate_obj['additional'] = 'NA'
                    rate_obj['additional_rate'] = 'NA'
                obj['rates'].append(rate_obj)
            flat_rates_objs.append(obj)
        context['flat_rates'] = flat_rates_objs

        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))


# renders user profile page
@login_required(login_url='login.html')
@csrf_protect
def userProfile_page(request):
    context = {'segment': 'user'}
    try:
        load_template = 'user.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# renders tableList page

@login_required(login_url='login.html')
@csrf_protect
def tableList_page(request):
    context = {'segment': 'tables'}
    try:
        load_template = 'tables.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# renders typography page

@login_required(login_url='login.html')
@csrf_protect
def typography_page(request):
    context = {'segment': 'typography'}
    try:
        load_template = 'typography.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

# reders rtl support sidebar

@login_required(login_url='login.html')
@csrf_protect
def rtlSupport_page(request):
    context = {}
    try:
        load_template = 'rtl.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def updateRoom_page(request, room_id):
    context = {}
    try:
        room = Room.objects.get(pk=room_id)
        quarterType_data = QuarterType.objects.all()
        meterRate_data = MeterRate.objects.all()
        flatRate_data = FlatRate.objects.all()
        context = {
            'room': room,
            'quarterType': quarterType_data,
            'meterRate': meterRate_data,
            'flatRate': flatRate_data,
        }

        if room.is_metered:
            meter_to_room = MeterToRoom.objects.filter(
                room_id=room).first()
            if meter_to_room:
                room.initial_reading = meter_to_room.meter_id.initial_reading
            meter_rate_to_room = MeterRateToRoom.objects.filter(
                room_id=room).first()
            if meter_rate_to_room:
                room.meter_rate_name = meter_rate_to_room.meter_rate_id.name
        else:
            flat_rate_to_room = FlatRateToRoom.objects.filter(
                room_id=room).first()
            if flat_rate_to_room:
                room.flat_rate_name = flat_rate_to_room.flat_rate_id.name

        load_template = 'update_room.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))
    except Room.DoesNotExist:
        messages.error(request, "Room not found.")
        return redirect('read_rooms')

    except Exception as e:
        messages.error(request, f"Error while getting room: {str(e)}")
        return render(request, 'home/page-500.html', context)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def read_rooms(request, msg=None):  # also pass id
    context = {}
    try:
        rooms = Room.objects.all()
        quarterType_data = QuarterType.objects.all()
        context = {
            'segment': 'readRooms',
            'rooms': rooms,
            'quarterType': quarterType_data,
        }
        if msg:
            arr = ast.literal_eval(msg)
            context[arr[0]] = arr[1]
            msg = None
        for room in rooms:
            if room.is_metered:
                meter_rate_to_room = MeterRateToRoom.objects.filter(
                    room_id=room).first()
                if meter_rate_to_room:
                    room.meter_rate_name = meter_rate_to_room.meter_rate_id.name
            else:
                flat_rate_to_room = FlatRateToRoom.objects.filter(
                    room_id=room).first()
                if flat_rate_to_room:
                    room.flat_rate_name = flat_rate_to_room.flat_rate_id.name

            room.quarter_type_name = room.quarter_type_id.quarter_name
    except Exception as e:
        messages.error(request, f"Error while getting room: {str(e)}")
    return render(request, 'home/read_rooms.html', context)


# Bill Reading Details page
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def details_page(request):
    context = {}

    try:
        # Fetch all readings_data
        readings_data = Reading.objects.all()
        rooms = Room.objects.all()
        quarterType_data = QuarterType.objects.all()

        context = {
            'rooms': rooms,
            'quarterType': quarterType_data,
            'readings': readings_data,
            'segment': 'details',
            # 'room_data': room_data,  # Add the room_data to the context
        }

        # Fetch room_data using meter_id from readings_data
        room_data = {}
        quarterType_data = {}
        for reading in readings_data:
            meter_id = reading.meter_id
            reading_id = reading.reading_id
            if True:
                meter_to_room = MeterToRoom.objects.get(meter_id=meter_id)
                if meter_to_room:
                    # Get the room associated with the meter
                    room = Room.objects.get(
                        room_id=meter_to_room.room_id.room_id)
                    if room:
                        room_data[reading_id] = {
                            'room_number': room.room_number,
                            'quarter_type': room.quarter_type_id.quarter_name,
                            'year': reading.year,
                            'month': reading.month,
                            'units': reading.units_consumed,

                        }

                context['room_data'] = room_data

            try:
                pass
            except MeterToRoom.DoesNotExist:
                pass

    except Exception as e:
        messages.error(request, f"Error while getting room: {str(e)}")

    return render(request, 'home/details.html', context)

# crud User

# renders add User page

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def addUser_page(request, message=None):
    quarterType_data = QuarterType.objects.all()
    department_data = Department.objects.all()

    # Create a dictionary to store rooms by quarter type
    quarter_rooms = {}
    for quarter_type in quarterType_data:
        # Get rooms associated with the current quarter type
        rooms = Room.objects.filter(quarter_type_id=quarter_type.quarter_id)
        quarter_rooms[quarter_type.quarter_name] = rooms

    context = {
        'segment': 'addUser',
        'quarterType': quarterType_data,
        'departmentType': department_data,
        'quarterRooms': quarter_rooms,  # Pass the quarter_rooms dictionary to the template
    }

    if message is not None:
        context[message[0]] = message[1]

    load_template = 'add_user.html'
    html_template = loader.get_template('home/' + load_template)
    return HttpResponse(html_template.render(context, request))

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def add_user(request):
    password=""
    msg = []
    try:
        with transaction.atomic():
            username = request.POST.get('username')
            email = request.POST.get('email')
            fullname = request.POST.get('fullname')
            department = request.POST.get('department_name')
            room_no = request.POST.get('room_id')
            quarter_name = request.POST.get('id_access')
            usertype = request.POST.get('user_type')
            if not (username and email and fullname and department and room_no and quarter_name and usertype):

                messages.error(request, "User Details Missing.")
                msg = ['error_message', "User Details Missing."]
                return addUser_page(request, message=msg)

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username Already Exists.")
                msg = ['error_message', "Username Already Exists."]
                return addUser_page(request, message=msg)


            if UserDetails.objects.filter(email=email).exists():
                messages.error(request, "User Email Exists.")
                msg = ['error_message', "User Email Exists."]
                return addUser_page(request, message=msg)
            django_user = User.objects.create_user(
                username=username, email=email)
            random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
            password=username+random_chars
            django_user.set_password(password)
            django_user.save()
            
            group_name = 'user'
            group, _ = Group.objects.get_or_create(name=group_name)
            django_user.groups.add(group)
            db_user = UserDetails.objects.create(
                email=email, full_name=fullname, user_type=usertype, django_user=django_user)

            department_id = get_object_or_404(
                Department, department_name=department)
            user_id = get_object_or_404(
                UserDetails, email=email)

            db_usertodepartment = UsersToDepartment.objects.create(
                user_id=user_id, department_id=department_id)
            if int(room_no) > 0 and not Room.objects.filter(room_number=room_no, quarter_type_id=get_object_or_404(QuarterType, quarter_name=quarter_name)).exists():
                messages.error(request, "Room Does Not Exist")
                msg = ['error_message', "Room does not exist"]
                return addUser_page(request, message=msg)

            if not quarter_name == 'select_quarter' and not room_no == -1:
                quarter_id = get_object_or_404(
                    QuarterType, quarter_name=quarter_name)
                room_id = get_object_or_404(
                    Room, room_number=room_no, quarter_type_id=quarter_id)
                room = Room.objects.get(
                    room_number=room_no, quarter_type_id=quarter_id)
                if UsersToRoom.objects.exclude(user_id=user_id).filter(room_id=room.room_id).exists():
                    messages.error(request, "Room Already Allotted.")
                    msg = ['error_message', "Room Already Allotted."]
                    return addUser_page(request, message=msg)
                db_usertoroom = UsersToRoom.objects.create(
                    user_id=user_id, room_id=room_id)
            
            subject="Account Creation Billing System"
            message = f"Hello {fullname},\n\nYour account with username '{username}' has been created successfully."
            message += f"\nYour temporary password is: {password}"

            send_mail(subject,message,EMAIL_HOST_USER,[email])
            messages.success(request, "User created successfully.")
            msg = ['success_message', "User created successfully."]
    except Exception as e:
        messages.error(request, f"Error while creating user: {str(e)}")
        msg = ['error_message', "Error while creating user"]
    
    return addUser_page(request, message=msg)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
def read_users(request, msg=None):
    context = {}
    try:
        users = UserDetails.objects.all()
        context = {
            'segment': 'readUsers',
            'users': users,
        }
        if msg:
            context[msg[0]] = msg[1]
    except Exception as e:
        messages.error(request, f"Error while getting users: {str(e)}")
    return render(request, 'home/read_users.html', context)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def updateUser_page(request, user_id):
    context = {}
    try:
        user = UserDetails.objects.get(pk=user_id)
        user_auth = user.django_user
        
        try:
            users_to_room = UsersToRoom.objects.get(user_id=user_id)
            room_number = users_to_room.room_id.room_number
            quarter_name = users_to_room.room_id.quarter_type_id.quarter_name
        except UsersToRoom.DoesNotExist:
            room_number = None
            quarter_name = None

        # Check if user has a department and get the department name if available
        try:
            users_to_department = UsersToDepartment.objects.get(
                user_id=user_id)
            department_name = users_to_department.department_id.department_name
        except UsersToDepartment.DoesNotExist:
            department_name = None

        quarterType_data = QuarterType.objects.all()
        department_data = Department.objects.all()
        quarter_rooms = {}
        for quarter_type in quarterType_data:
            # Get rooms associated with the current quarter type
            rooms = Room.objects.filter(
                quarter_type_id=quarter_type.quarter_id)
            quarter_rooms[quarter_type.quarter_name] = rooms

        context = {
            'user': user,
            'user_auth':user_auth,
            'room_number': room_number,
            'department_name': department_name,
            'quarter_name': quarter_name,
            'quarterType': quarterType_data,
            'departmentType': department_data,
            'quarterRooms': quarter_rooms,
        }

        load_template = 'update_user.html'
        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except UserDetails.DoesNotExist:
        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except Exception as e:
        messages.error(request, f"Error while getting user details: {str(e)}")
        return render(request, 'home/page-500.html', context)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
@transaction.atomic
def update_user(request):
    msg = []
    try:
        user_id = request.POST.get('user_id')
        user_db = UserDetails.objects.get(pk=int(user_id))
        
        # Get the data from the POST request
        username = request.POST.get('username')
        email = request.POST.get('email')
        full_name = request.POST.get('full_name')
        user_type = request.POST.get('user_type')
        balance = float(request.POST.get('balance', 0))
        department_name = request.POST.get('department_name')

        # Perform basic validation checks
        if not username or not email or not full_name or not user_type:
            messages.error(request, "User Details Missing.")
            msg = ['error_message', "User Details Missing."]
            return read_users(request, msg=msg)
        
        if User.objects.filter(username=username).exists():
            existing_user = User.objects.get(username=username)
            if existing_user.pk != user_db.django_user.pk:
                messages.error(request, "Username Already Exists.")
                msg = ['error_message', "Username Already Exists."]
                return read_users(request, msg=msg)

        if UserDetails.objects.filter(email=email).exists():
            existing_user = UserDetails.objects.get(email=email)
            if existing_user.pk != int(user_id):
                messages.error(request, "User Email Exists.")
                msg = ['error_message', "User Email Exists."]
                return read_users(request, msg=msg)

        # Update the fields of the user object with the data from the form
        user_auth = user_db.django_user
        if user_auth:
            user_auth.username = username
            user_auth.save()
        # user_db.username = username
        user_db.email = email
        user_db.full_name = full_name
        user_db.user_type = user_type
        user_db.balance = balance
        user_db.save()

        # Update department details
        department_id = get_object_or_404(
            Department, department_name=department_name)
        department_db = UsersToDepartment.objects.get(user_id=int(user_id))
        department_db.department_id = department_id
        department_db.save()

        quarter_name = request.POST.get('id_access')
        room_number = request.POST.get('room_id')
        user_to_room_id = UsersToRoom.objects.filter(user_id=user_db).first()
        if int(room_number) > 0 and not Room.objects.filter(room_number=room_number, quarter_type_id=get_object_or_404(QuarterType, quarter_name=quarter_name)).exists():
            messages.error(request, "Room Does Not Exist")
            msg = ['error_message', "Room does not exist"]
            return read_users(request, msg=msg)

        if not quarter_name == 'select_quarter' and not room_number == '-1':

            quarter_id = get_object_or_404(
                QuarterType, quarter_name=quarter_name)
            room_id = get_object_or_404(
                Room, room_number=room_number, quarter_type_id=quarter_id)
            existing_user_to_room = UsersToRoom.objects.filter(
                user_id=user_id).first()
            room = Room.objects.get(
                room_number=room_number, quarter_type_id=quarter_id)
            if existing_user_to_room and UsersToRoom.objects.exclude(user_id=user_id).filter(room_id=room.room_id).exists():
                messages.error(request, "Room Already Allotted.")
                msg = ['error_message', "Room Already Allotted."]
                return read_users(request, msg=msg)

            if user_to_room_id:
                user_to_room_id.room_id = room_id
                user_to_room_id.save()
            else:
                db_usertoroom = UsersToRoom.objects.create(
                    user_id=user_db, room_id=room_id)
        else:
            if user_to_room_id:
                user_to_room_id.delete()

        # If the update is successful, display a success message
        messages.success(request, "User updated successfully.")
        msg = ['success_message', "User updated successfully."]

    except Exception as e:
        # If there's an error during the update, display an error message
        messages.error(request, f"Error while updating user: {str(e)}")
        msg = ['error_message', "Error while updating user."]

    # After updating, redirect to the read_users view with the appropriate message
    return read_users(request, msg)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
@transaction.atomic
def delete_user(request, user_id):
    msg = []
    try:
        user = get_object_or_404(UserDetails, pk=user_id)

        if UsersToRoom.objects.filter(user_id=user_id).exists():
            user_to_room = get_object_or_404(UsersToRoom, user_id=user_id)
            user_to_room.delete()

        if UsersToDepartment.objects.filter(user_id=user_id).exists():
            user_to_department = get_object_or_404(UsersToDepartment, user_id=user_id)
            user_to_department.delete()

        user_fullname = user.full_name
        username = user.django_user.username
        email = user.email

        # Delete the actual Django User object
        user.django_user.delete()

        subject = "Account Deletion Billing System"
        message = f"Hello {user_fullname},\n\nYour account with username '{username}' has been deleted successfully from the Billing System."
        send_mail(subject,message,EMAIL_HOST_USER,[email])

        messages.success(request, "User Deleted successfully.")
        msg = ['success_message', "User Deleted successfully."]
    except UserDetails.DoesNotExist:
        messages.error(request, 'User not found.')
    except Exception as e:
        messages.error(request, str(e))
    return read_users(request, msg)



# to get createRoom form data

# @transaction.atomic
@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
def create_room(request):
    msg = []
    try:
        with transaction.atomic():
            quarter_type = request.POST.get('quarter_type')
            room_number = request.POST.get('room_number')
            room_type = request.POST.get('room_type')
            is_metered = True if room_type == 'metered' else False
            quarter_type_id = QuarterType.objects.get(
                quarter_name=quarter_type)
            sanctioned_load = request.POST.get('sanctioned_load')
            db_room = Room.objects.create(
                quarter_type_id=quarter_type_id, room_number=room_number, is_metered=is_metered, sanctioned_load=sanctioned_load)

            if is_metered:
                initial_reading = request.POST.get('initial_reading')
                meter_rate_name = request.POST.get('meter_rate')
                meter_rate_obj = MeterRate.objects.filter(name=meter_rate_name).first()
                db_meter = Meter.objects.create(
                    initial_reading=initial_reading)
                meter_to_room = MeterToRoom.objects.create(
                    meter_id=db_meter, room_id=db_room)

                meter_rate_to_room = MeterRateToRoom.objects.create(
                    meter_rate_id=meter_rate_obj, room_id=db_room)

            else:
                flat_rate_name = request.POST.get('flat_rate')
                flat_rate_obj = get_object_or_404(
                    FlatRate, name=flat_rate_name)
                flat_rate_to_room = FlatRateToRoom.objects.create(
                    flat_rate_id=flat_rate_obj, room_id=db_room)
            messages.success(request, "Room created successfully.")
            msg = ['success_message', "Room created successfully."]
    except Exception as e:
        print(e)
        messages.error(request, f"Error while creating room: {str(e)}")
        msg = ['error_message', "Error while creating room"]
    return createRoom_page(request, msg)

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin)
@transaction.atomic
def delete_room(request):
    if request.method == 'POST':
        try:
            room_id = request.POST.get('room_id')
            room = Room.objects.get(pk=room_id)
            if room.is_metered == True:
                db_meter_to_room = MeterToRoom.objects.get(room_id=room)
                db_meter = Meter.objects.get(
                    meter_id=db_meter_to_room.meter_id.meter_id)
                db_meter.delete()
            room.delete()
            return JsonResponse({'success': True})
        except Room.DoesNotExist:
            return JsonResponse({'error': 'Room not found.'})
        except Exception as e:
            return JsonResponse({'error': str(e)})
    else:
        # Handle GET requests, render the template with the list of rooms
        rooms = Room.objects.all()
        return render(request, 'your_template.html', {'rooms': rooms})

@login_required(login_url='login.html')
@csrf_protect
@transaction.atomic
@user_passes_test(is_admin)
def update_room(request):
    msg = []
    try:
        room_id = request.POST.get('room_id')
        room_db = Room.objects.get(room_id=int(room_id))
        room_db.room_number = request.POST.get('room_number')
        room_db.quarter_type_id = QuarterType.objects.get(
            quarter_name=request.POST.get('quarter_type'))
        room_db.sanctioned_load = request.POST.get('sanctioned_load')

        room_type = request.POST.get('room_type')
        is_metered = True if room_type == 'metered' else False
        db_is_metered = room_db.is_metered
        if is_metered:
            if room_db.is_metered:
                initial_reading = request.POST.get('initial_reading')
                db_meter_to_room = MeterToRoom.objects.get(room_id=room_db)
                db_meter = db_meter_to_room.meter_id
                db_meter.initial_reading = initial_reading
                meter_rate_name = request.POST.get('meter_rate')
                meter_rate_obj = MeterRate.objects.filter(name=meter_rate_name).first()
                db_meter_rate_to_room = MeterRateToRoom.objects.get(
                    room_id=room_db)
                db_meter_rate_to_room.meter_rate_id = meter_rate_obj
                db_meter_rate_to_room.save()
                room_db.save()
                db_meter.save()
            else:
                initial_reading = request.POST.get('initial_reading')
                meter_rate_name = request.POST.get('meter_rate')
                flat_rate_to_room = FlatRateToRoom.objects.get(room_id=room_db)
                flat_rate_to_room.delete()
                db_meter = Meter.objects.create(
                    initial_reading=initial_reading)
                meter_rate_obj = MeterRate.objects.get(
                    name=meter_rate_name)
                meter_to_room = MeterToRoom.objects.create(
                    meter_id=db_meter, room_id=room_db)
                meter_rate_to_room = MeterRateToRoom.objects.create(
                    meter_rate_id=meter_rate_obj, room_id=room_db)
                room_db.is_metered = True
                room_db.save()
        else:
            if room_db.is_metered == False:
                flat_rate_name = request.POST.get('flat_rate')
                flat_rate_obj = FlatRate.objects.get(
                    name=flat_rate_name)
                db_flat_rate_to_room = FlatRateToRoom.objects.get(
                    room_id=room_db)
                db_flat_rate_to_room.flat_rate_id = flat_rate_obj
                db_flat_rate_to_room.save()
                room_db.save()
            else:
                db_meter_rate_to_room = MeterRateToRoom.objects.get(
                    room_id=room_db)
                db_meter_to_room = MeterToRoom.objects.get(room_id=room_db)
                db_meter = db_meter_to_room.meter_id
                db_meter_rate_to_room.delete()
                db_meter_to_room.delete()
                db_meter.delete()
                room_db.is_metered = False

                flat_rate_name = request.POST.get('flat_rate')
                flat_rate_obj = FlatRate.objects.get(
                    name=flat_rate_name)
                flat_rate_to_room = FlatRateToRoom.objects.create(
                    flat_rate_id=flat_rate_obj, room_id=room_db)
                room_db.is_metered = False

                room_db.save()
        messages.success(request, "Room updated successfully.")
        msg = ['success_message', "Room updated successfully."]
    except Exception as e:
        messages.error(request, f"Error while updating room: {str(e)}")
        msg = ['error_message', "Error while updating room"]

    return redirect('read_rooms', msg=msg)

# update-readings

@login_required(login_url='login.html')
@csrf_protect
@user_passes_test(is_admin_or_operator)
@transaction.atomic
def update_readings(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        quarter_type = request.POST.get('quarter_type')
        selected_month_name = request.POST.get('selected_month')
        selected_year = int(request.POST.get('selected_year'))
        current_input_reading = float(request.POST.get('initial_reading'))

        # Month name to integer mapping
        month_name_to_number = {
            'January': 1,
            'February': 2,
            'March': 3,
            'April': 4,
            'May': 5,
            'June': 6,
            'July': 7,
            'August': 8,
            'September': 9,
            'October': 10,
            'November': 11,
            'December': 12,
        }

        # Convert month name to its corresponding integer
        selected_month = month_name_to_number.get(selected_month_name)
        quarter_type_instance = QuarterType.objects.get(quarter_name=quarter_type)
        room = Room.objects.get(quarter_type_id=quarter_type_instance, room_number=room_number)
        meter_to_room = MeterToRoom.objects.get(room_id=room)
        print(meter_to_room.meter_id.meter_id)
        meter_id = meter_to_room.meter_id.meter_id
        if meter_id is not None:
            try:
                meter = Meter.objects.get(meter_id=meter_id)
                room = Room.objects.get(
                    room_number=room_number, quarter_type_id__quarter_name=quarter_type)

                # Check if a reading already exists for the selected month-year combination
                reading_exists = Reading.objects.filter(
                    meter_id=meter,
                    month=selected_month,
                    year=selected_year,
                ).exists()

                if reading_exists:
                    return JsonResponse({'status': 'error', 'message': 'Reading already exists for the selected month and year.'})

                # Get the latest existing reading for this meter
                latest_reading = Reading.objects.filter(
                    meter_id=meter).order_by('-year', '-month').first()

                if latest_reading:
                    latest_year = latest_reading.year
                    latest_month = latest_reading.month

                    if selected_year < latest_year or (selected_year == latest_year and selected_month < latest_month):
                        return JsonResponse({'status': 'error', 'message': 'Cannot enter reading for a month earlier than the latest entry.'})

                # Get the actual initial reading associated with this meter
                actual_initial_reading = meter.initial_reading

                # Get the sum of all previous month readings associated with this meter
                previous_readings = Reading.objects.filter(
                    meter_id=meter.meter_id)
                if previous_readings.exists():
                    total_previous_units = previous_readings.aggregate(Sum('units_consumed'))[
                        'units_consumed__sum']
                else:
                    total_previous_units = 0

                # Calculate the new reading using the formula
                new_reading = current_input_reading - (actual_initial_reading + total_previous_units)

                if new_reading < 0:
                    return JsonResponse({'status': 'error', 'message': 'Invalid reading value. Please enter a valid value.'})

                # Save the new reading to the database
                db_user_to_room = UsersToRoom.objects.filter(room_id=room)
                if not db_user_to_room.exists():
                    return JsonResponse({'status': 'error', 'message': 'No user is assigned to this room. Please assign a user to this room before entering readings.'})

                reading = Reading.objects.create(
                    meter_id=meter,
                    month=selected_month,
                    year=selected_year,
                    units_consumed=new_reading
                )

                return JsonResponse({'status': 'success', 'message': 'Updated Reading Successfully!'})
            except Meter.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Meter with the given meter_id does not exist.'})
            except Room.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Room with the given room_number and quarter_type does not exist.'})
            except Exception as e:
                print(e)
                return JsonResponse({'status': 'error', 'message': 'An error occurred while saving the meter reading data. Please check the logs for more information.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Meter ID not found for the given quarter number and quarter type.'})

    return render(request, 'update_readings.html')


# render error pages if no other url is hit

def page_not_found(request):
    return render(request, 'home/page-404.html')


# * this is unreacheble code fix this
def server_error(request):
    return render(request, 'home/page-500.html')
