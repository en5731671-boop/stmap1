import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime, timedelta

# --- ページ設定 ---
st.set_page_config(page_title="九州気温スーパー3D Map", layout="wide")
st.title("🌡️ 九州主要都市の気温 3Dマップ（スーパー進化版）")

# 九州7県のデータ
kyushu_capitals = {
    'Fukuoka':    {'lat': 33.5904, 'lon': 130.4017},
    'Saga':       {'lat': 33.2494, 'lon': 130.2974},
    'Nagasaki':   {'lat': 32.7450, 'lon': 129.8739},
    'Kumamoto':   {'lat': 32.7900, 'lon': 130.7420},
    'Oita':       {'lat': 33.2381, 'lon': 131.6119},
    'Miyazaki':   {'lat': 31.9110, 'lon': 131.4240},
    'Kagoshima':  {'lat': 31.5600, 'lon': 130.5580}
}

# --- 単位切替 ---
unit = st.radio("温度単位", ["℃", "℉"])

# --- データ取得関数 ---
@st.cache_data(ttl=600)
def fetch_weather_data():
    weather_info = []
    BASE_URL = 'https://api.open-meteo.com/v1/forecast'
    
    for city, coords in kyushu_capitals.items():
        params = {
            'latitude': coords['lat'],
            'longitude': coords['lon'],
            'current_weather': True,
            'hourly': 'temperature_2m'
        }
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 現在の気温
            temp_c = data['current_weather']['temperature']
            # 過去24時間の時間軸データ
            times = data['hourly']['time']
            temps = data['hourly']['temperature_2m']
            
            weather_info.append({
                'City': city,
                'lat': coords['lat'],
                'lon': coords['lon'],
                'Temperature': temp_c,
                'HourlyTimes': times,
                'HourlyTemps': temps
            })
        except Exception as e:
            st.error(f"Error fetching {city}: {e}")
    
    return pd.DataFrame(weather_info)

# --- データ取得 ---
with st.spinner('最新の気温データを取得中...'):
    df = fetch_weather_data()

# 単位変換
if unit == "℉":
    df['Temperature'] = df['Temperature'] * 9/5 + 32

# --- メインレイアウト ---
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("取得したデータ")
    st.dataframe(df[['City', 'Temperature']], use_container_width=True)
    
    if st.button('データを更新'):
        st.cache_data.clear()
        st.experimental_rerun()
    
    # 都市選択
    selected_city = st.selectbox("都市を選択して時系列表示", df['City'])
    city_data = df[df['City'] == selected_city].iloc[0]
    times = city_data['HourlyTimes']
    temps = city_data['HourlyTemps']
    
    if unit == "℉":
        temps = [t*9/5 + 32 for t in temps]
    
    st.line_chart(pd.DataFrame({"Temperature": temps}, index=pd.to_datetime(times)))

with col2:
    st.subheader("3D カラムマップ")
    
    # 気温を高さ（メートル）に変換
    df['elevation'] = df['Temperature'] * 3000
    
    # カラーを温度に応じて変化（青→赤）
    df['color'] = df['Temperature'].apply(lambda t: [min(255, max(0, int((t-15)*10))), 100, 255 - min(255, max(0, int((t-15)*10))), 180])
    
    # Pydeck設定
    view_state = pdk.ViewState(
        latitude=32.7,
        longitude=131.0,
        zoom=6.2,
        pitch=45,
        bearing=0
    )

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position='[lon, lat]',
        get_elevation='elevation',
        radius=12000,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>{City}</b><br>気温: {Temperature}°" + unit, "style": {"color": "white"}}
    ))
