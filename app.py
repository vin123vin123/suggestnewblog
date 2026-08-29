import streamlit as st
from pymongo import MongoClient
from bson.binary import Binary
import io
from PIL import Image
from datetime import datetime

# 1. Database Connection Configuration
@st.cache_resource
def init_connection():
    # Replace with your MongoDB Atlas connection string if needed
    return MongoClient("mongodb://localhost:27017/")

client = init_connection()
db = client["streamlit_blog_db"]
posts_collection = db["posts"]

# 2. Main Application App Structure
st.title("📝 DevBlog: Streamlit & MongoDB")

# Sidebar Navigation
menu = ["Home", "Create a Post"]
choice = st.sidebar.selectbox("Navigation", menu)

# --- PAGE: CREATE A POST ---
if choice == "Create a Post":
    st.header("✍️ Write a New Blog Post")
    
    with st.form("new_post_form", clear_on_submit=True):
        title = st.text_input("Blog Title", placeholder="Enter a catchy title...")
        author = st.text_input("Author Name", placeholder="Your name")
        content = st.text_area("Content", placeholder="Write your thoughts here...", height=200)
        
        # Image Uploading (Handled as BSON Binary under 16MB)
        uploaded_file = st.file_uploader("Upload a Cover Image (Optional)", type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button("Publish Post")
        
        if submit:
            if not title or not content or not author:
                st.error("Please fill out the Title, Author, and Content fields!")
            else:
                binary_image = None
                # Convert image file to binary format if provided
                if uploaded_file is not None:
                    binary_image = Binary(uploaded_file.read())
                
                # Document payload structure
                post_data = {
                    "title": title,
                    "author": author,
                    "content": content,
                    "image": binary_image,
                    "created_at": datetime.now(),
                    "comments": []  # Embedded array for comments
                }
                
                posts_collection.insert_one(post_data)
                st.success(f"🎉 '{title}' has been successfully published!")

# --- PAGE: HOME (FEED & VIEWING) ---
elif choice == "Home":
    st.header("🚀 Latest Stories")
    
    # Fetch posts sorted by newest arrival
    posts = list(posts_collection.find().sort("created_at", -1))
    
    if not posts:
        st.info("No posts published yet. Head over to 'Create a Post' to write the first story!")
        
    for index, post in enumerate(posts):
        st.markdown(f"## {post['title']}")
        st.caption(f"By **{post['author']}** on {post['created_at'].strftime('%B %d, %Y at %H:%M')}")
        
        # Decode and render image if it exists in the document
        if post.get("image"):
            try:
                # Wrap the raw binary in BytesIO so PIL can parse it
                image_bytes = io.BytesIO(post["image"])
                img = Image.open(image_bytes)
                st.image(img, use_container_width=True)
            except Exception as e:
                st.error("Could not load post image.")
        
        # Display blog body content
        st.write(post["content"])
        
        # --- COMMENTS SECTION ---
        with st.expander(f"💬 Comments ({len(post.get('comments', []))})"):
            # Display existing comments
            for comment in post.get("comments", []):
                st.markdown(f"**{comment['user']}**: {comment['text']}")
                st.caption(f"_{comment['timestamp'].strftime('%b %d, %I:%M %p')}_")
                st.divider()
                
            # Submit a new comment (Unique keys assigned via loop index)
            with st.form(key=f"comment_form_{index}", clear_on_submit=True):
                c_user = st.text_input("Your Name", key=f"user_{index}")
                c_text = st.text_area("Write a comment...", key=f"text_{index}", height=70)
                c_submit = st.form_submit_button("Post Comment")
                
                if c_submit:
                    if c_user and c_text:
                        comment_payload = {
                            "user": c_user,
                            "text": c_text,
                            "timestamp": datetime.now()
                        }
                        # Push the comment payload into the specific post's comment array
                        posts_collection.update_one(
                            {"_id": post["_id"]},
                            {"$push": {"comments": comment_payload}}
                        )
                        st.success("Comment posted!")
                        st.rerun()  # Refresh the page to show the new comment instantly
                    else:
                        st.error("Both fields are required to comment.")
                        
        st.markdown("---")
