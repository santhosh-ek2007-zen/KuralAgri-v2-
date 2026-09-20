from rest_framework import permissions


class IsFarmer(permissions.BasePermission):
    """Allows access only to authenticated users with role FARMER."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'FARMER' or request.user.is_staff)
        )


class IsBuyer(permissions.BasePermission):
    """Allows access only to authenticated users with role BUYER."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'BUYER' or request.user.is_staff)
        )


class IsFPOAdmin(permissions.BasePermission):
    """Allows access only to authenticated users with role FPO_ADMIN."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'FPO_ADMIN' or request.user.is_staff)
        )


class IsPlatformAdmin(permissions.BasePermission):
    """Allows access only to superusers and platform administrators."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'ADMIN' or request.user.is_staff or request.user.is_superuser)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Object-level permission allowing only the owner or staff to modify."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'ADMIN':
            return True
        if hasattr(obj, 'farmer') and hasattr(obj.farmer, 'user'):
            return obj.farmer.user == request.user
        if hasattr(obj, 'buyer') and hasattr(obj.buyer, 'user'):
            return obj.buyer.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class ReadOnly(permissions.BasePermission):
    """Allows read-only access for safe HTTP methods."""
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
