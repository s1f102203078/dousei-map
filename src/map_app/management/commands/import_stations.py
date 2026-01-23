import urllib.request
import urllib.parse
import json
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from map_app.models import Line, Station

class Command(BaseCommand):
    help = 'HeartRails Express APIを使って東京都の全駅データをインポートします'

    def handle(self, *args, **options):
        self.stdout.write("📡 データのダウンロードを開始します...")

        # 1. まずデータを全削除（重複防止）
        Line.objects.all().delete()
        self.stdout.write("🗑️ 既存のデータをリセットしました")

        # 2. 東京都の路線一覧を取得
        # ★修正: 日本語(東京都)をURLエンコードしてエラーを回避
        params = urllib.parse.urlencode({
            'method': 'getLines',
            'prefecture': '東京都'
        })
        lines_url = f"http://express.heartrails.com/api/json?{params}"
        
        try:
            with urllib.request.urlopen(lines_url) as response:
                data = json.loads(response.read().decode('utf-8'))
                line_names = data['response']['line']
        except Exception as e:
            self.stderr.write(f"❌ 路線データの取得に失敗しました: {e}")
            return

        self.stdout.write(f"📋 {len(line_names)} 本の路線が見つかりました。詳細データの取得を開始します（数分かかります）...")

        # 3. 各路線の駅データを取得して保存
        total_stations = 0
        
        with transaction.atomic():
            for i, line_name in enumerate(line_names):
                # 路線を作成
                line = Line.objects.create(name=line_name, sort_order=i)
                
                # その路線の駅一覧を取得
                # ここも日本語(路線名)をURLエンコード
                station_params = urllib.parse.urlencode({
                    'method': 'getStations',
                    'line': line_name
                })
                stations_url = f"http://express.heartrails.com/api/json?{station_params}"

                try:
                    with urllib.request.urlopen(stations_url) as response:
                        station_data = json.loads(response.read().decode('utf-8'))
                        stations_list = station_data['response']['station']

                        for j, st in enumerate(stations_list):
                            # 駅を作成
                            Station.objects.create(
                                line=line,
                                name=st['name'],
                                latitude=st['y'],
                                longitude=st['x'],
                                sort_order=j
                            )
                            total_stations += 1
                    
                    # サーバー負荷軽減のため待機
                    time.sleep(0.1)
                    self.stdout.write(f"  ✅ ({i+1}/{len(line_names)}) {line_name} を保存しました")

                except Exception as e:
                    self.stderr.write(f"  ⚠️ {line_name} の駅データ取得に失敗: {e}")

        self.stdout.write(self.style.SUCCESS(f"\n✨ 完了！ 東京都の全路線と、合計 {total_stations} 個の駅をデータベースに登録しました！"))