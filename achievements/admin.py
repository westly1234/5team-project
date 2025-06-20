# achievements/admin.py
from django.contrib import admin
from .models import Achievement, UserAchievement

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'title_reward', 'codename')
    list_filter = ('category',)
    search_fields = ('name', 'description', 'codename')

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'awarded_at')
    list_filter = ('awarded_at',)
    search_fields = ('user__username', 'achievement__name')