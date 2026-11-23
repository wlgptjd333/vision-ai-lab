from django.conf import settings
from django.db import models

from apps.reviews.models import Review

User = settings.AUTH_USER_MODEL


class ReviewLike(models.Model):
    """
    리뷰 좋아요
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "review")


class ReviewBookmark(models.Model):
    """
    리뷰 북마크
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)


class ReviewComment(models.Model):
    """
    리뷰 댓글
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ReviewReport(models.Model):
    """
    리뷰 신고
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
