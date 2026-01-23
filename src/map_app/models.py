from django.db import models
from django.contrib.auth.models import User

# ---------------------------------------------------------
# 1. 路線（Line）と 駅（Station）のマスターデータ
#    ※これらはユーザーが登録するのではなく、管理者が用意するデータ
# ---------------------------------------------------------

class Line(models.Model):
    name = models.CharField("路線名", max_length=100)
    sort_order = models.IntegerField("並び順", default=0)

    def __str__(self):
        return self.name

class Station(models.Model):
    line = models.ForeignKey(Line, on_delete=models.CASCADE, related_name='stations')
    name = models.CharField("駅名", max_length=100)
    latitude = models.FloatField("緯度")
    longitude = models.FloatField("経度")
    sort_order = models.IntegerField("並び順", default=0)

    def __str__(self):
        return f"{self.name} ({self.line.name})"

# ---------------------------------------------------------
# 2. 地図グループ（MapGroup）
# ---------------------------------------------------------

class MapGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    
    # ★変更点：グループが「選んだ駅」をここで管理する
    # ManyToManyField = 多対多の関係（1つのグループは複数の駅を選べる）
    selected_stations = models.ManyToManyField(Station, blank=True, related_name='selected_by_groups')

    def __str__(self):
        return self.name

# ---------------------------------------------------------
# 3. ユーザープロフィール（UserProfile）
# ---------------------------------------------------------

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    group = models.ForeignKey(MapGroup, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

# ---------------------------------------------------------
# 4. 物件データ（Property）
# ---------------------------------------------------------

class Property(models.Model):
    group = models.ForeignKey(MapGroup, on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    rent = models.CharField(max_length=50)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_properties', blank=True)

    def is_matched(self):
        if self.group:
            # グループに所属する全ユーザー数を取得
            member_count = UserProfile.objects.filter(group=self.group).count()
            # いいねした人数と比較
            return self.likes.count() >= member_count and member_count > 0
        return False

    def __str__(self):
        return self.name