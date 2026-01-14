from django.db import models
from django.contrib.auth.models import User

class Property(models.Model):
    name = models.CharField("物件名", max_length=100)
    address = models.CharField("住所", max_length=200)
    rent = models.CharField("家賃", max_length=50)
    latitude = models.FloatField("緯度")
    longitude = models.FloatField("経度")
    
    # ここが「いいね」機能！Userと多対多で繋ぎます
    likes = models.ManyToManyField(User, related_name='liked_properties', blank=True)

    def __str__(self):
        return self.name

    def is_matched(self):
        """2人以上がいいねしているかチェックする"""
        return self.likes.count() >= 2
    

class Station(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name