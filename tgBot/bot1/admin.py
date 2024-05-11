from django.contrib import admin
from django.db.models import Count
from django.core.cache import cache # Кэш
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

def make_released(modeladmin, request, queryset):
    """
    Действие, которое меняет значение поля `is_release` на True для выделенных объектов.
    """
    queryset.update(is_release=True)
make_released.short_description = 'Сделать доступными'

@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    inlines = [VideoInline]
    list_display = ('name',"id", 'count_videos', 'is_release')
    search_fields = ("name", "description")
    actions = [make_released]

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
    list_display = ("name", "series", 'season', 'number')
    list_filter = ("series", )
    search_fields = ("name", )

@admin.register(ServiceUsage)
class ServiceUsageAdmin(admin.ModelAdmin):
    list_display = ('date', 'count')

@admin.register(StatisticRef)
class StatisticRef(admin.ModelAdmin):
    list_display = ('name_code', 'user_sdded')

@admin.register(SeriesUsage)
class SeriesUsageAdmin(admin.ModelAdmin):
    list_display = ('series', 'date', 'count', )