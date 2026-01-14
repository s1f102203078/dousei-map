from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache # <--- ★記憶するための道具
from .models import Property
from .forms import PropertyForm
import folium
from geopy.geocoders import Nominatim
import time
import requests
import json

def map_view(request):
    m = folium.Map(location=[35.6909, 139.7005], zoom_start=13)
    
    # ---------------------------------------------------------
    # ★ OpenRouteService (徒歩圏エリア) の取得ロジック
    # ---------------------------------------------------------
    API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQwOTZjMDE0OTBjZDQxMmViNzEyYTRhMTAwZjVjYjNjIiwiaCI6Im11cm11cjY0In0=' 
    target_station = [139.7005, 35.6909] # 新宿駅
    
    # キャッシュのキー（名前）を決める
    cache_key = 'isochrone_shinjuku_15min'
    
    # ★ここが高速化の魔法！
    # 「まずは記憶(cache)を探して、なければAPIを叩いて記憶する」という命令
    area_data = cache.get(cache_key)

    if not area_data:
        # 記憶になかった場合だけ、APIを叩きに行く（重い処理）
        print("🌍 新しいデータをAPIに取りに行きます...")
        body = {
            "locations": [target_station],
            "range": [900], # 900秒 = 15分
            "range_type": "time",
            "attributes": ["area"],
            "area_units": "m"
        }
        headers = {
            "Accept": "application/json, application/geo+json",
            "Authorization": API_KEY,
            "Content-Type": "application/json; charset=utf-8"
        }
        try:
            call = requests.post(
                'https://api.openrouteservice.org/v2/isochrones/foot-walking',
                json=body,
                headers=headers
            )
            if call.status_code == 200:
                area_data = call.json()
                # 結果をキャッシュに保存（86400秒 = 24時間）
                cache.set(cache_key, area_data, 86400)
                print("💾 データをキャッシュに保存しました")
            else:
                print(f"API Error: {call.text}")
        except Exception as e:
            print(f"Connection Error: {e}")
    else:
        print("⚡ キャッシュからデータを読み込みました（爆速）")

    # データがあれば地図に描画
    if area_data:
        folium.GeoJson(
            area_data,
            name='徒歩15分圏内',
            style_function=lambda x: {
                'fillColor': '#00ff00', 
                'color': '#00ff00',
                'weight': 1,
                'fillOpacity': 0.15 # ちょっと薄くして見やすく
            }
        ).add_to(m)

    # ---------------------------------------------------------

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

        like_btn_html = ""
        if request.user.is_authenticated:
            if request.user in prop.likes.all():
                text = "いいねを取り消す"
                btn_class = "btn-secondary"
            else:
                text = "❤️ いいね！"
                btn_class = "btn-danger"
            
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

# 登録・いいね機能はそのまま
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
    return HttpResponse("OK")