from rest_framework.filters import BaseFilterBackend

from .models import Traffic
from .serializers import JalaliDateTimeField
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured

from django_filters import rest_framework as filters


class JalaliDateTimeRangeFilter(BaseFilterBackend):
    """
    Filters a queryset by a Jalali date/time range using 'from' and 'until' query parameters.

    Expects the view to define a `date_time_field` attribute that names the model field to filter on.

    Query parameters:
      - **from**: Start of the date range (Jalali format, e.g., "YYYY/MM/DD-HH:MM:SS")
      - **until**: End of the date range (same format)

    If both parameters are provided, applies a range filter; if only one is provided, applies
    a greater-than or less-than filter accordingly. Raises ImproperlyConfigured if `date_time_field`
    is not set.
    """

    def filter_queryset(self, request, queryset, view):

        from_dt, until_dt = self.get_parsed_range_datetime(request)
        date_time_field = getattr(view, 'date_time_field', None)

        if date_time_field is None:
            raise ImproperlyConfigured("date_time_field should be specified in view for filtering")

        if (from_dt is not None) and (until_dt is not None):
            return queryset.filter(**{f'{date_time_field}__range': (from_dt, until_dt)})

        elif from_dt is not None:
            return queryset.filter(**{f'{date_time_field}__gte': from_dt})

        elif until_dt is not None:
            return queryset.filter(**{f'{date_time_field}__lte': until_dt})

        return queryset

    def get_parsed_range_datetime(self, request) -> tuple[timezone.datetime, timezone.datetime]:
        """
        Retrieves and validates the **from** and **until** date-time query parameters,
        converting them from a Jalali date string (with format in settings) to a UTC datetime object using the
        JalaliDateTimeField.

        :returns:
            A tuple of (from_datetime, until_datetime), where each is a timezone-aware
            datetime in UTC, or None if not provided.
        """

        jalali_dt_field = JalaliDateTimeField()

        from_dt = request.query_params.get('from', None)
        until_dt = request.query_params.get('until', None)

        validated_from_dt = jalali_dt_field.to_internal_value(from_dt)
        validated_until_dt = jalali_dt_field.to_internal_value(until_dt)

        return validated_from_dt, validated_until_dt


class TrafficFilterSet(filters.FilterSet):

    place = filters.CharFilter('gate__place__name', 'icontains')
    gate = filters.CharFilter('gate__name', 'icontains')
    security_agent = filters.CharFilter('security_agent__username', 'icontains')
    automobile = filters.CharFilter('automobile__plate', 'icontains')
    permitted = filters.BooleanFilter()
    automobile_owner = filters.CharFilter('automobile__owner_username', 'icontains')

    class Meta:
        model = Traffic
        fields = ['automobile', 'place', 'gate', 'security_agent', 'permitted', 'automobile_owner']
