from django.db import models
from django.contrib.auth.models import User

# ---------------------------------------------------------
# 1. 地図グループ（カップルの部屋）
# ---------------------------------------------------------
class MapGroup(models.Model):
    name = models.CharField("グループ名（地図の名前）", max_length=100)
    password = models.CharField("合言葉", max_length=100) # 簡易的なパスワードとして使用

    def __str__(self):
        return self.name

# ---------------------------------------------------------
# 2. ユーザー拡張（ユーザーがどのグループに属しているか）
# ---------------------------------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    group = models.ForeignKey(MapGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')

    def __str__(self):
        return f"{self.user.username} ({self.group.name if self.group else '未所属'})"

# ---------------------------------------------------------
# 3. 駅データ（グループに紐づく）
# ---------------------------------------------------------
class Station(models.Model):
    # ★どのグループの駅かを記録する
    group = models.ForeignKey(MapGroup, on_delete=models.CASCADE, related_name='stations')
    
    name = models.CharField("駅名", max_length=100)
    latitude = models.FloatField("緯度")
    longitude = models.FloatField("経度")

    def __str__(self):
        return f"{self.name} ({self.group.name})"

# ---------------------------------------------------------
# 4. 物件データ（グループに紐づく）
# ---------------------------------------------------------
class Property(models.Model):
    # ★どのグループの物件かを記録する
    group = models.ForeignKey(MapGroup, on_delete=models.CASCADE, related_name='properties')

    name = models.CharField("物件名", max_length=255)
    rent = models.CharField("家賃", max_length=100)
    address = models.CharField("住所", max_length=255)
    latitude = models.FloatField("緯度", null=True, blank=True)
    longitude = models.FloatField("経度", null=True, blank=True)
    
    # URLなど詳細情報は今回は省略（必要なら追加）
    
    likes = models.ManyToManyField(User, related_name='liked_properties', blank=True)

    def is_matched(self):
        """
        この物件を、グループ内の2人ともが「いいね」しているか判定するロジック
        """
        if not self.group:
            return False
            
        # この物件の属するグループのメンバーを取得
        members = self.group.members.all()
        member_count = members.count()
        
        # メンバーが2人以上で、かつ全員がいいねしている場合のみマッチング成立
        # (今は簡易的に「いいね数が2以上ならOK」とする)
        if member_count >= 2 and self.likes.count() >= 2:
            return True
        return False

    def __str__(self):
        return self.name