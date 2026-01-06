from fasthtml.common import *
import os
import json
import random
import time
from dotenv import load_dotenv
from netatmo_thermostat.core import Thermostat

load_dotenv()

# Initialize App
app, rt = fast_app(hdrs=(
    Script(src="https://cdn.jsdelivr.net/npm/apexcharts"),
    Script(src="https://cdn.tailwindcss.com"),
    Link(href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@300;400;600&display=swap", rel="stylesheet"),
    Script("""
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        display: ['Outfit', 'sans-serif'],
                    },
                    colors: {
                        'temp-real': '#81ecec',
                        'temp-set': '#fab1a0',
                        'solar-prod': '#ffeaa7',
                        'solar-cons': '#ff7675',
                        'card-bg': 'rgba(255, 255, 255, 0.85)',
                    },
                    boxShadow: {
                        'soft': '0 20px 40px rgba(0, 0, 0, 0.03)',
                    }
                }
            }
        }
    """)
))

# Auth / SDK Setup
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
REFRESH_TOKEN = os.environ['REFRESH_TOKEN']

def get_thermostat_data():
    """Fetch real data from Netatmo or return mock data if not configured."""
    
    # Generate mock timeline (last 10 hours)
    now_ms = int(time.time() * 1000)
    hour_ms = 3600 * 1000
    timeline = [now_ms - (i * hour_ms) for i in range(10)][::-1]

    try:
        t = Thermostat(CLIENT_ID, CLIENT_SECRET, refresh_token=REFRESH_TOKEN)
        t._refresh() # Ensure token is valid
        
        # Get first home
        homes = t.homesdata().homes
        if not homes: raise Exception("No homes found")
        home_id = homes[0].id
        
        # Get room status
        status = t.homestatus(home_id)
        rooms = status.home.rooms
        if not rooms: raise Exception("No rooms found")
        main_room = rooms[0] # Just grab the first room for now
        
        # For real history with dates, we would use t.getroommeasure(...)
        # For this version, we combine real CURRENT data with a mock timeline to demonstrate the chart capabilities
        return {
            'real_temp': main_room.therm_measured_temperature,
            'setpoint': main_room.therm_setpoint_temperature,
            'solar_prod': 4.8, 
            'solar_cons': 1.2, 
            # Charts expect [timestamp, value]
            'history_real': [[t, round(main_room.therm_measured_temperature - 1 + (random.random()*0.5), 2)] for t in timeline],
            'history_target': [[t, main_room.therm_setpoint_temperature] for t in timeline],
            'history_solar_prod': [[t, round(random.uniform(0, 5), 2)] for t in timeline],
            'history_solar_cons': [[t, round(random.uniform(0.5, 2), 2)] for t in timeline],
            'is_mock': False
        }
    except Exception as e:
        print(f"Error fetching data: {e}, falling back to mock.")
        return {
            'real_temp': 20.0,
            'setpoint': 19.5,
            'solar_prod': 0.0,
            'solar_cons': 0.0,
            'history_real': [[t, 20.0] for t in timeline],
            'history_target': [[t, 19.5] for t in timeline],
            'history_solar_prod': [[t, 0.0] for t in timeline],
            'history_solar_cons': [[t, 0.0] for t in timeline],
            'is_mock': True
        }

# Components
def DashboardCard(title, children, extra_classes=""):
    return Div(
        Div(
            Span(title, cls="font-display text-xs font-bold text-slate-400 uppercase tracking-widest"),
            cls="flex justify-between items-center mb-6"
        ),
        children,
        cls=f"bg-white/85 backdrop-blur-xl border border-white/60 rounded-[32px] p-8 shadow-soft flex flex-col h-full min-h-[320px] transition-transform hover:-translate-y-1 duration-300 {extra_classes}"
    )

def ControlBtn(text, change, current_temp, **kwargs):
    # HTMX button to update setpoint
    return Button(text, 
        hx_post="/setpoint", 
        hx_vals=json.dumps({'change': change, 'current_setpoint': current_temp}),
        hx_target="#setpoint-display",
        hx_swap="outerHTML",
        cls="w-10 h-10 rounded-full border border-black/5 bg-white/50 text-slate-700 text-lg flex items-center justify-center hover:bg-white hover:scale-105 transition-all shadow-sm cursor-pointer",
        **kwargs
    )

def SetpointDisplay(temp):
    return Span(
        "Target ", Span(f"{temp}°", cls="text-temp-set font-semibold"),
        id="setpoint-display",
        cls="text-slate-500 font-medium text-base transition-all duration-300 ease-in-out"
    )

@rt("/setpoint")
def post(change: float, current_setpoint: float):
    new_temp = round(current_setpoint + change, 1)
    
    # Try to update real API
    if CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN:
        try:
            t = Thermostat(CLIENT_ID, CLIENT_SECRET, refresh_token=REFRESH_TOKEN)
            t._refresh()
            # We need to fetch homes/rooms again to get IDs (simple but inefficient approach for this demo)
            homes = t.homesdata().homes
            if homes:
                home_id = homes[0].id
                status = t.homestatus(home_id)
                rooms = status.home.rooms
                if rooms:
                    room_id = rooms[0].id
                    # Set for 1 hour
                    t.setroomthermpoint(home_id, room_id, 'manual', new_temp, int(time.time() + 3600))
        except Exception as e:
            print(f"Failed to set temp: {e}")
            
    # Return updated display AND update the buttons with new current_setpoint using OOB swap
    return (
        SetpointDisplay(new_temp),
        ControlBtn("−", -0.5, new_temp, id="btn-minus", hx_swap_oob="true"),
        ControlBtn("+", 0.5, new_temp, id="btn-plus", hx_swap_oob="true")
    )

@rt("/")
def get():
    data = get_thermostat_data()
    
    # Chart scripts
    # ApexCharts with datetime X-axis expects [timestamp, value] pairs
    temp_json = json.dumps([{ 'name': 'Real', 'data': data['history_real'] }, { 'name': 'Target', 'data': data['history_target'] }])
    solar_json = json.dumps([{ 'name': 'Production', 'data': data['history_solar_prod'] }, { 'name': 'Consumption', 'data': data['history_solar_cons'] }])
    
    chart_init_script = Script(f"""
        const commonOptions = {{
            chart: {{ type: 'area', height: '100%', parentHeightOffset: 0, sparkline: {{ enabled: true }}, animations: {{ enabled: true }} }},
            stroke: {{ curve: 'smooth', width: 3 }},
            fill: {{ type: 'gradient', gradient: {{ opacityFrom: 0.15, opacityTo: 0 }} }},
            tooltip: {{ theme: 'light', x: {{ format: 'dd MMM HH:mm' }} }},
            grid: {{ padding: {{ top: 10, bottom: 10, left: 0, right: 0 }} }},
            xaxis: {{ type: 'datetime', tooltip: {{ enabled: false }}, labels: {{ show: false }}, axisBorder: {{ show: false }}, axisTicks: {{ show: false }} }}
        }};

        new ApexCharts(document.querySelector("#tempChart"), {{
            ...commonOptions,
            series: {temp_json},
            colors: ['#81ecec', '#fab1a0'],
            stroke: {{ ...commonOptions.stroke, width: [3, 2], dashArray: [0, 5] }}
        }}).render();

        new ApexCharts(document.querySelector("#solarChart"), {{
            ...commonOptions,
            series: {solar_json},
            colors: ['#ffeaa7', '#ff7675'],
            fill: {{ type: 'gradient', gradient: {{ shadeIntensity: 1, opacityFrom: 0.25, opacityTo: 0.05, stops: [0, 90, 100] }} }}
        }}).render();
    """)

    return Title("Tordera Dashboard"), Body(
        Div(
            # Header
            Header(
                Div(
                    Img(src="./img/tordera-thumbnail.png", alt="Smart Home", cls="w-full h-full object-contain filter drop-shadow-lg"),
                    cls="relative z-10 mb-2 drop-shadow-2xl",
                    style="width: 500px; height: 500px;" 
                ),
                Div(
                    H1("Tordera", cls="font-display text-3xl font-semibold text-slate-800 tracking-tight"),
                    # Removed weather line
                ),
                cls="col-span-1 md:col-span-2 flex flex-col items-center text-center mb-6"
            ),
            
            # Climate Widget
            DashboardCard("Climate", Div(
                Div(
                    Div(
                        # HTMX Controls with IDs
                        ControlBtn("−", -0.5, data['setpoint'], id="btn-minus"),
                        ControlBtn("+", 0.5, data['setpoint'], id="btn-plus"),
                        cls="absolute top-8 right-8 flex gap-2" 
                    ),
                ),
                Div(
                    Span(f"{data['real_temp']}°", cls="font-display text-6xl text-temp-real leading-none"),
                    SetpointDisplay(data['setpoint']),
                    cls="flex items-baseline gap-3 flex-wrap"
                ),
                Div(
                    Div(id="tempChart"),
                    cls="mt-auto -mx-3 h-[150px]"
                ),
                cls="flex flex-col h-full"
            ), extra_classes="relative"),

            # Energy Widget
            DashboardCard("Energy", Div(
                Div(
                    Div(
                        Span("Production", cls="text-xs text-slate-400 uppercase tracking-wide"),
                        Span(
                            f"{data['solar_prod']} ", Span("kW", cls="text-base font-normal"),
                            cls="font-display text-3xl font-semibold text-solar-prod"
                        ),
                        cls="flex flex-col"
                    ),
                    Div(
                        Span("Consumption", cls="text-xs text-slate-400 uppercase tracking-wide"),
                        Span(
                            f"{data['solar_cons']} ", Span("kW", cls="text-base font-normal"),
                            cls="font-display text-3xl font-semibold text-solar-cons"
                        ),
                        cls="flex flex-col"
                    ),
                    cls="flex items-baseline justify-between mb-4 mt-2"
                ),
                Div(
                    Div(id="solarChart"),
                    cls="mt-auto -mx-3 h-[150px]"
                ),
                cls="flex flex-col h-full"
            )),
            
            cls="w-full max-w-[900px] grid grid-cols-1 md:grid-cols-2 gap-6"
        ),
        chart_init_script,
        cls="bg-slate-50 text-slate-700 min-h-screen flex items-center justify-center p-6 md:p-10",
        style="background-image: radial-gradient(at 0% 0%, hsla(190, 100%, 95%, 1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(220, 100%, 92%, 1) 0, transparent 50%);"
    )

serve()
