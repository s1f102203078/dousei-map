from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Property
from .forms import PropertyForm
import folium
from geopy.geocoders import Nominatim
import time

def map_view(request):
    m = folium.Map(location=[35.6909, 139.7005], zoom_start=13)
    properties = Property.objects.all()

    for prop in properties:
        icon_color = 'blue'
        icon_icon = 'home'
        
        if prop.is_matched():
            icon_color = 'red'
            icon_icon = 'heart'
        elif request.user.is_authenticated and request.user in prop.likes.all():
            icon_color = 'pink'
            icon_icon = 'heart'

        # いいねボタンのHTML作成
        like_btn_html = ""
        if request.user.is_authenticated:
            if request.user in prop.likes.all():
                text = "いいねを取り消す"
                btn_class = "btn-secondary"
            else:
                text = "❤️ いいね！"
                btn_class = "btn-danger"
            
            # ★修正ポイント: parent.toggleLike に書き換えました
            like_btn_html = f"""
                <div style="margin-top:10px; text-align:center;">
                    <a href="#" 
                       onclick="parent.toggleLike('/like/{prop.id}/'); return false;"
                       class="btn {btn_class} btn-sm" 
                       style="color:white; text-decoration:none;">
                        {text}
                    </a>
                </div>
            """

        html = f"""
        <div style="min-width: 200px;">
            <h6 style="margin-bottom:5px; font-weight:bold;">{prop.name}</h6>
            <div style="font-size:0.9em; color:gray;">{prop.rent}</div>
            <div style="font-size:0.8em;">{prop.address}</div>
            {like_btn_html}
        </div>
        """
        
        popup = folium.Popup(html, max_width=300)

        folium.Marker(
            location=[prop.latitude, prop.longitude],
            popup=popup,
            tooltip=prop.name,
            icon=folium.Icon(color=icon_color, icon=icon_icon, prefix='fa')
        ).add_to(m)

    m = m._repr_html_()
    return render(request, 'map_app/index.html', {'map_data': m})

def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            geolocator = Nominatim(user_agent="dousei_app_v1")
            try:
                location = geolocator.geocode(obj.address)
                if location:
                    obj.latitude = location.latitude
                    obj.longitude = location.longitude
                    obj.save()
                    # 登録時も同様に、シンプルにJSで戻るようにします（一番安全）
                    return HttpResponse('<script>window.location.href="/";</script>')
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(1)
    else:
        form = PropertyForm()
    return render(request, 'map_app/add_property.html', {'form': form})

def toggle_like(request, property_id):
    prop = get_object_or_404(Property, pk=property_id)
    if request.user.is_authenticated:
        if request.user in prop.likes.all():
            prop.likes.remove(request.user)
        else:
            prop.likes.add(request.user)
    
    # ★変更点: リダイレクトせず、ただ「OK」と返すだけ。
    # 画面の移動はブラウザ側のJavaScript（window.location.reload）が担当します。
    return HttpResponse("OK")