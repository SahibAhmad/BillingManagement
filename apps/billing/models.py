import datetime
from django.db import models
from django.apps import apps
from django.db.models import CheckConstraint
from django.db.models import Sum
from django.contrib.auth.models import User
import math

class UserDetails(models.Model):
    __tablename__ = "users"
    TYPE_IN_USER_CHOICES = [
            ('admin', 'Admin'),
            ('operator', 'Operator'),
            ('user', 'User'),
    ]
    TYPE_IN_USER_TYPE_CHOICES = [
        ('simple', 'Simple'),
        ('outsource', 'Outsource'),
    ]
    user_id = models.AutoField(primary_key=True)
    # username = models.CharField(max_length=255, null=False, unique=True)
    email = models.CharField(max_length=255, null=False,unique=True)
    # hashed_password = Column(String)
    full_name = models.CharField(max_length=255,null=False)
    access = models.CharField(max_length=255, default='user', choices=TYPE_IN_USER_CHOICES)
    user_type = models.CharField(max_length=255, default='simple', choices=TYPE_IN_USER_TYPE_CHOICES)
    balance = models.FloatField(default=0)
    disabled = models.BooleanField(null=False, default=False)
    django_user = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.email

class Department(models.Model):
    __tablename__ = "departments"

    department_id = models.AutoField(primary_key=True, db_index=True)
    department_name = models.CharField(max_length=255, null=False, unique=True)
    def __str__(self):
        return self.department_name


class Meter(models.Model):
    __tablename__ = "meters"

    meter_id = models.AutoField(primary_key=True)
    initial_reading = models.FloatField(null=False)
    def __str__(self):
        return str(self.meter_id)


class QuarterType(models.Model):
    __tablename__ = "quarter_types"

    quarter_id = models.AutoField(primary_key=True)
    quarter_name = models.CharField(max_length=255, null=False, unique=True)
    def __str__(self):
        return self.quarter_name


class Room(models.Model):
    __tablename__ = "rooms"

    room_id = models.AutoField(primary_key=True)
    quarter_type_id = models.ForeignKey(QuarterType, on_delete=models.CASCADE)
    room_number = models.IntegerField(null=False)
    is_metered = models.BooleanField(null=False)
    sanctioned_load = models.FloatField(null=False)
    
    class Meta:
        unique_together = ('quarter_type_id', 'room_number')

    def calculate_amount(self, year, month):
        room_id = self.room_id
        if self.is_metered:
            rate_id = MeterRateToRoom.objects.get(room_id=room_id).meter_rate_id
            rate = MeterRate.objects.get(id=rate_id.id)
            return rate.calculate_amount(room_id, year, month)
        else:
            rate_id = FlatRateToRoom.objects.get(room_id=room_id).flat_rate_id
            rate = FlatRate.objects.get(id=rate_id.id)
            return rate.calculate_amount(room_id)

    def __str__(self):
        return str(self.room_number)

class UsersToDepartment(models.Model):
    __tablename__ = "user_to_department"

    user_to_department_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(UserDetails, on_delete=models.CASCADE)
    department_id = models.ForeignKey(Department, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.user_to_department_id)

class UsersToRoom(models.Model):
    __tablename__ = "user_to_room"

    user_to_room_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(UserDetails,unique=True, on_delete=models.CASCADE)
    room_id = models.ForeignKey(Room,unique=True, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.user_to_room_id)


class MeterToRoom(models.Model):
    __tablename__ = "meter_to_room"

    meter_to_room_id = models.AutoField( primary_key=True)
    meter_id = models.ForeignKey(Meter, on_delete=models.CASCADE, unique=True)
    room_id = models.ForeignKey(Room, on_delete=models.CASCADE, unique=True)
    def __str__(self):
        return str(self.meter_to_room_id)



class MeterRate(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    fixed_charges = models.FloatField(null=False)
    electricity_duty = models.FloatField(null=False)

    def unit_range(self):
        RangeModel = apps.get_model('billing', 'MeterRateRange')
        result = RangeModel.objects.filter(meter_rate=self.id)
        result = result.order_by('upto')
        result = list(result)
        result.append(result[0])
        result.pop(0)
        return result

    def calculate_amount(self, room_id, year, month):
        result = {}
        room = Room.objects.get(room_id=room_id)
        meter_id = MeterToRoom.objects.get(room_id=room_id).meter_id
        reading = Reading.objects.get(meter_id=meter_id, year=year, month=month)

        sanctioned_load = room.sanctioned_load # billya ye kya ?
        units_consumed = reading.units_consumed

        amount = 0
        unit_range = self.unit_range()

        # Add unit price
        energy_cost = 0
        prev = 0
        for x in unit_range:
            if units_consumed <= x.upto or x.upto == -1:
                energy_cost += (units_consumed - prev) * x.rate
                break
            else:
                energy_cost += (x.upto - prev) * x.rate
                prev = x.upto
        amount += energy_cost

        # Add duty_charges
        duty_charges = energy_cost * (self.electricity_duty / 100)
        amount += duty_charges

        # Add fixed charges
        # fixed_charges = int(self.fixed_charges) # str ?
        # amount += fixed_charges

        # Add demand charges
        demand_charges = float(self.fixed_charges) * (sanctioned_load)
        amount += demand_charges # why ?

        result['energy_cost'] = energy_cost
        result['duty_charges'] = duty_charges
        # result['fixed_charges'] = fixed_charges
        result['demand_charges'] = demand_charges
        result['total'] = amount
        return result

    def __str__(self):
        return self.name

class MeterRateRange(models.Model):
    id = models.AutoField(primary_key=True)
    upto = models.FloatField(null=False)
    rate = models.FloatField(null=False)
    meter_rate = models.ForeignKey('MeterRate', on_delete=models.CASCADE)



class FlatRate(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)

    def load_range(self):
        RangeModel = apps.get_model('billing', 'FlatRateRange')
        result = RangeModel.objects.filter(flat_rate=self.id)
        result = result.order_by('upto')
        result = list(result)
        result.append(result[0])
        result.pop(0)
        return result

    def calculate_amount(self, room_id):
        result = {}
        room = Room.objects.get(room_id=room_id)

        sanctioned_load = room.sanctioned_load

        amount = 0
        load_range = self.load_range()

        prev = 0
        # Find range
        energy_charges = 0
        for x in load_range:
            if sanctioned_load <= x.upto or x.upto == -1:
                energy_charges = x.rate
                # Add additional
                additional = x.additional()
                if additional:
                    energy_charges += math.ceil((sanctioned_load - prev) / additional.additional) * additional.rate
                break
            else:
                prev = x.upto
        amount += energy_charges

        result['energy_charges'] = energy_charges
        result['total'] = amount

        return result

    def __str__(self):
        return self.name

class FlatRateRange(models.Model):
    id = models.AutoField(primary_key=True)
    upto = models.FloatField(null=False)
    rate = models.FloatField(null=False)
    flat_rate = models.ForeignKey('FlatRate', on_delete=models.CASCADE)

    def additional(self):
        AdditionalModel = apps.get_model('billing', 'FlatRateAdditional')
        result = AdditionalModel.objects.filter(flat_rate_range=self.id)
        if result.exists():
            return result.first()
        return None

class FlatRateAdditional(models.Model):
    id = models.AutoField(primary_key=True)
    additional = models.FloatField(null=False)
    rate = models.FloatField(null=False)
    flat_rate_range = models.ForeignKey('FlatRateRange', on_delete=models.CASCADE)


class MeterRateToRoom(models.Model):
    __tablename__ = "meter_rate_to_room"

    meter_rate_to_room_id = models.AutoField(primary_key=True)
    meter_rate_id = models.ForeignKey(MeterRate, on_delete=models.CASCADE)
    room_id = models.ForeignKey(Room, on_delete=models.CASCADE, unique=True)


class FlatRateToRoom(models.Model):
    __tablename__ = "flat_rate_to_room"

    flat_rate_to_room_id = models.AutoField(primary_key=True)
    flat_rate_id = models.ForeignKey(FlatRate, on_delete=models.CASCADE)
    room_id = models.ForeignKey(Room, on_delete=models.CASCADE, unique=True)


class Reading(models.Model):
    __tablename__ = "readings"

    reading_id = models.AutoField(primary_key=True)
    meter_id = models.ForeignKey(Meter, on_delete=models.CASCADE)
    month = models.IntegerField(null=False)
    year = models.IntegerField(null=False)
    units_consumed = models.FloatField(null=False)
    locked = models.BooleanField(default=False)
    class Meta:
        constraints = [
            CheckConstraint(check=models.Q(month__gte=1, month__lte=12), name='check_month_reading'),
            CheckConstraint(check=models.Q(units_consumed__gte=0), name='check_units_consumed'),
        ]
    
class MeteredBill(models.Model):
    __tablename__ = "metered_bills"

    metered_bill_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=255, null=False)
    full_name = models.CharField(max_length=255, null=False)
    email = models.CharField(max_length=255, null=False)
    user_department = models.CharField(max_length=255, null=False)
    opening_balance = models.FloatField(null=False) # unpaid bills
    
    room_number = models.IntegerField(null=False)
    quarter_type = models.CharField(max_length=255, null=False)
    sanctioned_load = models.FloatField(null=False)

    issued_date = models.DateField(null=False )
    due_date = models.DateField(null=False)
    
    units_consumed = models.FloatField(null=False)
    previous_reading = models.FloatField(null=False)
    current_reading = models.FloatField(null=False)
    meter_rate_name = models.CharField(max_length=255, null=False)
    energy_charges = models.FloatField(null=False)
    demand_charges = models.FloatField(null=False)
    duty_charges = models.FloatField(null=False)
    month = models.IntegerField(null=False)
    year = models.IntegerField(null=False)
    total_bill = models.FloatField(null=False)
    
    def save(self, *args, **kwargs):
        self.total_bill = self.energy_charges + self.demand_charges + self.duty_charges + self.opening_balance
        super(MeteredBill, self).save(*args, **kwargs)
    class Meta:
        constraints = [
            CheckConstraint(check=models.Q(month__gte=1, month__lte=12), name='check_month_metered_bill'),
            CheckConstraint(check=models.Q(year__gt=0), name='check_year_metered_bill'),
        ]
        unique_together = ('room_number', 'quarter_type', 'month', 'year')

class UnmeteredBill(models.Model):
    __tablename__ = "unmetered_bills"

    unmetered_bill_id = models.AutoField(primary_key=True)
    
    user_name = models.CharField(max_length=255, null=False)
    full_name = models.CharField(max_length=255, null=False)
    email = models.CharField(max_length=255, null=False)
    user_department = models.CharField(max_length=255, null=False)
    opening_balance = models.FloatField(null=False) # unpaid bills
    
    room_number = models.IntegerField(null=False)
    quarter_type = models.CharField(max_length=255, null=False)
    sanctioned_load = models.FloatField(null=False)

    issued_date = models.DateField(null=False)
    due_date = models.DateField(null=False)
    
    flat_rate_name = models.CharField(max_length=255, null=False)
    energy_charges = models.FloatField(null=False)
    demand_charges = models.FloatField(null=False)
    total_bill = models.FloatField(null=False)
    month = models.IntegerField(null=False)
    year = models.IntegerField(null=False)
    
    def save(self, *args, **kwargs):
        self.total_bill = self.energy_charges + self.demand_charges + self.opening_balance
        super(UnmeteredBill, self).save(*args, **kwargs)
    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(month__gte=1, month__lte=12), name='check_month_unmetered_bill'),
            models.CheckConstraint(check=models.Q(year__gt=0), name='check_year_unmetered_bill'),
        ]
    unique_together = ('room_number', 'quarter_type', 'month', 'year')