from rest_framework.permissions import IsAdminUser as BaseAdminPermission


class IsManagerUser(BaseAdminPermission):

    # overwrite Permission class to check is admin instead of is_staff.
    def has_permission(self, request, view):
        """
        :return: ture if request.user exists and user.is_manager = true.
        """
        if not request.user.is_anonymous:
            return request.user.is_manager
        else:
            return False
