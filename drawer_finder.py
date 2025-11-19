import streamlit as st
import json
import os
import hashlib
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "drawer_data.json"
USER_FILE = "users.json"
ADMIN_USER = "admin"
# In a real app, store this in st.secrets
DEFAULT_ADMIN_PASS = "admin123" 

# --- AUTHENTICATION UTILS ---

def make_hashes(password):
    """Generate a SHA-256 hash of the password."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    """Check if entered password matches the stored hash."""
    if make_hashes(password) == hashed_text:
        return True
    return False

def load_users():
    """Load users from JSON file. Create default admin if not exists."""
    if not os.path.exists(USER_FILE):
        # Initialize with a default admin
        default_users = {
            ADMIN_USER: {
                "name": "sysAdmin",
                "password": make_hashes(DEFAULT_ADMIN_PASS),
                "role": "admin"
            }
        }
        with open(USER_FILE, 'w') as f:
            json.dump(default_users, f)
        return default_users
    
    with open(USER_FILE, 'r') as f:
        return json.load(f)

def save_user(username, name, password, role="user"):
    users = load_users()
    if username in users:
        return False, "Username already exists."
    
    users[username] = {
        "name": name,
        "password": make_hashes(password),
        "role": role
    }
    with open(USER_FILE, 'w') as f:
        json.dump(users, f)
    return True, "User created successfully."

# --- DATABASE UTILS ---
# NOTE: If hosting on Streamlit Cloud, replace these functions 
# to read/write from Google Sheets or Firestore instead of a local JSON file.

def load_data():
    """Load inventory data."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_item(item_name, drawer_number, notes, user):
    """Add a new item."""
    data = load_data()
    entry = {
        "item": item_name,
        "drawer": drawer_number,
        "notes": notes,
        "added_by": user,
        "timestamp": str(datetime.now())
    }
    data.append(entry)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def delete_item(index):
    """Delete an item by index."""
    data = load_data()
    if 0 <= index < len(data):
        data.pop(index)
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)

# --- UI SECTIONS ---

def login_page():
    st.title("🔐 Drawer Finder Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            users = load_users()
            if username in users:
                if check_hashes(password, users[username]['password']):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = users[username]['role']
                    st.success(f"Welcome back, {users[username]['name']}!")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("User not found.")

def main_app():
    st.sidebar.title(f"👤 {st.session_state['username']}")
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    menu = ["🔍 Find Item", "➕ Add Item", "📦 View All"]
    
    # Add Admin menu only if user is admin
    if st.session_state.get('role') == 'admin':
        menu.append("🛡️ Admin Panel")
        
    choice = st.sidebar.radio("Menu", menu)

    # --- FIND ITEM ---
    if choice == "🔍 Find Item":
        st.title("Find an Item")
        search_term = st.text_input("What are you looking for?", placeholder="e.g., Batteries, Passport...")
        
        data = load_data()
        if search_term:
            # Filter data
            results = [d for d in data if search_term.lower() in d['item'].lower() or search_term.lower() in d['notes'].lower()]
            
            if results:
                st.success(f"Found {len(results)} items:")
                for i, res in enumerate(results):
                    with st.container():
                        st.markdown(f"### **{res['item']}** in **Drawer {res['drawer']}**")
                        st.caption(f"Notes: {res['notes']}")
                        st.text(f"Added by {res['added_by']}")
                        st.divider()
            else:
                st.warning("No items found. Check the spelling or add it!")
        else:
            st.info("Enter a keyword above to search.")

    # --- ADD ITEM ---
    elif choice == "➕ Add Item":
        st.title("Add to Inventory")
        with st.form("add_item_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                item_name = st.text_input("Item Name (Required)")
            with col2:
                drawer_num = st.selectbox("Drawer #", list(range(1, 21))) # 20 Drawers
            
            notes = st.text_area("Description / Keywords")
            submitted = st.form_submit_button("Save Item")
            
            if submitted:
                if item_name:
                    save_item(item_name, drawer_num, notes, st.session_state['username'])
                    st.success(f"Saved **{item_name}** to Drawer {drawer_num}")
                else:
                    st.error("Please enter an item name.")

    # --- VIEW ALL ---
    elif choice == "📦 View All":
        st.title("All Inventory")
        data = load_data()
        if data:
            df = pd.DataFrame(data)
            # Reorder columns for display
            df = df[['drawer', 'item', 'notes', 'added_by', 'timestamp']]
            st.dataframe(df, use_container_width=True)
            
            with st.expander("🗑️ Delete Items"):
                st.warning("Be careful, this cannot be undone.")
                # Create a list of formatted strings for the deletion selector
                options = [f"{i}: {d['item']} (Drawer {d['drawer']})" for i, d in enumerate(data)]
                selected_to_delete = st.selectbox("Select item to delete", options)
                
                if st.button("Delete Selected Item"):
                    index = int(selected_to_delete.split(":")[0])
                    delete_item(index)
                    st.success("Item deleted!")
                    st.rerun()
        else:
            st.info("Inventory is empty.")

    # --- ADMIN PANEL ---
    elif choice == "🛡️ Admin Panel":
        st.title("User Management")
        st.write("Create new credentials for family members/users here.")
        
        with st.form("create_user"):
            new_user = st.text_input("New Username")
            new_name = st.text_input("Display Name")
            new_pass = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            create_btn = st.form_submit_button("Create User")
            
            if create_btn:
                if new_user and new_pass:
                    success, msg = save_user(new_user, new_name, new_pass, new_role)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Username and Password are required.")

# --- APP ENTRY POINT ---
if __name__ == '__main__':
    st.set_page_config(page_title="Drawer Finder", page_icon="🗄️")
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login_page()
    else:
        main_app()
