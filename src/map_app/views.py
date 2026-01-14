from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache # <--- ★記憶するための道具
from .models import Property, Station
from .forms import PropertyForm
import folium
from geopy.geocoders import Nominatim
import time
import requests
import json

def map_view(request):
    # 初期位置（新宿あたり）
    m = folium.Map(location=[35.6909, 139.7005], zoom_start=13)
    
    # 登録されている全駅を取得（チェックボックス表示用）
    all_stations = Station.objects.all()
    
    # ユーザーがチェックした駅のIDリストを取得（例: ['1', '3']）
    # 何も選ばれていなければ空っぽ
    selected_ids = request.GET.getlist('stations')

    # APIキー（ここだけ貼り直してください！）
    API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQwOTZjMDE0OTBjZDQxMmViNzEyYTRhMTAwZjVjYjNjIiwiaCI6Im11cm11cjY0In0='

    # チェックされた駅の数だけループしてエリアを描画
    for station in all_stations:
        # この駅がチェックされているか？（文字列として比較）
        if str(station.id) in selected_ids:
            
            # --- ここからいつものAPIロジック ---
            cache_key = f'isochrone_station_{station.id}_15min' # IDごとにキャッシュを分ける
            area_data = cache.get(cache_key)

            if not area_data:
                print(f"🌍 {station.name} のデータをAPIに取りに行きます...")
                body = {
                    "locations": [[station.longitude, station.latitude]], # geopyと逆順注意
                    "range": [900], 
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
                        cache.set(cache_key, area_data, 86400)
                except Exception as e:
                    print(f"Error: {e}")

            # 描画（色は緑で統一し、重なると濃くなるようにOpacity調整）
            if area_data:
                folium.GeoJson(
                    area_data,
                    name=f'{station.name} 15分圏内',
                    style_function=lambda x: {
                        'fillColor': '#00ff00', 
                        'color': '#00ff00',
                        'weight': 1,
                        'fillOpacity': 0.15 # 重なると濃くなって綺麗です
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

    # テンプレートに渡すデータに「全駅」と「選択されたID」を追加
    context = {
        'map_data': m._repr_html_(),
        'all_stations': all_stations,
        'selected_ids': selected_ids
    }
    return render(request, 'map_app/index.html', context)

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