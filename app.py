#streamlit run app.py
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import hashlib
from datetime import datetime, timedelta
import plotly.graph_objects as go
import re
import string
import random


# Load environment variables from the .env file
load_dotenv()

# Get the MongoDB connection URL from the environment variable
mongo_url = os.getenv("MONGO_PWD_URL")

# MongoDB setup 
client = MongoClient(mongo_url)

 
db = client["workflow_management"]

def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load CSS file
load_css("style.css")



def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def password_is_valid(password):
    """Check if the password meets the criteria."""
    if (len(password) >= 15 and 
        re.search(r"[A-Z]", password) and
        re.search(r"[a-z]", password) and
        re.search(r"\d", password) and
        re.search(r"[^\w\s]", password)):
        return True
    return False

# Pages

def register_page():
    st.title("Register")
    user_name = st.text_input("User Name")
    email = st.text_input("Email (User ID)")
    password = st.text_input("Password", type="password")
    role = "employee"  # Fixed role as employee
    st.text_input("Role", value=role, disabled=True)  # Disabled role input
    
    # Password requirements message
    st.info("Password must be at least 15 characters long, include uppercase letters, lowercase letters, special characters, and numbers.")

    if st.button("Register"):
        # Check if email is valid
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            st.error("Invalid email address.")
            return

        # Check if password meets requirements
        if len(password) < 15:
            st.error("Password must be at least 15 characters long.")
            return
        if not re.search(r"[A-Z]", password):
            st.error("Password must contain at least one uppercase letter.")
            return
        if not re.search(r"[a-z]", password):
            st.error("Password must contain at least one lowercase letter.")
            return
        if not re.search(r"[0-9]", password):
            st.error("Password must contain at least one number.")
            return
        if not re.search(r"[\W_]", password):  # \W matches any non-word character (special characters)
            st.error("Password must contain at least one special character.")
            return

        # Save to DB
        users_collection = db["users"]
        if users_collection.find_one({"UserID": email}):
            st.warning("User already exists!")
        else:
            users_collection.insert_one({
                "User Name": user_name,
                "UserID": email,
                "Password": hash_password(password),
                "Role": role
            })
            st.success("User registered successfully!")



def login_page():
    st.title("Login")
    email = st.text_input("Email (User ID)")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        users_collection = db["users"]
        user = users_collection.find_one({"UserID": email, "Password": hash_password(password)})
        if user:
            st.session_state["logged_in"] = True
            st.session_state["user"] = user
            st.experimental_rerun()
        else:
            st.error("Invalid email or password")



def profile_page():
    st.title("Profile Page")
    
    if "user" not in st.session_state:
        st.error("You must be logged in to view this page.")
        return

    user_id = st.session_state["user"]["UserID"]
    user = db["users"].find_one({"UserID": user_id})
    
    if not user:
        st.error("User details not found.")
        return
    
    # Display user details
    st.subheader("User Details")
    st.write(f"**UserID:** {user['UserID']}")
    st.write(f"**Name:** {user['User Name']}")
    st.write(f"**Role:** {user['Role'].capitalize()}")

    # Section for changing password
    st.subheader("Change Password")
    
    # Password requirements message
    st.info("Password must be at least 15 characters long, include uppercase letters, lowercase letters, special characters, and numbers.")

    # Using a form to handle the password change inputs
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")
        change_password_button = st.form_submit_button("Change Password")

    # Handle form submission
    if change_password_button:
        if user["Password"] != hash_password(current_password):
            st.error("Current password is incorrect.")
        elif new_password != confirm_new_password:
            st.error("New passwords do not match.")
        elif not password_is_valid(new_password):
            st.error("New password must be at least 15 characters long, "
                     "include uppercase and lowercase letters, numbers, and special characters.")
        else:
            new_hashed_password = hash_password(new_password)
            result = db["users"].update_one({"UserID": user_id}, {"$set": {"Password": new_hashed_password}})
            if result.modified_count == 1:
                st.session_state["password_change_success"] = True
                st.session_state["current_page"] = "Profile"
                st.rerun()
            else:
                st.error("Error updating password. Please try again.")

    # Display success message if password was changed successfully
    if st.session_state.get("password_change_success"):
        st.success("Password changed successfully!")
        st.session_state["password_change_success"] = False



def generate_project_id():
    """Generate a random 5-character project ID consisting of uppercase letters and/or digits."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=5))



def project_management_page():
    st.title("Project Management")

    if "user" not in st.session_state or st.session_state["user"]["Role"] not in ["admin", "project_manager"]:
        st.error("Access denied")
        return

    projects_collection = db["projects"]
    users_collection = db["users"]
    project_users_collection = db["project_users"]
    tasks_collection = db["tasks"]  # Add this line to define the tasks_collection

    # Get the logged-in user's ID and role
    logged_in_user_id = st.session_state["user"].get("UserID", "")
    logged_in_user_role = st.session_state["user"].get("Role", "")

    # Divide the page into different sections using columns and containers
    with st.container():
        st.header("Current Projects")

        if logged_in_user_role == "admin":
            user_projects = list(projects_collection.find())
        else:
            user_projects = list(project_users_collection.find({"UserID": logged_in_user_id}))

        user_project_ids = [project["Project ID"] for project in user_projects]

        if user_project_ids:
            # Display each project as a styled box
            for project_id in user_project_ids:
                st.markdown(f'<div class="project-id-box">{project_id}</div>', unsafe_allow_html=True)
        else:
            st.write("You are not involved in any projects.")

    # Section for adding new projects
    st.markdown("---")
    with st.container():
        st.header("Add New Project")

        # Columns for input fields
        col1, col2 = st.columns(2)
        with col1:
            project_id = st.text_input("Project ID (5 characters, uppercase letters or digits)", max_chars=5)
            if len(project_id) != 5 or not project_id.isalnum() or not any(char.isupper() for char in project_id):
                st.warning("Project ID must be 5 characters long and contain only uppercase letters and/or digits.")

        with col2:
            project_managers = list(users_collection.find({"Role": "project_manager"}))
            project_manager_names = [f"{pm['User Name']} - {pm['UserID']}" for pm in project_managers]
            selected_project_manager = st.selectbox("Select Project Manager", project_manager_names)

        # Button to add project
        if st.button("Add Project") and len(project_id) == 5 and project_id.isalnum() and any(char.isupper() for char in project_id):
            if projects_collection.find_one({"Project ID": project_id}):
                st.warning("Project ID already exists!")
            else:
                project_manager_name, project_manager_id = selected_project_manager.split(" - ")
                project_manager_display = f"{project_manager_name} - {project_manager_id}"

                projects_collection.insert_one({
                    "Project ID": project_id,
                    "Project Manager": project_manager_display
                })
                project_users_collection.insert_one({
                    "Project ID": project_id,
                    "UserID": project_manager_id
                })
                st.success("Project and Project Manager added successfully!")
                st.rerun()

    # Section for adding and displaying users in projects
    st.markdown("---")
    with st.container():
        st.header("Add Users into the Project")
        if user_project_ids:
            selected_project_id = st.selectbox("Select Project ID", user_project_ids, key="add_and_view_users_project_select")

            if selected_project_id:
                all_users = list(users_collection.find({"Role": "employee"}))
                project_users = list(project_users_collection.find({"Project ID": selected_project_id}))

                assigned_user_ids = [user["UserID"] for user in project_users]
                unassigned_users = [user for user in all_users if user["UserID"] not in assigned_user_ids]

                user_to_add = st.selectbox(
                    "Select User to Add",
                    [f"{user['User Name']} - {user['UserID']}" for user in unassigned_users]
                )

                if st.button("Add User to Project"):
                    if user_to_add:
                        user_id_to_add = user_to_add.split(" - ")[-1]
                        project_users_collection.insert_one({
                            "Project ID": selected_project_id,
                            "UserID": user_id_to_add
                        })
                        st.success(f"User {user_id_to_add} added to project {selected_project_id}!")
                        st.rerun()
                    else:
                        st.warning("No user selected to add.")

                if project_users:
                    project_manager_info = projects_collection.find_one({"Project ID": selected_project_id})
                    project_manager_display = project_manager_info["Project Manager"]
                    project_manager_id = project_manager_display.split(" - ")[-1]

                    st.markdown(f"**Project Manager:** {project_manager_display}")

                    for user in project_users:
                        if user["UserID"] != project_manager_id:
                            user_info = users_collection.find_one({"UserID": user["UserID"]})
                            if user_info:
                                st.markdown(f"**{user_info['User Name']} - {user_info['UserID']}**")
                else:
                    st.write("No users assigned to this project yet.")
        else:
            st.write("No projects available.")

    # Section for removing projects (Admin only)
    st.markdown("---")
    if logged_in_user_role == "admin":
        with st.container():
            st.header("Remove Project")

            all_projects = list(projects_collection.find())
            all_project_ids = [project["Project ID"] for project in all_projects]

            if all_project_ids:
                selected_project_id = st.selectbox("Select Project ID to Remove", all_project_ids, key="remove_project_select")
                if st.button("Remove Project"):
                    projects_collection.delete_one({"Project ID": selected_project_id})
                    project_users_collection.delete_many({"Project ID": selected_project_id})
                    tasks_collection.delete_many({"Project ID": selected_project_id})
                    st.success(f"Project {selected_project_id} and all related data have been removed successfully!")
                    st.rerun()
            else:
                st.write("No projects available to remove.")



def task_management_page():
    st.title("Task Management")
    
    # Get collections
    projects_collection = db["projects"]
    users_collection = db["users"]
    tasks_collection = db["tasks"]
    project_users_collection = db["project_users"]

    # Get logged-in user's ID and Role
    user_id = st.session_state["user"]["UserID"]
    user_role = st.session_state["user"]["Role"]
    user_name = st.session_state["user"]["User Name"]

    # Find projects where the user is involved
    if user_role == "admin":
        user_projects = list(projects_collection.find())
    else:
        user_projects = list(project_users_collection.find({"UserID": user_id}))

    user_project_ids = [project["Project ID"] for project in user_projects]

    if not user_project_ids:
        st.warning("No projects found or you do not have permission to view them.")
        return

    # Select project
    st.write("### Projects")
    selected_project_id = st.selectbox("Select Project ID", user_project_ids)

    # Section 1: Add Task ID
    st.markdown("---")
    st.write("### Add Task")
    task_id = st.text_input("Task ID")
    task_due_date = st.date_input("Due Date")

    # Custom time input
    col1, col2, col3 = st.columns(3)
    with col1:
        due_hour = st.text_input("Hour (1-12)", "12")
    with col2:
        due_minute = st.text_input("Minute (00-59)", "00")
    with col3:
        am_pm = st.selectbox("AM/PM", ["AM", "PM"])

    # Convert input time to 24-hour format
    try:
        due_hour = int(due_hour)
        due_minute = int(due_minute)
        if am_pm == "PM" and due_hour != 12:
            due_hour += 12
        elif am_pm == "AM" and due_hour == 12:
            due_hour = 0
        due_time = datetime.strptime(f"{due_hour}:{due_minute}", "%H:%M").time()
    except ValueError:
        st.error("Invalid time entered. Please check the hour and minute values.")
        return

    if st.button("Add Task ID"):
        if not task_id.strip():
            st.warning("Task ID cannot be empty.")
        else:
            # Check for uniqueness of Task ID within the selected project
            existing_task = tasks_collection.find_one({"Task ID": task_id, "Project ID": selected_project_id})
            if existing_task:
                st.warning(f"Task ID '{task_id}' already exists in the selected project. Please choose a different ID.")
            else:
                due_datetime = datetime.combine(task_due_date, due_time)
                tasks_collection.insert_one({
                    "Task ID": task_id,
                    "Project ID": selected_project_id,
                    "Description": "",
                    "Assigned To": "",
                    "Status": "Not Started",
                    "Start Time": None,
                    "End Time": None,
                    "Time Spent": None,
                    "Due Date": due_datetime
                })
                st.session_state['task_added'] = True
                st.session_state['task_id'] = task_id
                st.rerun()  # Force rerun to show updated tasks

    # Check if a task was added successfully
    if st.session_state.get('task_added'):
        st.success(f"Task ID  '{st.session_state['task_id']}'  added successfully!")
        # Reset the session state
        st.session_state['task_added'] = False

    # Section 2: Assign Tasks
    st.markdown("---")
    st.write("### Assign Tasks")
    task_ids = [t["Task ID"] for t in tasks_collection.find({"Project ID": selected_project_id, "Assigned To": ""})]
    if task_ids:
        selected_task_id = st.selectbox("Select Task ID to Assign", task_ids)
        task_description = st.text_input("Task Description")

        # "Assign to" field logic
        if user_role == "employee":
            task_user = f"{user_name} - {user_id}"
            st.text_input("Assign to", task_user, disabled=True)
        else:
            # Fetch users assigned to the selected project
            assigned_users = list(project_users_collection.find({"Project ID": selected_project_id}))
            assigned_user_ids = [user["UserID"] for user in assigned_users]
            project_users = [user for user in users_collection.find({"UserID": {"$in": assigned_user_ids}})]
            task_user = st.selectbox("Assign to", [f"{u['User Name']} - {u['UserID']}" for u in project_users])
        
        task_status = st.selectbox("Status", ["Not Started", "In Progress", "Completed"])
        
        if st.button("Assign Task"):
            user_id_to_assign = user_id if user_role == "employee" else task_user.split(" - ")[-1]
            tasks_collection.update_one(
                {"Task ID": selected_task_id, "Project ID": selected_project_id},
                {"$set": {
                    "Description": task_description,
                    "Assigned To": user_id_to_assign,
                    "Status": task_status
                }}
            )
            st.success("Task assigned successfully!")
            st.rerun()  # Force rerun to show updated tasks
    else:
        st.write("No unassigned tasks available.")

    # Section 3: Show Unassigned Tasks
    st.markdown("---")
    st.write("### Unassigned Tasks")
    unassigned_tasks = list(tasks_collection.find({"Project ID": selected_project_id, "Assigned To": ""}))
    if unassigned_tasks:
        for task in unassigned_tasks:
            st.write(f"Task ID: {task['Task ID']} - Due Date: {task['Due Date']}")
    else:
        st.write("No unassigned tasks available.")


         
def task_status_update_page():
    st.title("Task Status Update")

    # Get collections
    tasks_collection = db["tasks"]
    project_users_collection = db["project_users"]
    projects_collection = db["projects"]

    # Get logged-in user's ID and Role
    user_id = st.session_state["user"]["UserID"]
    user_role = st.session_state["user"]["Role"]

    # Find projects where the user is involved
    if user_role == "admin":
        user_projects = list(project_users_collection.find())
    elif user_role == "project_manager":
        user_projects = list(projects_collection.find({"Project Manager": {"$regex": user_id}}))
    else:
        user_projects = list(project_users_collection.find({"UserID": user_id}))
    
    # Use a set to ensure unique project IDs
    user_project_ids = list(set(project["Project ID"] for project in user_projects))

    if not user_project_ids:
        st.warning("No projects found or you do not have permission to view them.")
        return

    # Select project
    st.write("### Projects")
    selected_project_id = st.selectbox("Select Project ID", user_project_ids)

    if selected_project_id:
        # Filter tasks by status
        status_filter = st.selectbox("Filter by Status", ["All", "Not Started", "In Progress", "Completed"])
        
        # Fetch tasks for the selected project
        if user_role in ["admin", "project_manager"]:
            if status_filter == "All":
                tasks = list(tasks_collection.find({"Project ID": selected_project_id}))
            else:
                tasks = list(tasks_collection.find({"Project ID": selected_project_id, "Status": status_filter}))
        else:
            if status_filter == "All":
                tasks = list(tasks_collection.find({"Project ID": selected_project_id, "Assigned To": user_id}))
            else:
                tasks = list(tasks_collection.find({"Project ID": selected_project_id, "Assigned To": user_id, "Status": status_filter}))
        
        st.markdown("---")
        if tasks:
            for i, task in enumerate(tasks):
                start_time = task.get("Start Time")
                end_time = task.get("End Time")
                time_spent = task.get("Time Spent")

                # Background color based on task status
                status_colors = {
                    "Not Started": "#FFCCCC",  # Light red
                    "In Progress": "#FFFF99",  # Light yellow
                    "Completed": "#CCFFCC"    # Light green
                }
                status_color = status_colors.get(task["Status"], "#FFFFFF")

                # Format the task information
                task_info = f"""
                **{task['Task ID']}**: {task['Description']} - {task.get('Assigned To', 'Unassigned')} - <span style="background-color: {status_color}; padding: 5px;">{task['Status']}</span>
                """
                st.markdown(task_info, unsafe_allow_html=True)
                
                # Display start and end times if available
                if start_time:
                    st.markdown(f"**Start Time:** {start_time}")
                if end_time:
                    st.markdown(f"**End Time:** {end_time}")
                if time_spent:
                    st.markdown(f"**Time Spent:** {time_spent:.2f} seconds")
                
                # Show buttons only if the logged-in user is assigned to the task and task is not completed
                if user_id == task.get("Assigned To") and task["Status"] != "Completed":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Start", key=f"start_{i}", disabled=start_time is not None):
                            start_time = datetime.now()
                            tasks_collection.update_one(
                                {"Task ID": task["Task ID"]}, 
                                {"$set": {"Status": "In Progress", "Start Time": start_time}}
                            )
                            st.rerun()
                    with col2:
                        if st.button("Complete", key=f"complete_{i}"):
                            end_time = datetime.now()
                            start_time = task.get("Start Time")
                            if start_time:
                                time_spent = (end_time - start_time).total_seconds()
                            else:
                                time_spent = None
                            tasks_collection.update_one(
                                {"Task ID": task["Task ID"]}, 
                                {"$set": {"Status": "Completed", "End Time": end_time, "Time Spent": time_spent}}
                            )
                            st.rerun()
                st.markdown("---")
        else:
            st.write("No tasks assigned yet.")



def dashboard_page():
    st.title("Workflow Management Dashboard")
    
    # Get collections
    projects_collection = db["projects"]
    tasks_collection = db["tasks"]
    project_users_collection = db["project_users"]

    # Get logged-in user's ID and Role
    user_id = st.session_state["user"]["UserID"]
    user_role = st.session_state["user"]["Role"]

    # List projects the user is involved in
    if user_role == "admin":
        user_projects = list(projects_collection.find())
    else:
        user_projects = list(project_users_collection.find({"UserID": user_id}))

    user_project_ids = [project["Project ID"] for project in user_projects]

    if user_project_ids:
        st.write("### Task Statistics")

        # Dropdown to select a project
        selected_project_id = st.selectbox("Select Project ID", user_project_ids)

        # Fetch selected project details
        project = projects_collection.find_one({"Project ID": selected_project_id})
        if project:
            tasks = list(tasks_collection.find({"Project ID": selected_project_id}))
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task["Status"] == "Completed")
            in_progress_tasks = sum(1 for task in tasks if task["Status"] == "In Progress")
            not_started_tasks = sum(1 for task in tasks if task["Status"] == "Not Started")
            overdue_tasks = sum(1 for task in tasks if task.get("Due Date") and task["Due Date"] < datetime.now() and task["Status"] != "Completed")
            
            # Task Summary Metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.markdown(f'<div class="metric-box metric-total-tasks">Total<br><span>{total_tasks}</span></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-box metric-completed-tasks">Completed<br><span>{completed_tasks}</span></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-box metric-ongoing-tasks">Ongoing<br><span>{in_progress_tasks}</span></div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="metric-box metric-not-started-tasks">Not Started<br><span>{not_started_tasks}</span></div>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<div class="metric-box metric-overdue-tasks">Overdue<br><span>{overdue_tasks}</span></div>', unsafe_allow_html=True)

            # Project Progress
            st.write("### Project Progress")
            if total_tasks > 0:
                progress = (completed_tasks / total_tasks) * 100
                st.progress(progress / 100)
                st.write(f"Completed Tasks: {progress:.2f}%")
            else:
                st.write("No tasks available for this project.")

            # Tasks Due Time
            st.write("### Tasks Due Time")
            current_time = datetime.now()
            due_in_1_hour = sum(1 for task in tasks if task.get("Due Date") and timedelta(hours=0) < (task["Due Date"] - current_time) <= timedelta(hours=1) and task["Status"] != "Completed")
            due_in_2_hours = sum(1 for task in tasks if task.get("Due Date") and timedelta(hours=1) < (task["Due Date"] - current_time) <= timedelta(hours=2) and task["Status"] != "Completed")
            due_in_4_hours = sum(1 for task in tasks if task.get("Due Date") and timedelta(hours=2) < (task["Due Date"] - current_time) <= timedelta(hours=4) and task["Status"] != "Completed")
            
            col6, col7, col8 = st.columns(3)
            with col6:
                st.metric(label="Due in 4 Hours", value=due_in_4_hours, delta=None)
            with col7:
                st.metric(label="Due in 2 Hours", value=due_in_2_hours, delta=None)
            with col8:
                st.metric(label="Due in 1 Hour", value=due_in_1_hour, delta=None)

            # Pie chart for task status distribution including overdue tasks
            if total_tasks > 0:
                fig = go.Figure(data=[go.Pie(labels=['Not Started', 'In Progress', 'Completed', 'Overdue'],
                                             values=[not_started_tasks, in_progress_tasks, completed_tasks, overdue_tasks],
                                             hole=.3)])
                fig.update_layout(title_text=f"Task Distribution for Project ID: {selected_project_id}")
                fig.update_traces(marker=dict(colors=['#c0c0c0', '#FFFF99', '#CCFFCC', '#FFCCCC']))
                st.plotly_chart(fig)

            # Upcoming Deadlines
            st.write("### Upcoming Deadlines (Next 24 Hours)")
            upcoming_tasks = [task for task in tasks if task.get("Due Date") and 0 < (task["Due Date"] - datetime.now()).total_seconds() <= 86400]
            if upcoming_tasks:
                for task in upcoming_tasks:
                    due_date = task["Due Date"]
                    time_remaining = due_date - datetime.now()
                    st.write(f"**{task['Task ID']}**: Due in {time_remaining} - {task['Status']}")
            else:
                st.write("No tasks due in the next 24 hours.")
            
            # Overdue Tasks Summary
            st.write("### Overdue Tasks Summary")
            if overdue_tasks > 0:
                overdue_tasks_list = [task for task in tasks if task.get("Due Date") and task["Due Date"] < datetime.now() and task["Status"] != "Completed"]
                for task in overdue_tasks_list:
                    due_date = task["Due Date"]
                    st.write(f"**{task['Task ID']}**: Due on {due_date} - {task['Status']}")
            else:
                st.write("No overdue tasks.")

            # Task Completion Trend (Last 7 Days)
            st.write("### Task Completion Trend")
            today = datetime.now()
            last_week = today - timedelta(days=7)
            tasks_last_week = list(tasks_collection.find({"Project ID": selected_project_id, "Status": "Completed", "End Time": {"$gte": last_week}}))
            task_dates = [task["End Time"].date() for task in tasks_last_week if "End Time" in task]
            date_count = {date: task_dates.count(date) for date in set(task_dates)}

            # Prepare data for line chart
            dates = [(last_week + timedelta(days=i)).date() for i in range(8)]
            counts = [date_count.get(date, 0) for date in dates]

            fig = go.Figure(data=[go.Scatter(x=dates, y=counts, mode='lines+markers')])
            fig.update_layout(title="Tasks Completed in the Last 7 Days", xaxis_title="Date", yaxis_title="Number of Tasks")
            st.plotly_chart(fig)

            # Resource Allocation
            st.write("### Resource Allocation")
            task_users = [task.get("Assigned To") for task in tasks if task.get("Assigned To")]
            user_counts = {user: task_users.count(user) for user in set(task_users)}
            for user, count in user_counts.items():
                user_info = db["users"].find_one({"UserID": user})
                user_name = user_info.get("User Name", "Unknown User")
                st.write(f"{user_name} - {user} : {count} tasks")

        else:
            st.warning("Project not found.")
    else:
        st.warning("No projects found or you do not have permission to view them.")



def user_management_page():
    st.title("User Management")

    if "user" not in st.session_state or st.session_state["user"]["Role"] != "admin":
        st.error("Access denied")
        return

    users_collection = db["users"]

    # Fetch all users
    all_users = list(users_collection.find())

    if not all_users:
        st.write("No users found.")
        return

    # Create a dropdown to select a user
    user_names = [f"{user['User Name']} - {user['UserID']}" for user in all_users]
    selected_user = st.selectbox("Select User", user_names)

    if selected_user:
        # Extract the user ID of the selected user
        selected_user_id = selected_user.split(" - ")[-1]

        # Fetch the user's details from the database
        user = users_collection.find_one({"UserID": selected_user_id})

        if not user:
            st.error("User not found.")
            return

        # Display the current role of the selected user
        st.write(f"**Current Role:** {user['Role'].capitalize()}")

        # Allow the admin to change the role
        new_role = st.selectbox("Change Role", ["admin", "project_manager", "employee"], index=["admin", "project_manager", "employee"].index(user["Role"]))

        if st.button("Update Role"):
            if new_role != user["Role"]:
                users_collection.update_one({"UserID": selected_user_id}, {"$set": {"Role": new_role}})
                st.success(f"Role updated to {new_role} for user {user['User Name']} - {user['UserID']}")
                # Display a success message
                st.success("User role updated successfully!")
                
            else:
                st.warning("No changes made to the role.")





# main function
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        user_name = st.session_state["user"].get("User Name", "User")
        user_role = st.session_state["user"]["Role"]
        st.sidebar.title(f"Welcome, {user_name}")

        # Navigation based on user role
        if user_role == "admin":
            page = st.sidebar.radio("Navigation", ["Project Management", "Task Management", "Task Status Update", "Dashboard", "User Management", "Profile"], key="main_navigation")
        elif user_role == "project_manager":
            page = st.sidebar.radio("Navigation", ["Project Management", "Task Management", "Task Status Update", "Dashboard", "Profile"], key="main_navigation")
        elif user_role == "employee":
            page = st.sidebar.radio("Navigation", ["Task Management", "Task Status Update", "Dashboard", "Profile"], key="main_navigation")

        # Logout button
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state.pop("user", None)
            st.session_state.pop("current_page", None)
            st.rerun()
        
        # Render the selected page based on `page`
        if page == "Profile":
            profile_page()
        elif page == "Project Management":
            project_management_page()
        elif page == "Task Management":
            task_management_page()
        elif page == "Task Status Update":
            task_status_update_page()
        elif page == "Dashboard":
            dashboard_page()
        elif page == "User Management":
            user_management_page()
    else:
        page = st.sidebar.radio("Select a page", ["Login", "Register"], key="auth_navigation")
        if page == "Login":
            login_page()
        elif page == "Register":
            register_page()

if __name__ == "__main__":
    main()
