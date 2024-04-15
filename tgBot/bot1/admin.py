from django.contrib import admin
from django.db.models import Count
from bot1.models import *

@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ("name", "external_id", "last_activity")
    search_fields = ("external_id__startswith", "name")
    list_filter = ("is_superuser", )


class VideoInline(admin.TabularInline):
    model = Video
    extra = 0
    readonly_fields = ('season', 'number', 'video_id')
    ordering = ('season', 'number')

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    inlines = [VideoInline]
    list_display = ("id", 'name', 'count_videos', 'is_release')
    search_fields = ("name", "description")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_videos=Count('video'))
        return queryset

    def count_videos(self, obj):
        return obj.num_videos

    count_videos.short_description = 'Количество видео'
    count_videos.admin_order_field = 'num_videos'

#admin.site.register(Series, SeriesAdmin)
@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name_channel", "id_channel", "id_advertising")
    list_filter = ("id_advertising", "is_super_channel")
    search_fields = ("name_channel", "id_channel")

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("name", "series")
    list_filter = ("series", )
    search_fields = ("name", )

@admin.register(ServiceUsage)
class ServiceUsageAdmin(admin.ModelAdmin):
    list_display = ('date', 'count')

@admin.register(StatisticRef)
class StatisticRef(admin.ModelAdmin):
    list_display = ('name_code', 'user_sdded')
