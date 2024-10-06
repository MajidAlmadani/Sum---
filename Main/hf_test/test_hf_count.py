from gradio_client import Client, handle_file

client = Client("coolfrxcrazy/YOLO_MODEL_DETECTION")
result_in = client.predict(
    video={"video": handle_file('/Users/cornflex/Desktop/Project/T5/T5-CapstoneProject/Main/hf_test/IMG_9462.MOV')},
    api_name="/count_in"  # Correct api_name for counting in
)
print(result_in)


# from gradio_client import Client, handle_file

# client = Client("coolfrxcrazy/YOLO_MODEL_DETECTION")
# result_in = client.predict(
#     video={"video": handle_file('/Users/cornflex/Desktop/Project/T5/T5-CapstoneProject/Main/WhatsApp Video 2024-10-02 at 21.29.34.mp4')},
#     api_name="/count_out"  # Correct api_name for counting in
# )
# print(result_in)