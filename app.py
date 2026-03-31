import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.express as px
import os
import time
from datetime import datetime as dt

# ------------------- Google Sheets Setup -------------------
GOOGLE_SHEETS_ENABLED = False
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    gc = gspread.authorize(credentials)
    SHEET_ID = "16po2bcvWIQW8zOzM9GJRNsosezpXUA0H_iF5Ry-d3ek"
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Contributions")   # Change only if your tab name is different
    GOOGLE_SHEETS_ENABLED = True
except Exception:
    GOOGLE_SHEETS_ENABLED = False
    
# Rate limit config
RATE_LIMIT_SECONDS = 600

# Initialize separate session state timers
if "last_contrib_time" not in st.session_state:
    st.session_state.last_contrib_time = None
if "last_feedback_time" not in st.session_state:
    st.session_state.last_feedback_time = None
if "last_ip" not in st.session_state:
    st.session_state.last_ip = None

# MA CITIES list (Dorchester removed)
MA_CITIES = [
    "Abington", "Acton", "Acushnet", "Adams", "Agawam", "Alford", "Amherst", "Andover",
    "Arlington", "Ashburnham", "Ashfield", "Ashland", "Athol", "Attleboro", "Auburn",
    "Avon", "Ayer", "Barre", "Becket", "Bedford", "Bellingham", "Belmont", "Belchertown",
    "Berlin", "Bernardston", "Beverly", "Billerica", "Blackstone", "Blandford", "Bolton",
    "Boston", "Bourne", "Boxborough", "Boxford", "Braintree", "Brimfield", "Brockton", "Brookfield",
    "Brookline", "Buckland", "Burlington", "Cambridge", "Canton", "Carlisle", "Carver",
    "Charlemont", "Charlton", "Chatham", "Chester", "Chesterfield", "Chicopee", "Chilmark",
    "Clarksburg", "Clinton", "Cohasset", "Concord", "Conway", "Dalton", "Danvers",
    "Dartmouth", "Dedham", "Deerfield", "Dennis", "Dighton", "Douglas", "Dracut", "Dudley",
    "Dunstable", "Duxbury", "Eastham", "Easthampton", "East Bridgewater", "East Longmeadow",
    "Easton", "Edgartown", "Egremont", "Erving", "Essex", "Fairhaven", "Falmouth",
    "Fitchburg", "Florida", "Foxborough", "Framingham", "Franklin", "Freetown", "Gardner",
    "Georgetown", "Gill", "Gloucester", "Goshen", "Gosnold", "Grafton", "Granby",
    "Granville", "Great Barrington", "Greenfield", "Groton", "Groveland", "Hadley",
    "Hamilton", "Hancock", "Hanover", "Hanson", "Hardwick", "Harvard", "Harwich",
    "Hatfield", "Haverhill", "Hawley", "Hingham", "Hinsdale", "Hubbardston", "Hudson",
    "Hull", "Huntington", "Ipswich", "Kingston", "Lakeville", "Lancaster", "Lanesborough",
    "Leicester", "Lenox", "Leverett", "Leyden", "Lincoln", "Littleton", "Longmeadow",
    "Lowell", "Ludlow", "Lunenburg", "Lynn", "Lynnfield", "Manchester-by-the-Sea",
    "Mansfield", "Marion", "Marlborough", "Marshfield", "Mattapoisett", "Maynard",
    "Medfield", "Medford", "Medway", "Melrose", "Mendon", "Merrimac", "Middleborough",
    "Middlefield", "Middleton", "Milford", "Millis", "Millbury", "Millville", "Milton",
    "Monroe", "Montague", "Monterey", "Nahant", "Nantucket", "Natick", "Needham",
    "New Ashford", "New Bedford", "New Braintree", "New Marlborough", "New Salem",
    "Newbury", "Newburyport", "Newton", "North Adams", "North Andover", "North Attleborough",
    "North Reading", "Northampton", "Northborough", "Northbridge", "Norton", "Norfolk",
    "Norwood", "Oak Bluffs", "Orange", "Orleans", "Oxford", "Paxton", "Pembroke",
    "Pepperell", "Peru", "Petersham", "Phillipston", "Plainfield", "Plainville", "Plymouth",
    "Princeton", "Provincetown", "Randolph", "Raynham", "Reading", "Rehoboth", "Revere",
    "Rockport", "Rockland", "Rowe", "Rowley", "Royalston", "Russell", "Rutland", "Salem",
    "Sandisfield", "Sandwich", "Saugus", "Savoy", "Scituate", "Seekonk", "Sharon",
    "Sheffield", "Shelburne", "Sherborn", "Shirley", "Shrewsbury", "Shutesbury", "Somerset",
    "South Hadley", "Southampton", "Southborough", "Southbridge", "Southwick", "Spencer",
    "Springfield", "Stoughton", "Stow", "Sturbridge", "Sunderland", "Sutton", "Swampscott",
    "Swansea", "Templeton", "Tewksbury", "Tisbury", "Tolland", "Townsend", "Truro",
    "Uxbridge", "Wales", "Walpole", "Ware", "Wareham", "Warren", "Watertown", "Wayland",
    "Wellesley", "Wenham", "Wendell", "West Boylston", "West Bridgewater", "West Brookfield",
    "West Newbury", "West Springfield", "West Stockbridge", "West Tisbury", "Westborough",
    "Westfield", "Westminster", "Weston", "Westwood", "Weymouth", "Whately", "Whitman",
    "Wilbraham", "Wilmington", "Winchendon", "Winchester", "Windsor", "Winthrop", "Woburn",
    "Worcester", "Worthington", "Yarmouth"
]

# US Federal Holidays
FEDERAL_HOLIDAYS = {
    2025: [date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 5, 26),
           date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1), date(2025, 10, 13),
           date(2025, 11, 11), date(2025, 11, 27), date(2025, 12, 25)],
    2026: [date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 5, 25),
           date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7), date(2026, 10, 12),
           date(2026, 11, 11), date(2026, 11, 26), date(2026, 12, 25)],
    2027: [date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 5, 31),
           date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6), date(2027, 10, 11),
           date(2027, 11, 11), date(2027, 11, 25), date(2027, 12, 24)],
}

def get_holidays_for_year(year):
    return FEDERAL_HOLIDAYS.get(year, []) + FEDERAL_HOLIDAYS.get(year + 1, [])

def is_business_day(dt):
    if dt.weekday() >= 5:
        return False
    holidays = get_holidays_for_year(dt.year)
    return dt not in holidays

def next_business_day(dt):
    current = dt
    while not is_business_day(current):
        current += timedelta(days=1)
    return current

def add_business_days(start_date, days):
    current = start_date
    remaining = abs(days)
    direction = 1 if days >= 0 else -1
    while remaining > 0:
        current += timedelta(days=direction)
        if is_business_day(current):
            remaining -= 1
    return current

# Config
st.set_page_config(
    page_title="Boston LTC/FID Licensing Wait Time for Fingerprinting Appointment Calculator",
    page_icon="🖐️",
    layout="wide",
    initial_sidebar_state="expanded"
)

SLOPE = 1.0996490280303988
INTERCEPT = -4338.724561548079
BASE_DATE = date(1899, 12, 30)

ASSETS = "assets/"
DATA_DIR = "data/"

# Sidebar
# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🖐️ Boston LTC Predictor")
    
    # Load facts from external file
    try:
        with open("facts.txt", "r", encoding="utf-8") as f:
            facts_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        facts_list = ["Civil War|The right to bear arms shall not be infringed. (2nd Amendment)"]

    # Initialize session state for manual navigation
    if "fact_index" not in st.session_state:
        st.session_state.fact_index = 0

    # Placeholder for the fact box
    fact_box = st.empty()

    # Display current fact
    if facts_list:
        current_fact = facts_list[st.session_state.fact_index]
        try:
            war_name, fact_text = current_fact.split('|', 1)
            fact_box.markdown(f"""
            <div style="border: 2px solid #4a90e2; border-radius: 10px; padding: 12px 15px; background-color: #1e1e1e; margin-bottom: 10px; text-align: center;">
                <h4 style="margin: 0 0 8px 0; color: #4a90e2; font-size: 1.1em;">{war_name}</h4>
                <p style="margin: 0; line-height: 1.5; font-size: 0.95em;">{fact_text}</p>
            </div>
            """, unsafe_allow_html=True)
        except:
            fact_box.info(current_fact)

    # Previous / Next buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Previous", use_container_width=True):
            st.session_state.fact_index = (st.session_state.fact_index - 1) % len(facts_list)
            st.rerun()
    with col3:
        if st.button("Next →", use_container_width=True):
            st.session_state.fact_index = (st.session_state.fact_index + 1) % len(facts_list)
            st.rerun()

    # Auto-rotate every 13 seconds
    import time
    time.sleep(13)
    st.session_state.fact_index = (st.session_state.fact_index + 1) % len(facts_list)
    st.rerun()
    
    st.markdown("---")
    st.markdown("### ❤️ Support the project")
    st.markdown("[**Donate on Venmo**](https://www.venmo.com/u/helpingmassholes1776)")
    st.image(f"{ASSETS}venmo_qr.jpeg", width=220, caption="Scan to donate (100% voluntary)")
    st.caption("Thank you for using and sharing!")

# Header
st.image(f"{ASSETS}header_george.jpg", width='stretch')

# 3-column layout
left_col, main_col, right_col = st.columns([1.2, 7, 1.2])

with left_col:
    st.image(f"{ASSETS}border_left1.jpg", width='stretch')
    st.image(f"{ASSETS}border_left2.jpg", width='stretch')
    st.image(f"{ASSETS}border_left3.jpg", width='stretch')
    st.image(f"{ASSETS}border_left4.jpg", width='stretch')
    st.image(f"{ASSETS}border_left5.jpg", width='stretch')

with right_col:
    st.image(f"{ASSETS}border_right1.jpg", width='stretch')
    st.image(f"{ASSETS}border_right2.jpg", width='stretch')
    st.image(f"{ASSETS}border_right3.jpg", width='stretch')
    st.image(f"{ASSETS}border_right4.jpg", width='stretch')
    st.image(f"{ASSETS}border_right5.jpg", width='stretch')

with main_col:
    st.title("Boston LTC/FID Licensing Wait Time for Fingerprinting Appointment Calculator")
    st.caption("**Boston-only right now** — wait times can vary a lot by city/town. "
               "If you're in Milford, Concord, Worcester, or anywhere else in MA, "
               "your estimate may be different. Select the city/town where you live below.")

    col1, col2 = st.columns([3, 1])
    with col1:
        submission_date = st.date_input(
            "Enter the date you submitted / paid for your application",
            value=date(2025, 6, 20),
            min_value=date(2024, 1, 1),
            format="MM/DD/YYYY"
        )

    if submission_date:
        submission_serial = (submission_date - BASE_DATE).days
        predicted_serial = SLOPE * submission_serial + INTERCEPT
        predicted_raw = BASE_DATE + timedelta(days=round(predicted_serial))
        predicted_central = next_business_day(predicted_raw)
        lower_date = add_business_days(predicted_central, -5)
        upper_date = add_business_days(predicted_central, +5)
        days_wait_central = (predicted_central - submission_date).days

        st.header("📅 Your Estimated Fingerprint Call Date")
        st.success(f"**{predicted_central.strftime('%A, %m/%d/%Y')}** (±5 business days)")
        st.info(f"≈ **{days_wait_central} calendar days** after submission ({submission_date.strftime('%m/%d/%Y')}).\n"
                f"**Likely range:** {lower_date.strftime('%m/%d/%Y')} to {upper_date.strftime('%m/%d/%Y')}\n"
                f"(excluding weekends & federal holidays)")
        if predicted_central != predicted_raw:
            st.caption(f"Raw model estimate was {predicted_raw.strftime('%m/%d/%Y')} — adjusted forward to next business day.")
        st.caption("This is an estimate based on historical trends. Actual times vary due to processing volume, staffing, etc.")

    def get_approx_ip():
        try:
            if hasattr(st.context, "ip_address"):
                ip = st.context.ip_address
                if ip:
                    return ip
            headers = st.context.headers or {}
            forwarded = headers.get("X-Forwarded-For", "unknown")
            if forwarded != "unknown":
                return forwarded.split(",")[0].strip()
            return "unknown"
        except Exception:
            return "unknown"
    
        # ====================== CONTRIBUTE YOUR DATA ======================
    st.subheader("💡 Help Make This More Accurate")
    st.write("Submit your own dates + city to improve the model (and help build calculators for other MA cities). "
             "Limited to 1 submission every 10 minutes to prevent spam.")

    approx_ip = "unknown"

    can_contrib = True
    if st.session_state.last_contrib_time is not None:
        time_since = time.time() - st.session_state.last_contrib_time
        if time_since < RATE_LIMIT_SECONDS:
            remaining = int(RATE_LIMIT_SECONDS - time_since)
            st.warning(f"Contribution cooldown: {remaining // 60} min {remaining % 60} sec left")
            can_contrib = False

    with st.form("contribute_form"):
        col1, col2 = st.columns(2)
        with col1:
            user_sub = st.date_input("Your Submission / Paid Date *", key="user_sub", format="MM/DD/YYYY")
        with col2:
            user_fp = st.date_input("Your Actual Fingerprint Call Date *", key="user_fp", format="MM/DD/YYYY")

        user_city = st.selectbox(
            "Your City/Town in Massachusetts *",
            options=["Select your city..."] + MA_CITIES,
            index=0,
            help="Required — this helps me build city-specific predictors later"
        )

        col3, col4 = st.columns([3, 1])
        with col3:
            user_licence_date = st.date_input(
                "Licence in-hand Date *",
                key="user_licence",
                disabled=st.session_state.get("no_licence_yet", False),
                format="MM/DD/YYYY"
            )
        with col4:
            no_licence_yet = st.checkbox("I have not received this yet", key="no_licence_yet")

        submitted = st.form_submit_button("Submit My Data", disabled=not can_contrib)

        if submitted and can_contrib:
            if not user_sub or not user_fp or user_city == "Select your city...":
                st.error("Submission date, Fingerprint call date, and City are required.")
            else:
                licence_value = user_licence_date if not no_licence_yet else None
                
                # Convert dates to strings for Google Sheets
                row = [
                    user_city,
                    str(user_sub),
                    str(user_fp),
                    str(licence_value) if licence_value else "",
                    dt.now().strftime("%m/%d/%Y %H:%M:%S"),
                    approx_ip,
                    no_licence_yet
                ]

                if GOOGLE_SHEETS_ENABLED:
                    try:
                        worksheet.append_row(row, value_input_option="USER_ENTERED")
                        st.success("✅ Submitted successfully. Awaiting review by admin.")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")
                else:
                    st.error("Google Sheets connection is not active. Please contact the admin.")

                st.session_state.last_contrib_time = time.time()


# Hardcoded historical data
sub_serials = [45676, 45690, 45698, 45707, 45709, 45712, 45712, 45712, 45712, 45716,
               45718, 45725, 45739, 45746, 45752, 45753, 45755, 45764, 45822, 45831,
               45834, 45846, 45862, 45864, 45871]
fp_serials = [45889, 45908, 45915, 45919, 45923, 45924, 45926, 45929, 45930, 45931,
              45937, 45945, 45958, 45968, 45971, 45973, 45975, 45985, 46056, 46058,
              46066, 46080, 46091, 46093, 46099]

chart_df = pd.DataFrame({
    "Submission_Serial": sub_serials,
    "Fingerprint_Serial": fp_serials,
    "Submission_Date": [BASE_DATE + timedelta(days=s) for s in sub_serials],
    "Fingerprint_Date": [BASE_DATE + timedelta(days=f) for f in fp_serials]
})

chart_df["Submission_Date"] = pd.to_datetime(chart_df["Submission_Date"])
chart_df["Fingerprint_Date"] = pd.to_datetime(chart_df["Fingerprint_Date"])

# Main scatter (blue dots + trendline)
fig = px.scatter(
    chart_df,
    x="Submission_Serial",
    y="Fingerprint_Serial",
    hover_data={"Submission Date": chart_df["Submission_Date"], "Fingerprint Date": chart_df["Fingerprint_Date"]},
    title="Historical Submissions vs Actual Fingerprint Dates",
    labels={"Submission_Serial": "Submission Date", "Fingerprint_Serial": "Fingerprint Call Date"},
    trendline="ols",
    trendline_color_override="#ff7f0e"
)

fig.update_traces(marker=dict(size=10, color="#1f77b4"), selector=dict(mode='markers'))

# Add green in-hand points and lines for the two known records
known_indices = [16, 18]
known_inhand_serials = [46085, 46091]
known_inhand_dates = [date(2026, 3, 4), date(2026, 3, 10)]

for i, idx in enumerate(known_indices):
    sub_ser = sub_serials[idx]
    fp_ser = fp_serials[idx]
    inhand_ser = known_inhand_serials[i]

    fig.add_trace(
        px.scatter(
            x=[sub_ser],
            y=[inhand_ser],
            hover_data={"In-Hand Date": [known_inhand_dates[i]]}
        ).data[0].update(marker=dict(color="green", size=12, symbol="diamond"))
    )

    fig.add_shape(
        type="line",
        x0=sub_ser,
        y0=fp_ser,
        x1=sub_ser,
        y1=inhand_ser,
        line=dict(color="green", width=1, dash="dash"),
        opacity=0.7
    )

# Axis formatting
fig.update_xaxes(
    tickvals=chart_df["Submission_Serial"][::5],
    ticktext=chart_df["Submission_Date"][::5].dt.strftime('%m/%d/%Y'),
    title="Submission Date"
)
fig.update_yaxes(
    tickvals=chart_df["Fingerprint_Serial"][::5],
    ticktext=chart_df["Fingerprint_Date"][::5].dt.strftime('%m/%d/%Y'),
    title="Fingerprint Call Date"
)

fig.update_layout(height=500, hovermode="closest", showlegend=False)

st.plotly_chart(fig, use_container_width=True)
st.caption("Orange line = fitted linear regression. "
           "Green diamonds/lines = known LTC In-Hand dates **after** call dates (above blue dots). "
           "Hover over points for exact dates.")

# ====================== FEEDBACK ======================
st.subheader("💬 Ideas or Suggestions?")
feedback_text = st.text_area(
    "Share any feature requests, improvements, bugs, or comments here:", 
    placeholder="E.g. 'Add best/worst case dates' or 'Make it look even nicer on mobile'"
)

can_feedback = True
if st.session_state.last_feedback_time is not None:
    time_since = time.time() - st.session_state.last_feedback_time
    if time_since < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - time_since)
        st.warning(f"Feedback cooldown: {remaining // 60} min {remaining % 60} sec left")
        can_feedback = False

if st.button("Send Feedback", disabled=not can_feedback):
    if feedback_text.strip():
        feedback_row = [
            dt.now().strftime("%m/%d/%Y %H:%M:%S"),   # Timestamp
            feedback_text.strip(),
            dt.now().strftime("%m/%d/%Y %H:%M:%S")    # Submitted_At
        ]

        if GOOGLE_SHEETS_ENABLED:
            try:
                # Open the "Feedback" tab
                feedback_worksheet = sh.worksheet("Feedback")
                feedback_worksheet.append_row(feedback_row, value_input_option="USER_ENTERED")
                st.success("✅ Submitted successfully. Awaiting review by admin.")
            except Exception as e:
                st.error(f"Feedback upload failed: {e}")
        else:
            st.error("Google Sheets connection is not active. Please contact the admin.")

        st.session_state.last_feedback_time = time.time()
    else:
        st.warning("Please type something before sending.")

st.caption("")
st.markdown("---")
st.caption("Built with ❤️ for the 2A communit-ahy. No more left or right, lets follow in George Washington's footsteps! Be PRO-USA!")
