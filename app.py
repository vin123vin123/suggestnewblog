import streamlit as st
from pymongo import MongoClient
from bson.binary import Binary
import io
from PIL import Image
from datetime import datetime
from streamlit_quill import st_quill  # Visual Rich Text Editor
import bcrypt  # Secure password hashing

# 1. Config Database Connection with Caching
@st.cache_resource
def init_connection():
    # Replace with your MongoDB Atlas string if deploying to the cloud
    return MongoClient("mongodb://localhost:27017/")

client = init_connection()
db = client["rich_blog_db"]
posts_collection = db["posts"]
users_collection = db["users"]  # New collection for secure user credentials

# App styling and Title
st.set_page_config(page_title="DevBlog CMS", page_icon="📝", layout="centered")
st.title("📝 DevBlog: Secure Rich Content CMS")

# Initialize Session State variables for tracking logged-in state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# --- SIDEBAR: AUTHENTICATION INTERFACE ---
st.sidebar.title("🔐 Account Access")

if not st.session_state.logged_in:
    auth_mode = st.sidebar.radio("Sign In / Sign Up", ["Login", "Register"])
    
    username_input = st.sidebar.text_input("Username", key="auth_user")
    password_input = st.sidebar.text_input("Password", type="password", key="auth_pass")
    
    if auth_mode == "Login":
        if st.sidebar.button("Login"):
            user_record = users_collection.find_one({"username": username_input.lower().strip()})
            if user_record and bcrypt.checkpw(password_input.encode('utf-8'), user_record["password"]):
                st.session_state.logged_in = True
                st.session_state.username = user_record["username"]
                st.sidebar.success(f"Welcome back, {st.session_state.username}!")
                st.rerun()
            else:
                st.sidebar.error("Invalid Username or Password.")
                
    elif auth_mode == "Register":
        if st.sidebar.button("Sign Up"):
            if len(username_input) < 3 or len(password_input) < 4:
                st.sidebar.error("Username (3+ chars) & Password (4+ chars) are too short.")
            else:
                existing_user = users_collection.find_one({"username": username_input.lower().strip()})
                if existing_user:
                    st.sidebar.error("Username already taken!")
                else:
                    # Salt and Hash the raw plaintext password safely
                    hashed_password = bcrypt.hashpw(password_input.encode('utf-8'), bcrypt.gensalt())
                    users_collection.insert_one({
                        "username": username_input.lower().strip(),
                        "password": hashed_password
                    })
                    st.sidebar.success("Registration complete! You can now log in.")
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

# --- MAIN APP NAVIGATION CONTROL ---
menu = ["🏠 Feed Home", "✍️ Create Rich Post", "🛠️ Author Dashboard"]
choice = st.sidebar.selectbox("Navigation Control", menu)

# --- PAGE: CREATE RICH POST ---
if choice == "✍️ Create Rich Post":
    if not st.session_state.logged_in:
        st.warning("🔒 Access Denied. Please log in via the sidebar to write a blog post.")
    else:
        st.header("✍️ Write a Styled Blog Post")
        st.caption(f"Drafting as author profile: **{st.session_state.username}**")

        with st.form("rich_post_form", clear_on_submit=False):
            title = st.text_input("Blog Title", placeholder="Enter a catchy title...")
            
            st.write("---")
            st.markdown("**Blog Body Editor**")
            
            content_html = st_quill(
                placeholder="Write your story here... Highlight text to format!",
                html=True,
                key="quill_editor_create"
            )
            
            st.write("---")
            uploaded_file = st.file_uploader("Upload a Cover Image (Optional)", type=["jpg", "jpeg", "png"])
            
            submit = st.form_submit_button("Publish Post")
            
            if submit:
                if not title or len(content_html.strip()) < 10:
                    st.error("Please fill out the Title and ensure your blog body has content!")
                else:
                    binary_image = None
                    if uploaded_file is not None:
                        binary_image = Binary(uploaded_file.read())
                    
                    post_payload = {
                        "title": title,
                        "author": st.session_state.username,  # Tied explicitly to the login profile
                        "content": content_html,
                        "image": binary_image,
                        "created_at": datetime.now(),
                        "comments": []
                    }
                    
                    posts_collection.insert_one(post_payload)
                    st.success(f"🎉 '{title}' has been successfully published!")
                    st.balloons()

# --- PAGE: AUTHOR DASHBOARD (EDIT & DELETE) ---
elif choice == "🛠️ Author Dashboard":
    if not st.session_state.logged_in:
        st.warning("🔒 Access Denied. Please log in via the sidebar to manage posts.")
    else:
        st.header("🛠️ Author Management Dashboard")
        st.caption("Modify or remove your own articles from the database.")
        
        # 🔒 SECURITY RULE: Authors can ONLY view and edit their OWN posts!
        my_posts = list(posts_collection.find({"author": st.session_state.username}).sort("created_at", -1))
        
        if not my_posts:
            st.info("You haven't published any articles yet under this account.")
        else:
            post_options = {f"{p['title']} ({p['created_at'].strftime('%Y-%b-%d')})": p for p in my_posts}
            selected_option = st.selectbox("Select one of your articles to manage:", list(post_options.keys()))
            
            target_post = post_options[selected_option]
            action = st.radio("Choose management action:", ["📝 Edit Content", "🗑️ Delete Article"], horizontal=True)
            st.write("---")
            
            if action == "📝 Edit Content":
                st.subheader(f"Editing: {target_post['title']}")
                updated_title = st.text_input("Edit Title", value=target_post['title'])
                
                st.markdown("**Update Body Content**")
                updated_content = st_quill(
                    value=target_post['content'],
                    html=True,
                    key="quill_editor_edit"
                )
                
                if st.button("💾 Save Document Changes"):
                    if not updated_title or len(updated_content.strip()) < 10:
                        st.error("Fields cannot be saved empty.")
                    else:
                        posts_collection.update_one(
                            {"_id": target_post["_id"]},
                            {"$set": {
                                "title": updated_title,
                                "content": updated_content
                            }}
                        )
                        st.success("Changes saved successfully!")
                        st.rerun()
                        
            elif action == "🗑️ Delete Article":
                st.subheader("⚠️ Danger Zone")
                st.error(f"Are you sure you want to delete '{target_post['title']}'?")
                confirm = st.checkbox("Confirm permanent deletion.")
                
                if st.button("❌ Permanently Delete Post", type="primary"):
                    if confirm:
                        posts_collection.delete_one({"_id": target_post["_id"]})
                        st.success("Post successfully expunged!")
                        st.rerun()
                    else:
                        st.warning("Please check the confirmation box.")

# --- PAGE: FEED HOME ---
elif choice == "🏠 Feed Home":
    st.header("🚀 Latest Stories")
    
    search_query = st.text_input("🔍 Search posts by title, author, or keyword...", value="")
    
    query_filter = {}
    if search_query:
        regex_dict = {"$regex": search_query, "$options": "i"}
        query_filter = {
            "$or": [
                {"title": regex_dict},
                {"author": regex_dict},
                {"content": regex_dict}
            ]
        }
    
    
        posts = list(posts_collection.find(query_filter).sort("created_at", -1))

if search_query:
    st.caption(f"Found {len(posts)} results matching your search.")

if not posts:
    if search_query:
        st.warning("No matches found.")
    else:
        st.info("No posts published yet.")

for index, post in enumerate(posts):
    st.markdown(f"## {post['title']}")
    st.caption(f"By **{post['author']}** on {post['created_at'].strftime('%B %d, %Y at %I:%M %p')}")

    # Render Post Image
    if post.get("image"):
        try:
            image_bytes = io.BytesIO(post["image"])
            img = Image.open(image_bytes)
            st.image(img, use_container_width=True)
        except Exception:
            st.error("⚠️ Failed to parse or render the cover image binary.")

    # Render Post Content
    st.markdown(post["content"], unsafe_allow_html=True)

    # Render Existing Comments
    with st.expander(f"💬 Comments ({len(post.get('comments', []))})"):
        for comment in post.get("comments", []):
            st.markdown(f"**{comment['user']}**: {comment['text']}")
            st.caption(f"_{comment['timestamp'].strftime('%b %d, %I:%M %p')}_")
            st.divider()
            
        # Add Comment Form (Now correctly placed inside the loop)
        with st.form(key=f"comment_block_{index}", clear_on_submit=True):
            # Automatically pre-fill commenter's name if they are logged in
            default_user = st.session_state.username if st.session_state.logged_in else ""
            c_user = st.text_input("Your Name", value=default_user, key=f"user_id_{index}")
            c_text = st.text_area("Write a response...", key=f"text_id_{index}", height=70)
            c_submit = st.form_submit_button("Post Comment")
            
            if c_submit:
                if c_user and c_text:
                    comment_payload = {
                        "user": c_user,
                        "text": c_text,
                        "timestamp": datetime.now()
                    }
                    posts_collection.update_one(
                        {"_id": post["_id"]},
                        {"$push": {"comments": comment_payload}}
                    )
                    st.success("Comment updated successfully!")
                    st.rerun()
                else:
                    st.error("Ensure both fields are filled out to share your comment.")
                    
    st.markdown("", unsafe_allow_html=True)
