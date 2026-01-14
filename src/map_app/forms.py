from django import forms
from .models import Property

class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = ['name', 'address', 'rent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 新宿駅前マンション'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 東京都新宿区西新宿1-1'}),
            'rent': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 12万円'}),
        }