from django.urls import path

from .views import MyRewardsView, RewardCreateView, RewardStatusView

urlpatterns = [
    path("", RewardCreateView.as_view(), name="reward-create"),
    path("/mine", MyRewardsView.as_view(), name="reward-mine"),
    path("/<uuid:pk>/status", RewardStatusView.as_view(), name="reward-status"),
]
