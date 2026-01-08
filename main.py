import os
import json
import random
from time import time

from monsterui.all import *
from fasthtml.common import *
from fasthtml.oauth import GoogleAppClient, OAuth
from dotenv import load_dotenv
from netatmo_thermostat.core import Thermostat, ThermostatWidget, setup_thermostat_widget
from netatmo_thermostat.solar import SolaX, SolarWidget

load_dotenv()

cli = GoogleAppClient(client_id=os.environ['GOOGLE_CLIENT_ID'], client_secret=os.environ['GOOGLE_CLIENT_SECRET'])

accepted_emails = os.environ['ALLOWED_EMAILS'].split(',')

class Auth(OAuth):
    def get_auth(self, info, ident, session, state):
        email = info.email or ''
        if info.email_verified and email in accepted_emails:
            return RedirectResponse('/', status_code=303)

# Initialize App
app, rt = fast_app(hdrs=(
    Theme.blue.headers(apex_charts=True),
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
                        'temp-real': '#00b894',
                        'temp-set': '#e17055',
                        'solar-prod': '#fdcb6e',
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

skip = ('/login', '/logout', '/redirect', r'/.*\.(png|jpg|ico|css|js|md|svg)', '/static')
oauth = Auth(app, cli, skip=skip)

# Auth / SDK Setup
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
REFRESH_TOKEN = os.environ['REFRESH_TOKEN']

@rt('/login')
@rt
def login(req):
    return (
        Title("Tordera Dashboard - Login"),
        Div(
            Div(
                Img(src="./img/tordera-thumbnail.png", cls="w-[30rem] mb-2 drop-shadow-xl hover:scale-105 transition-transform duration-700 ease-in-out"),
                H1('Tordera Dashboard', cls="font-display text-3xl font-bold mb-8 text-slate-800 tracking-wide"),
                A(Button("Log in with Google", cls="px-8 py-3 bg-white text-slate-700 border border-slate-100 rounded-2xl shadow-sm hover:shadow-md hover:scale-105 transition-all duration-300 font-medium tracking-wide"), href=oauth.login_link(req)),
                cls="flex flex-col items-center bg-white/60 backdrop-blur-2xl border border-white/50 p-16 rounded-[48px] shadow-soft"
            ),
            cls="h-screen w-full flex items-center justify-center bg-slate-50",
            style="background-image: radial-gradient(at 0% 0%, hsla(190, 100%, 95%, 1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(220, 100%, 92%, 1) 0, transparent 50%);"
        )
    )

@rt('/logout')
def logout(session):
    session.pop('auth', None)
    return RedirectResponse('/login', status_code=303)


# Initialize Thermostat globally and setup widget routes
t = Thermostat(CLIENT_ID, CLIENT_SECRET, refresh_token=REFRESH_TOKEN)
main_room, room_id = None, None
try:
    hd = t.homesdata()
    home_id = hd.homes[0].id
    room_id = hd.homes[0].rooms[0].id
except Exception as e:
    print(f"Error getting home & room id: {e}")
    raise

# Register the library's widget routes (handle /setpoint POST)
thermostat_widget = setup_thermostat_widget(rt, t, home_id, room_id, xtra_classes='relative')

# Initialize SolaX
s = SolaX()



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

@rt("/")
def get():
    return Title("Tordera Dashboard"), Body(
        Div(
            # Main Flex/Grid Container
            Div(
                # Left Column: Hero (Title + Image)
                Div(
                    H1("Tordera", cls="font-display text-5xl font-semibold text-slate-800 tracking-tight mb-1"),
                    Img(src="./img/tordera-thumbnail.png", alt="Smart Home", cls="w-full h-auto object-contain filter drop-shadow-lg"),
                    cls="flex flex-col items-center justify-center p-6 text-center lg:w-1/3 lg:h-full lg:fixed lg:left-0 lg:top-0"
                ),
                
                # Right Column: Widgets (Scrollable content)
                Div(
                    Div(
                        # Climate Widget (From SDK)
                        thermostat_widget,
                        # ThermostatWidget(t, home_id, room_id, xtra_classes='relative'),  

                        # Energy Widget (From SolaX)
                        SolarWidget(s, xtra_classes='relative'), 
                        
                        cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 w-full max-w-4xl" # Widget Grid
                    ),
                    cls="flex-1 flex items-center justify-center p-6 lg:p-12 lg:ml-[33%] min-h-screen" # Right side container
                ),
                
                cls="flex flex-col lg:flex-row min-h-screen w-full relative"
            ),
            cls="w-full min-h-screen"
        ),
        cls="bg-slate-50 text-slate-700 min-h-screen m-0 p-0",
        style="background-image: radial-gradient(at 0% 0%, hsla(190, 100%, 95%, 1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(220, 100%, 92%, 1) 0, transparent 50%);"
    )

serve()
