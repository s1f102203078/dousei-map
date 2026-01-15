from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache
from .models import Property, Station, MapGroup, UserProfile
from .forms import PropertyForm, MapGroupForm, StationForm
from django.contrib.auth.decorators import login_required
import folium
from geopy.geocoders import Nominatim
import time
import requests
import json

# ---------------------------------------------------------
# グループ選択（玄関）
# ---------------------------------------------------------
@login_required
def group_setup(request):
    # すでにグループに参加済みなら、トップ（地図）へ飛ばす
    if hasattr(request.user, 'profile') and request.user.profile.group:
        return redirect('index')

    if request.method == 'POST':
        form = MapGroupForm(request.POST)
        action = request.POST.get('action') # 'create' か 'join' か

        if form.is_valid():
            name = form.cleaned_data['name']
            password = form.cleaned_data['password']

            if action == 'create':
                # 新規作成
                new_group = MapGroup.objects.create(name=name, password=password)
                # プロフィールを作って紐付ける
                UserProfile.objects.update_or_create(user=request.user, defaults={'group': new_group})
                return redirect('index')

            elif action == 'join':
                # 参加（合言葉の一致確認）
                try:
                    group = MapGroup.objects.get(name=name, password=password)
                    UserProfile.objects.update_or_create(user=request.user, defaults={'group': group})
                    return redirect('index')
                except MapGroup.DoesNotExist:
                    form.add_error(None, "地図の名前か合言葉が間違っています")

    else:
        form = MapGroupForm()

    return render(request, 'map_app/group_setup.html', {'form': form})

# ---------------------------------------------------------
# メイン画面：地図と到達圏の表示
# ---------------------------------------------------------
@login_required # ★ログインしてない人は入れないようにする
def map_view(request):
    # ★門番処理：グループに入ってない人は玄関へGO
    # プロフィールがない、またはグループがない場合
    if not hasattr(request.user, 'profile') or not request.user.profile.group:
        return redirect('group_setup')
    
    # 自分のグループを取得
    my_group = request.user.profile.group

    # ★修正1: Figure(台紙)はやめて、普通のMapに戻す
    # .add_to(m) は不要です
    m = folium.Map(location=[35.6909, 139.7005], zoom_start=13, height='100%')

    # 登録されている全駅を取得
    all_stations = Station.objects.filter(group=my_group)
    
    # ユーザーがチェックした駅のIDリスト
    selected_ids = request.GET.getlist('stations')

    # APIキー
    API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQwOTZjMDE0OTBjZDQxMmViNzEyYTRhMTAwZjVjYjNjIiwiaCI6Im11cm11cjY0In0='

    for station in all_stations:
        if str(station.id) in selected_ids:
            
            # キャッシュキー
            cache_key = f'isochrone_station_{station.id}_gradated' 
            
            area_data = cache.get(cache_key)

            if not area_data:
                print(f"🌍 {station.name} のデータをAPIに取りに行きます...")
                
                body = {
                    "locations": [[station.longitude, station.latitude]],
                    "range": [300, 600, 900], # 5分, 10分, 15分
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
                except Exception:
                    pass

            if area_data:
                folium.GeoJson(
                    area_data,
                    name=f'{station.name} 到達圏',
                    style_function=lambda feature: {
                        'fillColor': '#00ff00', 
                        'color': '#00ff00',     
                        'weight': 1,
                        'fillOpacity': 0.4 if feature['properties']['value'] == 300 else \
                                       0.2 if feature['properties']['value'] == 600 else \
                                       0.1 
                    }
                ).add_to(m) # 地図mに追加

    # ---------------------------------------------------------
    # 物件ピンの表示
    # ---------------------------------------------------------
    properties = Property.objects.filter(group=my_group)

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
            
            # iframeじゃなくなるので parent.toggleLike ではなく window.toggleLike で呼べるようになりますが
            # 安全のためコードはそのままにしておきます（どちらでも動くことが多いです）
            like_btn_html = f"""
                <div style="margin-top:10px; text-align:center;">
                    <a href="#" 
                       onclick="toggleLike('/like/{prop.id}/'); return false;"
                       class="btn {btn_class} btn-sm" 
                       style="color:white; text-decoration:none;">
                        {text}
                    </a>
                </div>
            """

        # 簡易版ポップアップ（長いので省略せず書くなら前のコードと同じでOK）
        html = f"""<div style="min-width: 200px;">
                    <h6>{prop.name}</h6>
                    <div>{prop.rent}</div>
                    <a href="#" onclick="toggleLike('/like/{prop.id}/'); return false;">いいね</a>
                   </div>"""
        
        folium.Marker(
            location=[prop.latitude, prop.longitude],
            popup=folium.Popup(html, max_width=300),
            icon=folium.Icon(color=icon_color, icon=icon_icon, prefix='fa')
        ).add_to(m)

    figure = m.get_root()
    figure.render()

    context = {
        # map_data は削除
        'map_header': figure.header.render(), # CSS
        'map_body':   figure.html.render(),   # HTML(div)
        'map_script': figure.script.render(), # JS
        
        'all_stations': all_stations,
        'selected_ids': selected_ids
    }
    return render(request, 'map_app/index.html', context)

# ---------------------------------------------------------
# 物件登録ページ
# ---------------------------------------------------------
def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)

            # ログインユーザーのグループを自動セット
            if hasattr(request.user, 'profile') and request.user.profile.group:
                obj.group = request.user.profile.group
            else:
                # 万が一グループがない場合のエラー処理（本来ここには来ないはず）
                return HttpResponse("エラー：グループに所属していません", status=400)
            
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

# ---------------------------------------------------------
# 駅の追加（＆APIデータの先読み保存）
# ---------------------------------------------------------
@login_required
def add_station(request):
    if request.method == 'POST':
        form = StationForm(request.POST)
        if form.is_valid():
            station = form.save(commit=False)
            
            # 1. グループをセット
            if hasattr(request.user, 'profile') and request.user.profile.group:
                station.group = request.user.profile.group
            else:
                return redirect('group_setup')

            # 2. 駅名から座標を検索 (Geocoding)
            geolocator = Nominatim(user_agent="dousei_app_v1")
            try:
                # "駅" がついてなかったらつける（検索精度アップのため）
                search_name = station.name
                if not search_name.endswith('駅'):
                    search_name += '駅'
                
                location = geolocator.geocode(search_name)
                
                if location:
                    station.latitude = location.latitude
                    station.longitude = location.longitude
                    station.save() # ここでIDが確定する

                    # 3. ★ここが高速化のキモ！
                    # 登録したついでに、裏でAPIを叩いて到達圏データをキャッシュしておく
                    # (次に地図を開いたときは爆速で表示される)
                    print(f"🚀 {station.name} のデータを先読み中...")
                    
                    API_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjQwOTZjMDE0OTBjZDQxMmViNzEyYTRhMTAwZjVjYjNjIiwiaCI6Im11cm11cjY0In0='
                    body = {
                        "locations": [[station.longitude, station.latitude]],
                        "range": [300, 600, 900],
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
                            json=body, headers=headers
                        )
                        if call.status_code == 200:
                            area_data = call.json()
                            # キャッシュに保存
                            cache_key = f'isochrone_station_{station.id}_gradated'
                            cache.set(cache_key, area_data, 86400 * 30) # 30日間保存
                            print("✅ 先読み完了！")
                    except Exception as e:
                        print(f"API Error: {e}")

                    return redirect('index')
                else:
                    form.add_error('name', '場所が見つかりませんでした。')
            except Exception as e:
                print(e)
                form.add_error(None, 'エラーが発生しました。')
                
    else:
        form = StationForm()
    
    return render(request, 'map_app/add_station.html', {'form': form})

# ---------------------------------------------------------
# いいね機能
# ---------------------------------------------------------
def toggle_like(request, property_id):
    prop = get_object_or_404(Property, pk=property_id)
    if request.user.is_authenticated:
        if request.user in prop.likes.all():
            prop.likes.remove(request.user)
        else:
            prop.likes.add(request.user)
    return HttpResponse("OK")