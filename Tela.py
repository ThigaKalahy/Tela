import datetime
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

BASE_URL = "http://integration.systemsatx.com.br"
LOGIN_URL = f"{BASE_URL}/Login"
POSITION_HISTORY_URL = f"{BASE_URL}/Tracking/PositionHistory/List"

USERNAME = "systemday24@systemsat.com.br"
PASSWORD = "123456"
HASHAUTH = "D32DCDE9-D9DB-43EF-81CF-AA6007032261"


last_20_temperatures = []
last_20_humidities = []

latest_data = {
    "temperature": None,
    "humidity": None,
    "update_date": None,
    "last_id_position": None
}

access_token = None

def login():
    global access_token
    url = f"{LOGIN_URL}?username={USERNAME}&password={PASSWORD}&hashauth={HASHAUTH}"
    response = requests.post(url)
    if response.status_code == 200:
        token_response = response.json()
        access_token = token_response["AccessToken"]
    else:
        print(f"Erro ao fazer login: {response.text}")

def get_latest_position():
    global access_token
    if access_token:
        headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }
        if latest_data["last_id_position"] is None:
            start_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=3)
            params = [{
                "PropertyName": "EventDate",
                "Condition": "GreaterThan",
                "Value": start_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            }]
        else:
            params = [{
                "PropertyName": "IdPosition",
                "Condition": "GreaterThan",
                "Value": latest_data["last_id_position"]
            }]
        
        response = requests.post(POSITION_HISTORY_URL, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                latest_position = data[0]
                temperature = latest_position["ListTelemetry"].get("9")
                humidity = latest_position["ListTelemetry"].get("526")
                update_date = latest_position["UpdateDate"]
                last_id_position = latest_position["IdPosition"]
                latest_data.update({
                    "temperature": temperature,
                    "humidity": humidity,
                    "update_date": update_date,
                    "last_id_position": last_id_position
                })
                
                if temperature is not None:
                    last_20_temperatures.append(temperature)
                    if len(last_20_temperatures) > 20:
                        last_20_temperatures.pop(0)
                if humidity is not None:
                    last_20_humidities.append(humidity)
                    if len(last_20_humidities) > 20:
                        last_20_humidities.pop(0)
            else:
                print("Falha no retorno.")
        else:
            print(f"Erro ao obter posição mais recente: {response.text}")
    else:
        print("Token de acesso não disponível. Realize o login.")

def daily_login():
    login()
   
    get_latest_position()

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(daily_login, 'interval', days=1)  
scheduler.add_job(get_latest_position, 'interval', seconds=10)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html', temperature=latest_data["temperature"], humidity=latest_data["humidity"], update_date=latest_data["update_date"], last_20_temperatures=last_20_temperatures, last_20_humidities=last_20_humidities)

@app.route('/latest_data')
def get_latest_data():  
    return jsonify(temperature=latest_data["temperature"], humidity=latest_data["humidity"], update_date=latest_data["update_date"])

if __name__ == '__main__':
    # Chamar daily_login uma vez ao iniciar o programa para garantir que o token de acesso esteja disponível
    daily_login()
    app.run(debug=True)
