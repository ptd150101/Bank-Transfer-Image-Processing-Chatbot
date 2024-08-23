import os
import numpy as np
import pandas as pd
import json
import time
import streamlit as st
from PIL import Image
from tensorflow.keras.applications.efficientnet import EfficientNetB7, preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from sklearn.metrics.pairwise import cosine_similarity

# Tạo thư mục uploads nếu chưa tồn tại
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Tạo mô hình EfficientNetB7 với các trọng số đã được huấn luyện trước
base_model = EfficientNetB7(weights='imagenet', include_top=False, pooling='avg', input_shape=(600, 600, 3))

# Tạo một mô hình mới chỉ bao gồm phần cơ sở và các lớp pooling
model = Model(inputs=base_model.input, outputs=base_model.output)

# Hàm để lấy embedding của ảnh
def get_image_embedding(img_path):
    img = image.load_img(img_path, target_size=(600, 600))  # Resize ảnh cho phù hợp với đầu vào của EfficientNetB7
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)  # Thay đổi hình dạng của ảnh
    x = preprocess_input(x)  # Tiền xử lý ảnh
    
    embedding = model.predict(x)  # Dự đoán embedding của ảnh
    return embedding.flatten()

# Đọc file JSON chứa embedding đã lưu trữ
with open('image_embeddings.json', 'r') as file:
    data = json.load(file)

# Tạo DataFrame từ dữ liệu JSON
df = pd.DataFrame(data)

# Chuyển đổi cột embedding từ danh sách thành mảng numpy
df['Embedding'] = df['Embedding'].apply(lambda x: np.array(x))

# Hàm để so sánh embedding input với các embedding trong file JSON
def find_similar_images(input_image_path, df, top_n=10):
    input_embedding = get_image_embedding(input_image_path)
    
    # Tính khoảng cách cosine
    similarities = cosine_similarity([input_embedding], list(df['Embedding'].values))
    
    # Lấy top N hình liên quan nhất
    df['Similarity'] = similarities[0]
    top_images = df.sort_values(by='Similarity', ascending=False).head(top_n)
    
    return top_images

# Giao diện Streamlit
st.title('Image Similarity Finder')
st.write('Upload an image and find the top 10 similar images.')

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    # Lưu ảnh tải lên
    img = Image.open(uploaded_file)
    img_path = os.path.join('uploads', uploaded_file.name)
    img.save(img_path)
    
    st.image(img, caption='Uploaded Image.', use_column_width=True)
    st.write("")
    st.write("Finding similar images...")

    # Tìm top 10 hình liên quan nhất
    start_time = time.time()
    top_images = find_similar_images(img_path, df)
    end_time = time.time()

    # Hiển thị kết quả
    st.write(f'Thời gian chạy: {end_time - start_time:.2f} giây')
    st.write('Top 10 hình liên quan nhất:')
    
    # In tên ngân hàng của top 10 hình liên quan nhất
    for index, row in top_images.iterrows():
        st.write(f"{index + 1}. {row['Tên ngân hàng']}")
