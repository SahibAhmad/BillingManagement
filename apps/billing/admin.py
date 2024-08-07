from django.contrib import admin
from .models import (UserDetails, Department, Meter, QuarterType, Room, UsersToDepartment, UsersToRoom, MeterToRoom,
                     MeterRateToRoom, FlatRateToRoom, Reading,
                     MeterRate, MeterRateRange, FlatRate, FlatRateRange, FlatRateAdditional, UnmeteredBill, MeteredBill)

admin.site.register(UserDetails)
admin.site.register(Department)
admin.site.register(Meter)
admin.site.register(QuarterType)
admin.site.register(Room)
admin.site.register(UsersToDepartment)
admin.site.register(UsersToRoom)
admin.site.register(MeterToRoom)
admin.site.register(MeterRateToRoom)
admin.site.register(FlatRateToRoom)
admin.site.register(Reading)

admin.site.register(MeterRate)
admin.site.register(MeterRateRange)
admin.site.register(FlatRate)
admin.site.register(FlatRateRange)
admin.site.register(FlatRateAdditional)

admin.site.register(UnmeteredBill)
admin.site.register(MeteredBill)

# Register your models here.
