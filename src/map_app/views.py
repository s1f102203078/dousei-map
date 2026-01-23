from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.cache import cache
from .models import Property, Station, MapGroup, UserProfile, Line
from .forms import PropertyForm, MapGroupForm, StationSelectionForm
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
@login_required
def map_view(request):
    my_group = request.user.profile.group
    
    if not my_group:
        return redirect('group_setup')

    # 1. 駅データをリストにする
    stations_data = []
    all_stations = my_group.selected_stations.all()
    
    # 地図の中心用（データがなければ新宿）
    center = {'lat': 35.690921, 'lon': 139.700258}
    
    if all_stations.exists():
        center['lat'] = all_stations.first().latitude
        center['lon'] = all_stations.first().longitude

    for station in all_stations:
        stations_data.append({
            'name': station.name,
            'lat': station.latitude,
            'lon': station.longitude,
        })

    # 2. 物件データをリストにする
    properties_data = []
    properties = Property.objects.filter(group=my_group)
    
    for prop in properties:
        if prop.latitude and prop.longitude:
            # マッチ度判定などのロジックもここで計算して渡す
            is_matched = prop.is_matched()
            
            # いいねした人の名前リスト
            liked_users = [u.username for u in prop.likes.all()]
            
            properties_data.append({
                'id': prop.id,
                'name': prop.name,
                'rent': prop.rent,
                'address': prop.address,
                'lat': prop.latitude,
                'lon': prop.longitude,
                'is_matched': is_matched,
                'liked_users': liked_users,
            })

    # 3. HTMLには「地図」ではなく「データ」を渡す
    context = {
        'group_name': my_group.name,
        'center_lat': center['lat'],
        'center_lon': center['lon'],
        # json.dumpsでJavaScriptが読める形式に変換
        'stations_json': json.dumps(stations_data, ensure_ascii=False),
        'properties_json': json.dumps(properties_data, ensure_ascii=False),
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
    # ユーザーの所属グループを取得
    group = request.user.profile.group
    
    if not group:
        return redirect('group_setup')

    if request.method == 'POST':
        # フォーム送信時の処理（チェックされた駅を保存）
        form = StationSelectionForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        # 初期表示（現在の選択状態を反映）
        form = StationSelectionForm(instance=group)

    # 路線ごとに駅データを取得（テンプレートでツリー表示するために必要）
    # prefetch_related を使うと、SQLの回数を減らして高速に駅を取得できます
    lines = Line.objects.prefetch_related('stations').all().order_by('sort_order')

    context = {
        'form': form,
        'lines': lines, # これがVSCode風表示のデータ源になります
    }
    return render(request, 'map_app/add_station.html', context)

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