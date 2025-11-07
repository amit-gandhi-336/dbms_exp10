import streamlit as st
import mysql.connector
import pandas as pd
import datetime

# --- Database Connection and Credential Management ---
def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        return mysql.connector.connect(
            host="sql12.freesqldatabase.com",
            user="sql12806488",
            password="U3FCfx2g9d",
            database="sql12806488"
            port='3306'
        )
    except mysql.connector.Error as err:
        st.error(f"Database connection failed: {err}")
        return None

# --- Session Management ---

def do_logout():
    """Resets session state to log out the user."""
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.app_view = "login"
    st.success("Successfully logged out. Redirecting...")
    st.rerun()

# --- Data Fetching & Modification Functions (No Change) ---

def authenticate_user(username, password):
    db = get_db_connection()
    if not db: return None
    
    cursor = db.cursor(dictionary=True)
    query = "SELECT password_hash, user_id, role_id FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    db.close()

    if result:
        stored_password = result['password_hash']
        if isinstance(stored_password, bytes):
            stored_password = stored_password.decode('utf-8')
            
        if password == stored_password:
            return {'user_id': result['user_id'], 'role_id': result['role_id'], 'username': username}
    return None

def register_user(username, email, password):
    db = get_db_connection()
    if not db: return "Database unavailable."
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
    if cursor.fetchone():
        cursor.close(); db.close()
        return "Username or email already exists."
        
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, %s)",
            (username, email, password, 2) 
        )
        db.commit()
        return "Registration successful! You can now log in."
    except mysql.connector.Error as err:
        return f"Registration failed due to database error: {err}"
    finally:
        cursor.close(); db.close()

def add_vehicle(user_id, make, model, year, registration_number):
    db = get_db_connection()
    if not db: return "Database unavailable."

    cursor = db.cursor()
    try:
        cursor.execute("SELECT vehicle_id FROM vehicles WHERE registration_number = %s", (registration_number,))
        if cursor.fetchone():
            return "Error: Vehicle with this registration number already exists."
            
        cursor.execute(
            "INSERT INTO vehicles (user_id, make, model, year, registration_number) VALUES (%s, %s, %s, %s, %s)",
            (user_id, make, model, year, registration_number)
        )
        db.commit()
        return "Vehicle added successfully!"
    except mysql.connector.Error as err:
        return f"Failed to add vehicle: {err}"
    finally:
        cursor.close(); db.close()

def get_all_policies():
    db = get_db_connection()
    if not db: return []
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT policy_id, policy_name, premium FROM policies")
    policies = cursor.fetchall()
    cursor.close(); db.close()
    return policies

def assign_policy_to_vehicle(vehicle_id, policy_id):
    db = get_db_connection()
    if not db: return "Database unavailable."

    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT vehicle_id FROM vehicle_policies WHERE vehicle_id = %s AND status = 'Active'", 
            (vehicle_id,)
        )
        if cursor.fetchone():
             return "Error: Vehicle already has an active policy. Please manage existing one."
             
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=365)
        
        cursor.execute(
            "INSERT INTO vehicle_policies (vehicle_id, policy_id, start_date, end_date, status) VALUES (%s, %s, %s, %s, 'Active')",
            (vehicle_id, policy_id, start_date, end_date)
        )
        db.commit()
        return "Policy assigned successfully!"
    except mysql.connector.Error as err:
        return f"Failed to assign policy: {err}"
    finally:
        cursor.close(); db.close()

def fetch_user_vehicles(user_id):
    db = get_db_connection()
    if not db: return []
    cursor = db.cursor(dictionary=True) 
    query = """
    SELECT v.vehicle_id, v.make, v.model, v.year, v.registration_number,
           p.policy_name, p.coverage, p.premium, 
           vp.start_date, vp.end_date, vp.status
    FROM vehicles v
    LEFT JOIN vehicle_policies vp ON v.vehicle_id = vp.vehicle_id AND vp.status = 'Active'
    LEFT JOIN policies p ON vp.policy_id = p.policy_id
    WHERE v.user_id = %s
    ORDER BY v.vehicle_id
    """
    try:
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        st.error(f"Error fetching data: {err}")
        rows = []
    finally:
        cursor.close(); db.close()
    return rows

def fetch_all_users_vehicles():
    db = get_db_connection()
    if not db: return []
    cursor = db.cursor(dictionary=True) 
    query = """
    SELECT u.user_id, u.username, u.email, 
           v.vehicle_id, v.make, v.model, v.registration_number, v.year,
           p.policy_name, p.premium, vp.status, vp.end_date
    FROM users u
    LEFT JOIN vehicles v ON u.user_id = v.user_id
    LEFT JOIN vehicle_policies vp ON v.vehicle_id = vp.vehicle_id AND vp.status = 'Active'
    LEFT JOIN policies p ON vp.policy_id = p.policy_id
    ORDER BY u.user_id
    """
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except mysql.connector.Error as err:
        st.error(f"Error fetching all data: {err}")
        rows = []
    finally:
        cursor.close(); db.close()
    return rows

# --- Streamlit UI Components (Logged In Views) ---

def user_dashboard_view():
    st.header(f"👋 Welcome, {st.session_state.user_info['username'].upper()}")
    
    # 🚗 Sidebar Navigation
    with st.sidebar:
        st.subheader("Actions")
        if st.button("Add New Vehicle", key="nav_add_vehicle", use_container_width=True, type="primary"):
            st.session_state.app_view = "add_vehicle"
            st.rerun()
        st.markdown("---")
        if st.button("Logout", key="nav_logout_user", use_container_width=True, type="secondary"):
            do_logout()
    
    st.markdown("---")

    st.subheader("🚗 Your Vehicles and Policies Overview")
    
    user_id = st.session_state.user_info['user_id']
    vehicle_data = fetch_user_vehicles(user_id)
    all_policies = get_all_policies()
    
    if not vehicle_data:
        st.warning("You currently have no vehicles registered. Please use the **Add New Vehicle** button in the sidebar.")
    
    # Vehicle List (Wider & Centered: 1:2:1)
    col_dash_1, col_dash_2, col_dash_3 = st.columns([1, 2, 1])
    
    with col_dash_2:
        for vehicle in vehicle_data:
            # Vehicle Title
            st.markdown(f"**<div style='text-align: center;'>{vehicle['make']} {vehicle['model']} ({vehicle['registration_number']})</div>**", unsafe_allow_html=True)
            
            # Policy Management Section
            with st.expander(f"Details for {vehicle['registration_number']}", expanded=False):
                st.markdown(f"**Policy:** {'**'+vehicle['policy_name']+'**' if vehicle['policy_name'] else '*None*'}")
                st.markdown(f"**Status:** {vehicle['status'] or 'N/A'}")
                if vehicle['end_date']:
                    st.markdown(f"**Ends On:** {vehicle['end_date'].strftime('%Y-%m-%d')}")
                if vehicle['premium']:
                    st.markdown(f"**Premium:** ${vehicle['premium']:.2f}")

                st.caption("Policy Management")
                policy_options = {p['policy_name']: p['policy_id'] for p in all_policies}
                policy_names = list(policy_options.keys())
                
                if policy_names:
                    selected_policy_name = st.selectbox(
                        "Select Policy Type:", 
                        ['Select Policy'] + policy_names,
                        key=f"policy_{vehicle['vehicle_id']}"
                    )
                    
                    if st.button("Assign Policy", key=f"assign_btn_{vehicle['vehicle_id']}", type="primary", use_container_width=True):
                        if selected_policy_name != 'Select Policy':
                            policy_id = policy_options[selected_policy_name]
                            result = assign_policy_to_vehicle(vehicle['vehicle_id'], policy_id)
                            if "successfully" in result:
                                st.success(f"Policy assignment for {vehicle['registration_number']} successful!")
                                st.rerun() 
                            else:
                                st.error(result)
                        else:
                            st.warning("Please select a policy type.")
                else:
                    st.warning("No policies are currently available.")
            st.markdown("<hr style='border: 1px solid #ccc;'>", unsafe_allow_html=True) # Custom separator


def add_vehicle_view():
    st.header("➕ Register a New Vehicle")
    
    # 🚗 Sidebar Navigation
    with st.sidebar:
        st.subheader("Actions")
        if st.button("Add New Vehicle", key="nav_add_vehicle_sidebar", use_container_width=True, type="primary"):
            st.session_state.app_view = "add_vehicle"
            st.rerun()
        st.markdown("---")
        if st.button("Logout", key="nav_logout_user_sidebar", use_container_width=True, type="secondary"):
            do_logout()
    
    # Back button centered (Wider: 1:2:1)
    col_back_1, col_back_2, col_back_3 = st.columns([1, 2, 1])
    with col_back_2:
        if st.button("← Back to My Vehicles", key="back_to_dash", use_container_width=True):
            st.session_state.app_view = "dashboard"
            st.rerun()
        
    st.markdown("---")
    
    # Wider and Centered Form (1:2:1)
    col_space_1, col_content, col_space_2 = st.columns([1, 2, 1])
    
    with col_content:
        with st.container(border=True):
            st.subheader("Vehicle Details")
            
            current_year = datetime.datetime.now().year

            user_id = st.session_state.user_info['user_id']
            
            make = st.text_input("Make (e.g., Toyota)", key="v_make")
            model = st.text_input("Model (e.g., Camry)", key="v_model")
            year = st.number_input("Year", min_value=1900, max_value=current_year + 1, value=current_year, step=1, key="v_year")
            registration_number = st.text_input("Registration Number (e.g., ABC-123)", key="v_reg_num").upper()
            
            if st.button("Add Vehicle to Account", use_container_width=True, type="primary"):
                if not all([make, model, registration_number]):
                    st.error("Please fill in all vehicle details.")
                else:
                    result = add_vehicle(user_id, make, model, year, registration_number)
                    if "successful" in result:
                        st.success(result)
                        st.session_state.app_view = "dashboard" 
                        st.rerun()
                    else:
                        st.error(result)

def admin_dashboard_view():
    st.header("👑 Admin Dashboard")
    
    # 👑 Sidebar Navigation
    with st.sidebar:
        st.subheader("Actions")
        # No 'Add Vehicle' for admin, just Logout
        st.info("Admin functionality here...")
        st.markdown("---")
        if st.button("Logout", key="nav_logout_admin", use_container_width=True, type="secondary"):
            do_logout()
            
    st.markdown("---")

    st.subheader("All User Data Overview")
    
    # Selector centered (Wider: 1:2:1)
    col_select_1, col_select_2, col_select_3 = st.columns([1, 2, 1])
    
    data = fetch_all_users_vehicles()
    
    if not data:
        st.warning("No user data found.")
        return

    df = pd.DataFrame(data).fillna({'vehicle_id': 'No Vehicle', 'make': 'N/A', 'policy_name': 'None', 'status': 'N/A'})

    users = df[['user_id', 'username', 'email']].drop_duplicates().to_dict('records')
    user_names = {user['user_id']: f"{user['username']} ({user['email']})" for user in users}
    
    with col_select_2:
        selected_user_id = st.selectbox(
            "Select a User to view their Vehicles:",
            options=[None] + list(user_names.keys()),
            format_func=lambda x: user_names.get(x, "Select User")
        )
    
    # Table uses full width for readability
    if selected_user_id:
        st.markdown(f"### Vehicles for {user_names[selected_user_id]}")
        user_vehicles = df[df['user_id'] == selected_user_id]
        
        if not user_vehicles.empty:
            display_df = user_vehicles[[
                'registration_number', 'make', 'model', 'year', 'policy_name', 'premium', 'status', 'end_date'
            ]].copy()
            display_df.rename(columns={
                'registration_number': 'Reg. No.',
                'policy_name': 'Policy Name',
                'end_date': 'Policy End'
            }, inplace=True)
            display_df['premium'] = display_df['premium'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else 'N/A')
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"{user_names[selected_user_id]} has no vehicles registered.")

# --- Initial Views (Login/Register) ---

def show_register_view():
    """Renders the registration form, wider and centered (1:2:1)."""
    
    # Use 3 columns to center the form (ratio 1:2:1)
    col_space_1, col_content, col_space_2 = st.columns([1, 2, 1])
    
    with col_content:
        st.header("📝 Create a New Account")
        with st.container(border=True):
            reg_username = st.text_input("New Username", key="reg_username")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password (Stored Plaintext)", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            
            if st.button("Create Account", use_container_width=True, type="primary"):
                if reg_password != reg_confirm_password:
                    st.error("Passwords do match.")
                elif not all([reg_username, reg_email, reg_password, reg_confirm_password]):
                    st.error("Please fill all fields.")
                else:
                    result = register_user(reg_username, reg_email, reg_password)
                    if "successful" in result:
                        st.success(result)
                        st.session_state.app_view = "login"
                        st.rerun()
                    else:
                        st.error(result)
        
        st.markdown("---")
        if st.button("Already have an account? Login here.", key="back_to_login", use_container_width=True):
            st.session_state.app_view = "login"
            st.rerun()

def show_login_view():
    """Renders the login box, wider and centered (1:2:1), with the register link."""
    
    # Use 3 columns to center the form (ratio 1:2:1)
    col_space_1, col_content, col_space_2 = st.columns([1.5, 1, 1.5])
    
    with col_content:
        st.header("🔑 Insurance Portal Login")
        
        with st.container(border=True):
            st.markdown('<span style="font-size: 24px;">Username</span>', unsafe_allow_html=True)
            username = st.text_input("", key="login_username")
            st.text("")
            st.text("")
            st.text("")
            st.markdown('<span style="font-size: 24px;">Password</span>', unsafe_allow_html=True)   
            password = st.text_input('',key='login_password',type='password')
            st.text("")
            st.text("")
            st.text("")
            
            if st.button("Sign In", use_container_width=True, type="primary"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.app_view = "dashboard" 
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        st.markdown("---")
        
        if st.button("Don't have an account? **Register a New Account**", key="switch_to_register", use_container_width=True):
            st.session_state.app_view = "register"
            st.rerun()

# --- Main App Execution ---

def app():
    st.set_page_config(page_title="Insurance Portal", layout="wide") 
    
    col_title_1, col_title_2, col_title_3 = st.columns([1, 2, 1])
    with col_title_2:
        st.title("🛡️ Insurance Policy Portal")
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.app_view = "login" 
        
    st.markdown("---")
        
    if st.session_state.logged_in:
        role_id = st.session_state.user_info['role_id']
        
        if role_id == 1: # Admin
            admin_dashboard_view()
        elif role_id == 2: # User
            if st.session_state.app_view == "add_vehicle":
                add_vehicle_view()
            else:
                user_dashboard_view()
    else:
        if st.session_state.app_view == "register":
            show_register_view()
        else:
            show_login_view()

if __name__ == "__main__":
    app()