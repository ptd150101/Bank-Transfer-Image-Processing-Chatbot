import json
import os
import re
import google.generativeai as genai
import requests
import streamlit as st
from unidecode import unidecode
from PIL import Image

# API Configuration
AI_CHATBOT_URL = os.getenv("AI_CHATBOT_URL", "http://127.0.0.1:6379")
api_key = "AIzaSyDdWMQNVqB9bmrN2SHqTzOKBeHaatDK7bM"
genai.configure(api_key=api_key)
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(model_name="gemini-1.5-pro")
top_k = 11

# App Config
st.set_page_config(page_title="Transfer Chat Bot", page_icon="🦜")

if "chat_history" not in st.session_state:
    st.session_state.full_chat_history = [
        {"role": "assistant", "content": "Hello! May I help you?"}
    ]
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hello! May I help you?"}
    ]
    st.session_state.summary_history = ""
previous_summary_history = st.session_state.summary_history


# Chat Conversation Display
for message in st.session_state.full_chat_history:
    MESSAGE_TYPE = "AI" if message["role"] == "assistant" else "Human"
    with st.chat_message(MESSAGE_TYPE):
        st.write(message["content"])

# User Input
user_query = st.chat_input("Type your message ✍")
if user_query is not None and user_query != "":
    with st.chat_message("Human"):
        st.write(user_query)
    response = requests.post(
        url=AI_CHATBOT_URL + "/aichatbot5/v1/chat",
        json={
            "content": user_query,
            "histories": st.session_state.chat_history,
            "summary": previous_summary_history,
        },
        headers={"Content-Type": "application/json"},
        verify=False,
    )
    print(response.json())
    content = response.json()["data"]["content"]
    with st.chat_message("AI"):
        st.write(content)
    st.session_state.full_chat_history.append({"role": "user", "content": user_query})
    st.session_state.full_chat_history.append({"role": "assistant", "content": content})
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    st.session_state.chat_history.append({"role": "assistant", "content": content})
    if (
        len(st.session_state.chat_history) == top_k
        and len(st.session_state.chat_history) != 0
    ):
        previous_chat_history = st.session_state.chat_history[: top_k // 2]
        previous_chat_history.append(
            {"role": "previous_summary_history", "content": previous_summary_history}
        )
        st.session_state.summary_history = requests.post(
            url=AI_CHATBOT_URL + "/aichatbot5/v1/summary",
            data=json.dumps({"histories": previous_chat_history}),
        ).text
        print(previous_chat_history)
        del st.session_state.chat_history[: top_k // 2]


# File Uploader at the Bottom Left
# st.markdown('<div class="upload-box">', unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Upload an image", type=["jpg", "jpeg", "png", "webp"], key="uploader"
)
# st.markdown("</div>", unsafe_allow_html=True)

# Process the uploaded image
if uploaded_file is not None and uploaded_file != "":
    st.image(uploaded_file)
    with st.chat_message("Human"):
        st.write("Uploaded an image.")
    img = Image.open(uploaded_file)
    
    
    def process_image(image):
        input_text = """
        - You are an expert in extracting data from bank transfer images in accented Vietnamese.
        - Your task is to convert the successful transfer image to JSON format
        - Data Consistency: Information like "Nội dung" will always represent the transaction description, and "Mã giao dịch" the transaction ID.
        - Error Handling:
            1. Essential information is missing from the image? (e.g., amount, date, etc.) ----> return null.
            2. The image is of poor quality and the text is not clear? ----> state that "The image is invalid, please resend a clear image".
            3. There are multiple transactions displayed in a single image? ----> state that "The image is invalid, please resend each transaction in separate images".
            4. The image is not a successful transfer? ----> state that "The image is invalid, please resend the image of successful transfer".
        
        - Please use the example below to fulfill the above requirements:
        {
            "transaction_status": "Giao dịch thành công",
            
            "amount": "2500000",   (THE TRANSFER AMOUNT MUST BE WRITTEN AS A NUMBER, WITHOUT ANY PERIODS OR COMMAS)
            
            "transaction_date": "16/07/2024",   (DD/MM/YYYY)
            
            "transaction_time": "20:11:56",    (HH/MM/SS)
            
            "sender": {
                "bank": "BBank",
                REMEMBER:
                1. The name of the sender's bank is usually written prominently at the top of the photo
                
                "name": null,
                REMEMBER:
                1. The sender's name does not have to be an individual's name but can be the name of a company, organization, school, university,...
                
                2. If there are 2 names and 2 account numbers (not included in the description), the sender's name is the first name, the receiver's name is the second name, the sender's account number is the first account number, the receiver's account number is the second account number.
                Example:
                NGUYEN TAT THANH CONG
                0000 1111 2222 3333
                HUAN HOA HONG
                1111 2222 3333 4444
                ----> the sender's name is "NGUYEN TAT THANH CONG", the receiver's name is "HUAN HOA HONG"
                
                3. If there is only one name and one account number (not included in the description), the sender's name is null, the receiver's name is the first name, the sender's account number is null, the receiver's account number is the first account number.
                Example:
                **** **** ****
                **** **** ****
                HUAN HOA HONG
                1111 2222 3333 4444
                ----> the receiver's name is "HUAN HOA HONG"
                
                4. DO NOT USE THE NAME IN THE CONTENT OF THE TRANSFER TO PUT IN THE SENDER'S NAME.
                
                "account_number": nulL
                REMEMBER:
                1. The sender's account number is the first account number.
            },   
            
            "receiver": {
                "bank": "ABank",
                
                "name": "NGUYEN DANG TOAN NANG",    (The receiver's name is the second name)
                REMEMBER:
                1. The receiver's name does not have to be an individual's name but can be the name of a company, organization, school, university,...
                2. The receiver's name is the second name.
                
                "account_number": "1234567890"
                REMEMBER:
                1. The receiver's account number is the second account number.
            },
            
            "description": "NGUYEN DANG TOAN NANG/n0982408916 dang ki/nnhan hoc bong/n toan phan",
            REMEMBER:
            1. DON'T DROP ANY INFORMATION FROM THE DESCRIPTION.
            
            "transaction_id": "AB1234567890"  
        }
        
        
        - If there is no bank logo, the sender bank will be null.
        """
        response = model.generate_content(
            [input_text, image], stream=True, generation_config=generation_config
        )
        response.resolve()
        return response.text

    def process_bank_response(prompt_system, response_text, image, generation_config):
        input_text = prompt_system.format(response_text=response_text)
        response = model.generate_content([input_text, image], stream=True, generation_config=generation_config)
        response.resolve()
        return response.text


    def TPBANK(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
            1. If there is only 1 name and 1 account number, that is the receiver's information.
            2. If there are 2 names and 2 account numbers, the sender's information is written before the receiver's information.   
            3. Fill in the description of the json file from "Nội dung"
            
        REMEMBER:
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)
        

    
    def Vietinbank(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
                    
        REMEMBER:
        - Get information from "Từ tài khoản" to fill in the sender's name and the sender's account_number.
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.
        - Transaction ID: it is presented on the image. It is the text under the line representing the date and time. If there is no line representing the date and time, the transaction_id will be null.
        
        STRUCTURE:    
        Từ tài khoản        [sender's account_number]
                            [sender's name]
        Đến tài khoản       [receiver's account_number]
                            [receiver's name]
        Ngân hàng           [receiver's bank]
        Số tiền             [amount]
        Phí
        Nội dung            [description]


        Example 1:
        Từ tài khoản        ******1234
                            HUAN RAU SY/nHUAN HOA HONG
        Đến tài khoản       1234569876
                            CO LAM THI/nMOI CO AN
        Ngân hàng           WTFBANK_Ngân hàng WTF Việt Nam (WTF)
        Số tiền             5,000,000 VND
        Phí                 Miễn phí
        Nội dung            HUAN RAU SY/nHUAN HOA HONG chuyen tien/nthi vstep bach khoa
        ----> the sender's name is "HUAN RAU SY/nHUAN HOA HONG", the sender's account_number is "******1234", the receiver's name is "CO LAM THI/nMOI CO AN", the receiver's account_number is "1234569876", the receiver's bank is "WTFBANK_Ngân hàng WTF Việt Nam (WTF)", the description is "HUAN RAU SY/nHUAN HOA HONG chuyen tien/nthi vstep bach khoa"
        
        
        Example 2:
        Từ tài khoản        ******1234
                            XIAOCHAOMENG VIET/nNAM
        Đến tài khoản       1234569876
                            CO LAM THI/nMOI CO AN
        Ngân hàng           WTFBANK_Ngân hàng WTF Việt Nam (WTF)
        Số tiền             5,000,000 VND
        Phí                 Miễn phí
        Nội dung            MCK VIET NAM/nchuyen tien/nthi vstep bach khoa
        ----> the sender's name is "XIAOCHAOMENG VIET/nNAM", the sender's account_number is "******1234", the receiver's name is "CO LAM THI/nMOI CO AN", the receiver's account_number is "1234569876", the receiver's bank is "WTFBANK_Ngân hàng WTF Việt Nam (WTF)", the description is "MCK VIET NAM/nchuyen tien/nthi vstep bach khoa"


        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)

    
    def Techcombank(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
            1. Take the infomation of the receiver's bank, the receiver's account number in "Thông tin chi tiết".
            2. Take the infomation of the receiver's name in "Chuyển thành công tới".
            3. The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
            4. The sender's name is null. 
            5. The sender's account_number is null.
            6. Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
            7. Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.
            
        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)
        

    def MB(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
        
        REMEMBER:
        - Get information from "Chuyển từ tài khoản" to fill in the sender's name. Without "Chuyển từ tài khoản", the sender name will be null.
        - If the description only contains the name, it is neither the sender's name nor the recipient's name
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        STRUCTURE:
        Chuyển tiền thành công
        [amount]
        [transaction_time] - [transaction_date]
        [receiver's name]
        [receiver's bank] - [receiver's account_number]
        [description]
        Chuyển từ tài khoản     [sender's name]
        Mã giao dịch            [transaction_id]
        
        Example 1:
        Chuyển tiền thành công
        30,500,000 VND
        20:45 - 1/1/2001
        DAI HOC KINH TE/nQUOC DAN
        WTFBank (WTF) - 02468976211
        HUAN HOA HONG 0123987654 chuyen tien/nan hang thang
        Chuyển từ tài khoản     HUAN HOA HONG
        Mã giao dịch            0357912345644
        ----> the sender's name is "HUAN HOA HONG", the receiver's name is "DAI HOC KINH TE/nQUOC DAN"
        
        Example 2:
        Chuyển tiền thành công
        30,500,000 VND
        20:45 - 1/1/2001
        DAI HOC KINH TE/nQUOC DAN
        WTFBank (WTF) - 02468976211
        NGUYEN CHIEN THANG 0123987654 chuyen tien/nan hang thang
        Chuyển từ tài khoản     PHAN TIEN DAT
        Mã giao dịch            0357912345644
        ----> the sender's name is "PHAN TIEN DAT", the receiver's name is "DAI HOC KINH TE/nQUOC DAN"
        
        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)


    def BIDV(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
            1. The receiver's account_number is the first account number shown in the image.
            2. The receiver's name is the first name shown in the image.
            3. The sender's account_number and the sender's name is null.
            4. Fill in the description of the json file from "Nội dung"
            5. The receiver's bank can't just be "NHTMCP" (must include the line break after the /n mark).
            
        STRUCTURE:
        Quý khách đã chuyển thành công số tiền [amount] đến số tài khoản [receiver's account_number]/ [receiver's name]/ [receiver's bank] vào lúc [transaction_date] [transaction_time]. Nội dung: [description]
        Số tham chiếu: [transaction_id]
        
        Example:
        Quý khách đã chuyển thành công số tiền 500,000 VND đến số tài khoản "123456789"/ "CO LAM THI/nMOI CO AN"/ "NHTMCP/nKinh Tế" vào lúc 6/9/1969 6:9:69. Nội dung: "CHUYEN TIEN/nCHO HUAN HOA HONG"
        Số tham chiếu: 02468936
        ----> the receiver's bank is "NHTMCP/nKinh Tế", the receiver's name is "CO LAM THI/nMOI CO AN", the description is "CHUYEN TIEN/nCHO HUAN HOA HONG", the receiver's account_number is "123456789",
        
        REMEMBER:
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)

    
    def ViettelMoney(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank in the json file as described below:
            1. The receiver's name is the first name in the image (Maximum 1 "\n" allowed).
            2. GET ALL THE INFORMATION FROM "Nội dung" TO FILL IN THE DESCRIPTION OF THE JSON FILE (YOU SHOULD DO THIS AT LEAST TWICE). YOU MUST KEEP IT AS ORIGINAL, DON'T DROP ANY INFORMATION.
            3. DON'T DROP PHONE NUMBER FROM DESCRIPTION.
            
        STRUCTURE
        Số tiền chuyển                                                                 ['amount']
        Chủ tài khoản nhận                                                   ['receiver']['name']
        Nội dung                                                                  ['description']
        ---------------------------------------------------------------------------------------------
        Số tài khoản (This part may or may not be included)        ['receiver']['account_number']
        Ngân hàng nhận (This part may or may not be included)                ['receiver']['bank']
        Tài khoản chuyển (This part may or may not be included)                ['sender']['bank']
        
        
        EXAMPLE 1:
        Số tiền chuyển                         15.000.000đ
        Chủ tài khoản nhận                 Dai Hoc Kinh Te
                                                  Quoc Dan
        Nội dung                             Phan Tien Dat
                                        20195854 dong tien
                                                 thi toeic
        ----> ['receiver']['account_number'] of the json file is null, ['receiver']['bank'] of the json file is null, ['receiver']['name'] of the json file is "Dai Hoc Kinh Te/nQuoc Dan", ['description'] of the json file is "Phan Tien Dat/n20195854 dong tien/nthi toeic".


        EXAMPLE 2:
        Số tiền chuyển                         20.000.000đ
        Chủ tài khoản nhận                Dai Hoc Xay Dung
                                                    Ha Noi
        Nội dung              Con Cho Nao Lam ViettelMoney   
                                       123456789 dong tien
                                     lam lai giao dien app
        --------------------------------------------------
        Số tài khoản                          196656982236
        Ngân hàng nhận                              Bank 1
        Tài khoản chuyển                            Bank 2
        ----> ['receiver']['account_number'] of the json file is "196656982236", ['receiver']['bank'] of the json file is "Bank 1", ['receiver']['name'] of the json file is "Dai Hoc Xay Dung/nHa Noi", ['description'] of the json file is "Con Cho Nao Lam ViettelMoney/n123456789 dong tien/nlam lai giao dien app", ['sender']['bank'] of the json file is "Bank 2".

    
        REMEMBER:
        - The sender's name and the receiver's name don't have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)
        
    def VNPay(response_text, image):
        prompt_system = """
        - Your task is to change the information except the sender's bank, the transaction_date, transaction_time, amount and transaction_id in the json file as described below:
            1. MUST return "description" be Null
        - Before you start, please ask me any questions you have about this so I can give you more context. Be extremely comprehensive
        STRUCTURE:
        Số tiền (VND)
        Khuyến mại (VND)
        Phí giao dịch (VND)
        Ví của tôi              ["sender's account_number"]
        Dịch vụ
        Mã thanh toán
        Thời gian giao dịch     ["transaction_date", "transaction_time"]
        
        
        REMEMBER:
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)    

    def MoMo(response_text, image):
        prompt_system = """
        - Your task is to change the information except the "sender"'s "bank", "transaction_date", "transaction_time", "amount" and "transaction_id" in the json file as described below:
            1. THE TRANSFER AMOUNT MUST BE WRITTEN AS A NUMBER, WITHOUT ANY PERIODS OR COMMAS
            2. ONLY take "Tin nhắn" field, "Mô tả" field to fill "description". If "Tin nhắn", "Mô tả" are not presented on the image, "description" MUST be null
        STRUCTURE 1 (Some labels may or may not appear):
    
        Thời gian thanh toán        ["the transaction_date", "transaction_time"]
        Nguồn tiền                  
        Tổng phí

        Số dư ví
        Loại chỉ tiêu

        Tên Ví MoMo                 [receiver's name]
        Số điện thoại               [receiver's account_number]
        
        EXAMPLE 1:
        Thời gian thanh toán        HH:MM - DD/MM/YYYY
        Nguồn tiền                  Ví MoMo
        Tổng phí

        Số dư ví
        Loại chỉ tiêu

        Tên Ví MoMo                 Hà Tuấn Phong
        Số điện thoại               0987654321

        ---> receiver's name MUST be "Hà Tuấn Phong", receiver's account_number MUST be "0987654321"

        STRUCTURE 2 (Some labels may or may not appear):
        Trạng thái
        Thời gian                   ["transaction_time", "the transaction_date"]

        Mã giao dịch                ["transaction_id"]
        Tài khoản thẻ               [sender's bank]
        Tổng phí

        Dịch vụ

        Cửa hàng                    [receiver's name]

        Mã đơn hàng

        Mô tả                       ["description"]
        
        EXAMPLE 2:
        
        Trạng thái

        Thời gian                   HH:MM - DD/MM/YYYY

        Mã giao dịch   

        Tài khoản thẻ      

        Tổng phí

        Dịch vụ                     MIXI FOOD

        Cửa hàng                    MiXi Food Tuan Phong

        Mã đơn hàng                 XXX

        Mô tả                       Thanh toán MoMo

        ----> receiver's name is "MiXi Food Tuan Phong" (ONLY GET receiver's name from "Cửa hàng", IGNORE content from "Dịch vụ"), "description" is "Thanh toán MoMo". DO NOT get "account_number" from "Mã đơn hàng"
        REMEMBER:
        - The name does not have to be an individual's name but can be the name of a company, organization, school, university,...
        - Character encoding: You must not anticipate any character encoding issues with Vietnamese text but must preserve the Vietnamese characters. You must copy the content directly and keep it as original.
        - Error Handling: If you cannot extract some information from the image (e.g., due to poor image quality or unexpected format), you should leave the corresponding fields blank in the JSON.

        Json format: {response_text}
        Result json format: 
        """
        return process_bank_response(prompt_system, response_text, image, generation_config)    


    
    def enrichment_json(image):
        prompt_system = """
        - Based on the json format and banking interface description below, i want you to fill the sender bank by bank name. And if you still not sure, return the sender bank is null.
        REMEMBER: JUST FILL THE SENDER BANK, DO NOT CHANGE ANYTHING.
        Banking interface description:
        1. OLD MB banking interface:
        - There are 4 buttons at the bottom include "Lưu người thụ hưởng", "Lưu mẫu giao dịch", "Về trang chủ" and "Tạo giao dịch khác".

        2. MOMO banking interface:
        - Main color: White and pink
        - Pattern: Light patterns, geometric shapes
        - Above: Dark to light pink gradient
        - Below: Light blue for support information
        - The function buttons at the bottom include "Chuyển thêm", "Chia tiền" or "Bấm để nhận email", "Tạo giao dịch mới", "Màn hình chính"

        3. Agribank banking interface:
        - Information labels in order from top to bottom such as: "Tài khoản thụ hưởng", "Tên người thụ hưởng", "Thời gian giao dịch", "Phí giao dịch, ""Nội dung CK"
        - On the top, the interface color is orange and having the text "KẾT QUẢ GIAO DỊCH".
        
        4. OLD Vietcombank banking interface:
        Fixed Elements
        - Information labels in order from top to bottom such as: "Tên người thụ hưởng", "Tài khoản thụ hưởng", "Ngân hàng thụ hưởng", "Mã giao dịch", "Nội dung"
        - Background image of a road with car lights at night
        - Buttons at the bottom such as: "Chia sẻ", "Lưu ảnh", "Lưu thụ hưởng"
        - The interface is designed with green as the primary color.

        5. Viettel Money banking interface:
        - Information labels in order from top to bottom such as: "Số tiền chuyển", "Chủ tài khoản nhận", "Nội dung", "Số tài khoản", "Ngân hàng nhận", "Tài khoản chuyển", "Phí giao dịch"
        - Buttons at the bottom such as: "Về trang chủ", "Tiếp tục chuyển tiền"
        
        6. ACB banking interface:
        - Information labels in order from top to bottom such as: "Ngày lập lệnh", "Ngày hiệu lực", "Bên chuyển", "Bên nhận", "Thông tin giao dịch"
        - The interface structure of the ABC bank transfer app will be similar to the structure of the following HTML file:
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <title>Transaction Receipt</title>
        </head>
        <body>
            <div class="receipt">
                <div class="header">
                    <h2>1.960.000 VND</h2>
                    <p>Một triệu chín trăm sáu mươi nghìn đồng</p>
                    <p>Giao dịch thành công</p>
                </div>
                <div class="content">
                    <div class="section">
                        <p>Ngày lập lệnh: <span class="highlight">24/12/2021 - 21:33:48</span></p>
                        <p>Ngày hiệu lực: <span class="highlight">24/12/2021</span></p>
                    </div>
                    <div class="section">
                        <p class="section-title">Bên chuyển</p>
                        <p>TRẦN HOÀNG YẾN</p>
                        <p>TGTT KHTN (CÁ NHÂN) VND</p>
                        <p class="highlight">6584267</p>
                    </div>
                    <div class="section">
                        <p class="section-title">Bên nhận</p>
                        <p>Tên người nhận: <span class="highlight">LÊ THỊ HIỀN</span></p>
                        <p>Ngân hàng nhận: <span class="highlight">VIETCOMBANK - NH TMCP NGOẠI THƯƠNG</span></p>
                        <p>Tài khoản nhận: <span class="highlight">0781000401997</span></p>
                    </div>
                    <div class="section info">
                        <div>
                            <p>Thời gian</p>
                            <p>Phí</p>
                            <p>Người chịu phí</p>
                            <p>Nội dung</p>
                        </div>
                        <div>
                            <p class="highlight">Chuyển ngay</p>
                            <p class="highlight">5.000 VND</p>
                            <p class="highlight">Bên chuyển</p>
                            <p class="highlight">VAN NAM CK-241221-21:33:44</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>

        -The content of the information such as the recipient, sender, and transaction details may differ from the HTML file, but as long as the structure is similar, it indicates the ACB app.
        
        7. OLD Techcombank banking interface:
        - There is a red "Giao dịch khác" button at the bottom of the screen to continue making other transactions.
        - Title: "Giao Dịch Thành Công" is displayed in the center, in black
        - "Số tiền chuyển khoản" is printed boldly and large, with a deep red background and geometric patterns on the back.
        - Red "X" icon in the upper right corner.

        Json format: {response_text}
        Enrichment text: 

        """
        return process_bank_response(prompt_system, response_text, image, generation_config)



    def clean_json(output):
        # Remove triple backticks and the 'sql' tag
        cleaned_json = output.replace("```json", "").replace("```", "").strip()
        # Remove the semicolon at the end if present
        if cleaned_json.endswith(";"):
            cleaned_json = cleaned_json[:-1].strip()
        return cleaned_json



    def convert_bank_name(json_text):
        # Tạo danh sách các từ khóa và viết tắt cho mỗi ngân hàng
        banks = {
            "MB": ["MB", "MBBANK", "MB BANK", "Quân đội", "Ngân hàng Quân đội", "QĐ", "NHQĐ"],
            "Vietinbank": ["CTG", "Vietinbank", "Vietin bank", "Vietin", "VTBank", "VT Bank", "Công thương Việt Nam", "Công thương", "NHTMCPCTVN", "NHTMCPCT", "TMCPCTVN", "TMCPCT"],
            "Vietcombank": ["Vietcombank", "Vietcom bank", "VCB", "VCBank", "VC Bank", "Ngoại thương Việt Nam", "Ngoại thương", "NHTMCPNTVN", "NHTMCPNT", "TMCPNTVN", "TMCPNT"],
            "Agribank": ["Agribank", "Nông nghiệp", "Nông nghiệp và Phát triển Nông thôn Việt Nam"],
            "Techcombank": ["Techcombank", "TCB", "Techcom bank", "Kỹ Thương Việt Nam", "Kỹ Thương", "NHTMCPKTVN", "NHTMCPKT", "TMCPKTVN", "TMCPKT"],
            "BIDV": ["BIDV", "Đầu tư và Phát triển Việt Nam", "Đầu tư", "Đầu tư và Phát triển"],
            "Eximbank": ["Eximbank", "Xuất Nhập Khẩu", "EIB", "XNK", "Exim bank"],
            "CB": ["CB Bank", "CBBank", "Xây dựng"],
            "Oceanbank": ["Đại dương", "Ocean", "Ocean bank"],
            "GPBank": ["Dầu khí", "Dầu Khí Toàn Cầu", "GPBank", "GP Bank"],
            "VPBank": ["VPB", "Việt Nam Thịnh Vượng", "VPBank", "VP Bank", "VNTV"],
            "PG Bank": ["PG", "PGBank", "PG Bank", "Thịnh vượng và Phát triển"],
            "ACB": ["ACBBank", "ACB Bank", "Á Châu"],
            "SHB": ["SHBBank", "SHB Bank"],
            "SCB": ["SCBBank", "SCB Bank", "TMCP Sài Gòn", "TMCPSG"],
            "Sacombank": ["Sacom bank", "Sacombank", "Sài gòn thương tín", "SGTT", "STB"],
            "TPBank": ["TP", "TPBank", "TP Bank", "Tiên phong", "TPB"],
            "VIB": ["VIBBank", "VIB bank", "VIB", "Quốc tế"],
            "MSB": ["MSB", "MSBBank", "MSB Bank", "Hàng hải"],
            "PVcombank": ["PVcombank", "PVcom bank", "Đại chúng"],
            "VietBank": ["VietBank", "Viet Bank", "Việt Nam Thương Tín", "VNTT", "VBB"],
            "Viettel Money": ["ViettelMoney", "Viettel Money", "Money", "ViettelPay", "Viettel Pay"],
            "Momo": ["Momo"]
        }
        
        # Hàm loại bỏ dấu và chuyển thành chữ thường
        def normalize_text(text):
            if text is None:
                return None
            # Chuyển các ký tự Unicode thành dạng ASCII
            ascii_text = unidecode(text)
            # Chuyển thành chữ thường
            lower_text = ascii_text.lower()
            # Thay thế ký tự '/n' và dấu xuống dòng '\n' bằng dấu cách
            cleaned_text = re.sub(r'/n|\n', ' ', lower_text)
            return cleaned_text

        # Ghép các từ khóa thành một regex pattern
        patterns = {bank: re.compile(r'\b' + r'\b|\b'.join(re.escape(normalize_text(keyword)) for keyword in keywords) + r'\b', re.IGNORECASE) for bank, keywords in banks.items()}
        
        def find_bank_name(text):
            # Kiểm tra và trả về tên ngân hàng tương ứng
            for bank, pattern in patterns.items():
                if pattern.search(text):
                    return bank
            # Nếu không tìm thấy từ khóa nào phù hợp
            return text

        # Chuyển đổi amount thành số
        def convert_amount(amount):
            amount_str = str(amount)  # Chuyển đổi thành string
            amount_cleaned = re.sub(r'[^\d]', '', amount_str)
            return amount_cleaned
        
        # Lấy thông tin ngân hàng từ json_text và chuẩn hóa nếu không phải là None
        sender_bank = json_text['sender']['bank']
        receiver_bank = json_text['receiver']['bank']

        if sender_bank is not None:
            normalized_sender_bank = normalize_text(sender_bank)
            json_text['sender']['bank'] = find_bank_name(normalized_sender_bank)
        
        if receiver_bank is not None:
            normalized_receiver_bank = normalize_text(receiver_bank)
            json_text['receiver']['bank'] = find_bank_name(normalized_receiver_bank)
        
        # Chuyển đổi amount thành số nguyên
        if json_text.get('amount'):
            json_text['amount'] = convert_amount(json_text['amount'])
        
        return json_text
    
    
    
    
    
    response_text = process_image(img)
    print("----------------------------------------------------------------")
    print("1. Response_text: ", response_text)
    print("----------------------------------------------------------------")
    
    
    json_text = json.loads(clean_json(response_text))
    print("2. Json_text: ", json_text)
    print("----------------------------------------------------------------")
    print("Sender's bank: ", json_text["sender"]["bank"])
    print("----------------------------------------------------------------")
    json_text_convert_bank = convert_bank_name(json_text)
    
    if json_text_convert_bank['sender']['bank'] == "TPBank":
        response_text_TP = TPBANK(response_text=response_text, image=img)
        json_text_TP = json.loads(clean_json(response_text_TP))
        if json_text_TP['description'] is not None:
            json_text_TP['description'] = unidecode(json_text_TP['description'])
        print("3. Response_text_TP: ", json_text_TP)
        print("----------------------------------------------------------------")

        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_TP))

    elif json_text_convert_bank['sender']['bank'] == "Techcombank":
        response_text_Techcombank = Techcombank(response_text=response_text, image=img)
        json_text_Techcombank = json.loads(clean_json(response_text_Techcombank))
        if json_text_Techcombank['description'] is not None:
            json_text_Techcombank['description'] = unidecode(json_text_Techcombank['description'])
        print("3. Response_text_Techcombannk: ", json_text_Techcombank)
        print("----------------------------------------------------------------")

        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_Techcombank))
            
    elif json_text_convert_bank['sender']['bank'] == "MB":
        response_text_MB = MB(response_text=response_text, image=img)
        json_text_MB = json.loads(clean_json(response_text_MB))
        if json_text_MB['description'] is not None:
            json_text_MB['description'] = unidecode(json_text_MB['description'])
        print("3. Response_text_MB: ", json_text_MB)
        print("----------------------------------------------------------------")
        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_MB))
            
    elif json_text_convert_bank['sender']['bank'] == "BIDV":
        response_text_BIDV = BIDV(response_text=response_text, image=img)
        json_text_BIDV = json.loads(clean_json(response_text_BIDV))
        account_number = json_text_BIDV["receiver"]["account_number"]
        print("json_text_BIDV", json_text_BIDV)
        print("----------------------------------------------------------------")
        
        
        if json_text_BIDV['receiver']['bank'] is None:
            if json_text_BIDV['description'] is not None:
                    json_text_BIDV['description'] = unidecode(json_text_BIDV['description'])
            print("3. Response_text_BIDV(receiver's bank is null): ", json_text_BIDV)
            print("----------------------------------------------------------------")
            with st.chat_message("AI"):
                st.write(convert_bank_name(json_text_BIDV))
        
        elif json_text_BIDV['receiver']['bank'].lower() in ["bidv"]:
            if len(account_number) > 10:
                # Giữ lại 3 số đầu và 7 số cuối
                modified_account_number = account_number[:3] + account_number[-7:]
                print("STK cũ: ", account_number)
                print("STK mới: ", modified_account_number)
                # Cập nhật lại số tài khoản trong json_text
                json_text_BIDV["receiver"]["account_number"] = modified_account_number
                json_text_BIDV["sender"]["account_number"] = None
                if json_text_BIDV['description'] is not None:
                    json_text_BIDV['description'] = unidecode(json_text_BIDV['description'])
                print("3. Response_text_BIDV(STK cũ ---> STK mới): ", json_text_BIDV)
                print("----------------------------------------------------------------")
                with st.chat_message("AI"):
                    st.write(convert_bank_name(json_text_BIDV))
            else:
                if json_text_BIDV['description'] is not None:
                    json_text_BIDV['description'] = unidecode(json_text_BIDV['description'])
                print("3. Response_text_BIDV(STK không đổi): ", json_text_BIDV)
                print("----------------------------------------------------------------")
                with st.chat_message("AI"):
                    st.write(convert_bank_name(json_text_BIDV))
        
        else:
            if json_text_BIDV['description'] is not None:
                json_text_BIDV['description'] = unidecode(json_text_BIDV['description'])
            print("3. Response_text_BIDV(receiver's bank không phải bidv): ", json_text_BIDV)
            print("----------------------------------------------------------------")
            with st.chat_message("AI"):
                st.write(convert_bank_name(json_text_BIDV))
    
    
    elif json_text_convert_bank['sender']['bank'] == "Vietinbank":
        response_text_Vietinbank = Vietinbank(response_text=response_text, image=img)
        json_text_Vietinbank = json.loads(clean_json(response_text_Vietinbank))
        print(json_text_Vietinbank)
        if json_text_Vietinbank['sender']['account_number'][-4:] == json_text_Vietinbank['transaction_id'][-4:]:
            json_text_Vietinbank['sender']['account_number'] = json_text_Vietinbank['transaction_id']
            json_text_Vietinbank['transaction_id'] = None
        if json_text_Vietinbank['description'] is not None:
            json_text_Vietinbank['description'] = unidecode(json_text_Vietinbank['description'])
        print("3. Response_text_Vietinbank: ", json_text_Vietinbank)
        print("----------------------------------------------------------------")
        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_Vietinbank))
    
    elif json_text_convert_bank['sender']['bank'] == "Viettel Money":
        response_text_ViettelMoney = ViettelMoney(response_text=response_text, image=img)
        json_text_ViettelMoney = json.loads(clean_json(response_text_ViettelMoney))
        print(json_text_ViettelMoney)
        json_text_ViettelMoney['transaction_date'] = json_text_convert_bank['transaction_date']
        json_text_ViettelMoney['transaction_time'] = json_text_convert_bank['transaction_time']
        json_text_ViettelMoney['receiver']['name'] = unidecode(json_text_ViettelMoney['receiver']['name'])
        
        if json_text_ViettelMoney['receiver']['bank'] is None:
            json_text_ViettelMoney['receiver']['account_number'] = None
            
        if json_text_ViettelMoney['description'] is not None:
            json_text_ViettelMoney['description'] = unidecode(json_text_ViettelMoney['description'])
        
        print("3. Response_text_ViettelMoney: ", json_text_ViettelMoney)
        print("----------------------------------------------------------------")
        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_ViettelMoney))
            
    elif json_text_convert_bank['sender']['bank'] == "MoMo":
        def contains_vietnamese_characters(text):
            # Biểu thức chính quy để kiểm tra các ký tự có dấu tiếng Việt
            vietnamese_pattern = re.compile(
                r'[ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơ'
                r'ĂắằẳẵặẤầẩẫậẮẰẲẴẶÉÈẼẸỀỀỂỄỆỐỒỔỖỘỚỜỞỠỢ'
                r'ÚÙỦŨỤỨỪỬỮỰỲÝỶỸỴĐđ]'
            )
            return bool(vietnamese_pattern.search(text))      
        json_text = json.loads(clean_json(response_text))  
        json_text["description"] = None
        response_text_MoMo = MoMo(response_text=json.dumps(json_text), image=img)
        json_text_MoMo = json.loads(clean_json(response_text_MoMo))
        if contains_vietnamese_characters(json_text_MoMo["receiver"]["name"]): json_text_MoMo["receiver"]["bank"] = "MoMo"
        print("3. Response_text_MB: ", json_text_MoMo)
        print("----------------------------------------------------------------")
        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_MoMo))
    
    elif json_text_convert_bank['sender']['bank'] == "VNPay":
        response_text_VNPay = VNPay(response_text=response_text, image=img)
        json_text_VNPay = json.loads(clean_json(response_text_VNPay))
        print("3. Response_text_MB: ", json_text_VNPay)
        print("----------------------------------------------------------------")
        with st.chat_message("AI"):
            st.write(convert_bank_name(json_text_VNPay))

    
       
    else:
        with st.chat_message("AI"):
            if json_text['description'] is not None:
                json_text['description'] = unidecode(json_text['description'])
            print("*******************************")
            print(convert_bank_name(json_text))
            st.write(convert_bank_name(json_text))
