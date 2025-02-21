from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Automobile, TemporaryPermission, Place, Gate, Traffic, SecurityAssignment


# Restrict Admin Panel Access to Superusers Only


# Custom User Admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "phone_number", "is_staff", "is_superuser")
    search_fields = ("username", "phone_number")
    list_filter = ("is_staff", "is_superuser")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("phone_number", "profile_image")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


# Automobile Admin
@admin.register(Automobile)
class AutomobileAdmin(admin.ModelAdmin):
    list_display = ("plate", "owner_username", "is_allways_permitted")
    search_fields = ("plate", "owner_username", "owner_first_name", "owner_last_name")
    list_filter = ("is_allways_permitted",)
    ordering = ("plate",)


# TemporaryPermission Admin
@admin.register(TemporaryPermission)
class TemporaryPermissionAdmin(admin.ModelAdmin):
    list_display = ("automobile", "from_time", "to_time", "granted_by")
    search_fields = ("automobile__plate", "granted_by__username")
    list_filter = ("from_time", "to_time")
    ordering = ("-from_time",)


# Place Admin
@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_assigned")
    search_fields = ("name",)
    list_filter = ("is_assigned",)
    ordering = ("name",)


# Gate Admin
@admin.register(Gate)
class GateAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "place", "permission_needed")
    search_fields = ("name", "place__name")
    list_filter = ("type", "permission_needed")
    ordering = ("name",)


# Traffic Admin
@admin.register(Traffic)
class TrafficAdmin(admin.ModelAdmin):
    list_display = ("automobile", "gate", "time", "permitted", "security_agent")
    search_fields = ("automobile__plate", "gate__name", "security_agent__username")
    list_filter = ("permitted", "time")
    ordering = ("-time",)


# Security Assignment Admin
@admin.register(SecurityAssignment)
class SecurityAssignmentAdmin(admin.ModelAdmin):
    list_display = ("security_agent", "place", "start_time", "end_time")
    search_fields = ("security_agent__username", "place__name")
    list_filter = ("start_time", "end_time")
    ordering = ("-start_time",)
