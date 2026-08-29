import streamlit as st
import pymongo
from datetime import datetime
from bson.objectid import ObjectId

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"])

client = init_connection()
db = client.blogdb
posts_collection = db.posts

@st.cache_data(ttl=60)
def get_all_posts():
    return list(posts_collection.find().sort("created_at", -1))

def create_post(title, author, content, image_bytes=None, image_type=None):
    posts_collection.insert_one({
        "title": title,
        "author": author,
        "content": content,
        "image": image_bytes,
        "image_type": image_type,
        "created_at": datetime.now().isoformat()
    })
    get_all_posts.clear()

st.title("📝 My Blog")

tab1, tab2 = st.tabs(["Read Posts", "Write a Post"])

with tab1:
    posts = get_all_posts()
    for post in posts:
        with st.expander(f"**{post['title']}** — by {post['author']}"):
            if post.get("image"):
                st.image(post["image"])
            st.write(post["content"])
            st.caption(f"Published: {post.get('created_at', '')}")

with tab2:
    st.header("Write a New Post")
    with st.form("new_post_form"):
        title = st.text_input("Title")
        author = st.text_input("Author")
        content = st.text_area("Content", height=200)

        # File uploader widget
        uploaded_file = st.file_uploader(
            "Upload a cover image (optional)",
            type=["jpg", "jpeg", "png"],
        )

        submitted = st.form_submit_button("Publish")
        if submitted:
            if title and author and content:
                image_bytes = uploaded_file.getvalue() if uploaded_file else None
                image_type = uploaded_file.type if uploaded_file else None
                create_post(title, author, content, image_bytes, image_type)
                st.success("Post published!")
            else:
                st.error("Please fill in all fields.")