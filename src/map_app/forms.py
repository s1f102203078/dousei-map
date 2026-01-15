from django import forms
from .models import Property, MapGroup, Station

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'address', 'rent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 新宿駅前マンション'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 東京都新宿区西新宿1-1'}),
            'rent': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 12万円'}),
        }

class MapGroupForm(forms.ModelForm):
    class Meta:
        model = MapGroup
        fields = ['name', 'password']
        labels = {
            'name': '地図の名前（グループ名）',
            'password': '合言葉',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：佐藤・鈴木ペア'}),
            'password': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'パートナーと共有する合言葉'}),
        }

class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name'] # ユーザーに入力させるのは駅名だけ
        labels = {
            'name': '駅名',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例：新宿'}),
        }