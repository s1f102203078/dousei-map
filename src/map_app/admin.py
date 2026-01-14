from django.contrib import admin
from .models import Property

# 管理画面に表示する設定
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'rent', 'match_status') # 一覧に出す項目
    
    # 2人ともいいねしているかを表示するカスタム項目
    def match_status(self, obj):
        if obj.is_matched():
            return "❤️ マッチング！"
        return f"いいね数: {obj.likes.count()}"
    match_status.short_description = "ステータス"

# 管理画面に登録
admin.site.register(Property, PropertyAdmin)