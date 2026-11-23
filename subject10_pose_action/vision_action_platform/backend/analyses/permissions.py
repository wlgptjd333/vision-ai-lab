from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """본인이 만든 분석 작업만 조회·수정·삭제. (목록은 views.get_queryset 에서 이미 본인 것만 거른다)"""

    message = "본인의 분석 기록만 볼 수 있습니다."

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id
