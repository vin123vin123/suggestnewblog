import streamlit as st
from pymongo import MongoClient
from bson.binary import Binary
import io
from PIL import Image
from datetime import datetime
from streamlit_quill import st_quill  # Visual Rich Text Editor

# 1. Config Database Connection with Caching
@st.cache_resource
def init_connection():
    # Replace with your MongoDB Atlas string if deploying to the cloud
    return MongoClient("mongodb://localhost:27017/")

client = init_connection()
db = client["rich_blog_db"]
posts_collection = db["posts"]

# App styling and Title
st.set_page_config(page_title="DevBlog CMS", page_icon="📝", layout="centered")
st.title("📝 DevBlog: Rich Content CMS")

# Sidebar navigation interface
menu = ["🏠 Feed Home", "✍️ Create Rich Post"]
choice = st.sidebar.selectbox("Navigation Control", menu)

# --- PAGE: CREATE RICH POST ---
if choice == "✍️ Create Rich Post":
    st.header("✍️ Write a Styled Blog Post")
    st.caption("Use the toolbar below to apply headers, bold text, italics, lists, or custom formatting.")

    # Form structure for drafting contents
    with st.form("rich_post_form", clear_on_submit=False):
        title = st.text_input("Blog Title", placeholder="Enter a catchy title...")
        author = st.text_input("Author Name", placeholder="Your name or handle")
        
        st.write("---")
        st.markdown("**Blog Body Editor**")
        
        # 2. Embed the WYSIWYG Editor 
        # This outputs styled HTML markup directly
        content_html = st_quill(
            placeholder="Write your story here... Highlight text to format!",
            html=True, # Configures output format to HTML
            key="quill_editor"
        )
        
        st.write("---")
        # Cover image upload section
        uploaded_file = st.file_uploader("Upload a Cover Image (Optional)", type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button("Publish Post")
        
        if submit:
            # Minimal basic field handling validation
            if not title or not author or len(content_html.strip()) < 10:
                st.error("Please fill out the Title, Author, and ensure your blog body has content!")
            else:
                binary_image = None
                # Transform image stream to BSON Binary if uploaded
                if uploaded_file is not None:
                    binary_image = Binary(uploaded_file.read())
                
                # Build database document architecture
                post_payload = {
                    "title": title,
                    "author": author,
                    "content": content_html,  # Clean formatted HTML
                    "image": binary_image,
                    "created_at": datetime.now(),
                    "comments": []
                }
                
                posts_collection.insert_one(post_payload)
                st.success(f"🎉 '{title}' has been successfully published!")
                st.balloons()

# --- PAGE: FEED HOME ---
elif choice == "🏠 Feed Home":
    st.header("🚀 Latest Stories")
    
    # Extract records descending based on real creation time
    posts = list(posts_collection.find().sort("created_at", -1))
    
    if not posts:
        st.info("No posts published yet. Select 'Create Rich Post' from the sidebar menu to write the first story!")
        
    for index, post in enumerate(posts):
        st.markdown(f"## {post['title']}")
        st.caption(f"By **{post['author']}** on {post['created_at'].strftime('%B %d, %Y at %I:%M %p')}")
        
        # Render Cover Image if present inside the document
        if post.get("image"):
            try:
                image_bytes = io.BytesIO(post["image"])
                img = Image.open(image_bytes)
                st.image(img, use_container_width=True)
            except Exception:
                st.error("⚠️ Failed to parse or render the cover image binary.")
        
        # 3. Dynamic HTML Injection
        # We safely render the editor HTML syntax to preserve layout and typography
        st.markdown(post["content"], unsafe_allow_html=True)
        
        # --- ACTIVE COMMENTS BLOCK ---
        with st.expander(f"💬 Comments ({len(post.get('comments', []))})"):
            # Display existing user comments
            for comment in post.get("comments", []):
                st.markdown(f"**{comment['user']}**: {comment['text']}")
                st.caption(f"_{comment['timestamp'].strftime('%b %d, %I:%M %p')}_")
                st.divider()
                
            # Form block to drop down a comment pipeline
            with st.form(key=f"comment_block_{index}", clear_on_submit=True):
                c_user = st.text_input("Your Name", key=f"user_id_{index}")
                c_text = st.text_area("Write a response...", key=f"text_id_{index}", height=70)
                c_submit = st.form_submit_button("Post Comment")
                
                if c_submit:
                    if c_user and c_text:
                        comment_payload = {
                            "user": c_user,
                            "text": c_text,
                            "timestamp": datetime.now()
                        }
                        # Target document array atomic operation update push
                        posts_collection.update_one(
                            {"_id": post["_id"]},
                            {"$push": {"comments": comment_payload}}
                        )
                        st.success("Comment updated successfully!")
                        st.rerun()
                    else:
                        st.error("Ensure both fields are filled out to share your comment.")
                        
        st.markdown("<hr style='margin: 2em 0;' />", unsafe_allow_html=True)
