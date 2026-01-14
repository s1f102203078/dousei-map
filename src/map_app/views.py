from django.shortcuts import render
from .models import Property
import folium

def map_view(request):
    # 1. 地図の初期設定（新宿中心）
    m = folium.Map(location=[35.6909, 139.7005], zoom_start=13)

    # 2. データベースから全物件を取得
    properties = Property.objects.all()

    # 3. 物件をループしてマーカーを追加
    for prop in properties:
        # アイコンの色と形を決めるロジック
        icon_color = 'blue'
        icon_icon = 'home'
        
        # マッチング判定（models.pyで作った関数を利用）
        if prop.is_matched():
            icon_color = 'red'
            icon_icon = 'heart'
        # 自分だけがいいねしている場合（ログインしている場合のみ判定）
        elif request.user.is_authenticated and request.user in prop.likes.all():
            icon_color = 'pink'
            icon_icon = 'heart'

        # ポップアップの内容（HTML）
        html = f"""
        <div style="width:200px">
            <h4>{prop.name}</h4>
            <p>家賃: {prop.rent}</p>
            <p>住所: {prop.address}</p>
        </div>
        """
        popup = folium.Popup(folium.IFrame(html, width=220, height=120), max_width=220)

        folium.Marker(
            location=[prop.latitude, prop.longitude],
            popup=popup,
            tooltip=prop.name,
            icon=folium.Icon(color=icon_color, icon=icon_icon, prefix='fa')
        ).add_to(m)

    # 4. 地図をHTML文字データに変換
    m = m._repr_html_()

    # 5. テンプレート（index.html）に地図データを渡す
    return render(request, 'map_app/index.html', {'map_data': m})