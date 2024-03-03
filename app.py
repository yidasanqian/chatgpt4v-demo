import os
import inspect
import json
import shutil
from turtle import width
import uuid
from altair import value
import gradio as gr
from openai import AzureOpenAI
from recognizeTextSample import get_ocr_text,get_ocr_text_from_filepath

api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key= os.getenv("AZURE_OPENAI_API_KEY")
api_version="2024-02-15-preview",
model_name = 'gpt-4' #Replace with model deployment name

client = AzureOpenAI(
    api_key=api_key,  
    azure_endpoint=api_base,
    api_version=api_version
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_ocr_text",
            "description": "OCR统一识别接口支持识别多种图片类型，从图片链接url读取参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "图片链接（长度不超过 2048，不支持 base64）。示例值:https://example.png",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ocr_text_from_filepath",
            "description": "OCR统一识别接口支持识别多种图片类型，从文件路径filepath读取参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "图片路径。示例值:/tmp/example.png",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
]
available_functions = {
    "get_ocr_text": get_ocr_text,
    "get_ocr_text_from_filepath": get_ocr_text_from_filepath
}

# helper method used to check if the correct arguments are provided to a function
def check_args(function, args):
    sig = inspect.signature(function)
    params = sig.parameters

    # Check if there are extra arguments
    for name in args:
        if name not in params:
            return False
    # Check if the required arguments are provided
    for name, param in params.items():
        if param.default is param.empty and name not in args:
            return False

    return True

def run_conversation(messages, tools, available_functions):
    # Step 1: send the conversation and available functions to GPT
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    response_message = response.choices[0].message

    # Step 2: check if GPT wanted to call a function
    if response_message.tool_calls:
        print("Recommended Function call:")
        print(response_message.tool_calls[0])
        print()

        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors

        function_name = response_message.tool_calls[0].function.name

        # verify function exists
        if function_name not in available_functions:
            return "Function " + function_name + " does not exist"
        function_to_call = available_functions[function_name]

        # verify function has correct number of arguments
        function_args = json.loads(response_message.tool_calls[0].function.arguments)
        if check_args(function_to_call, function_args) is False:
            return "Invalid number of arguments for function: " + function_name
        function_response = function_to_call(**function_args)

        print("Output of function call:")
        print(function_response)
        print()

        # Step 4: send the info on the function call and function response to GPT

        # adding assistant response to messages
        messages.append(
            {
                "role": response_message.role,
                "function_call": {
                    "name": response_message.tool_calls[0].function.name,
                    "arguments": response_message.tool_calls[0].function.arguments,
                },
                "content": None,
            }
        )

        # adding function response to messages
        messages.append(
            {
                "role": "function",
                "name": function_name,
                "content": function_response,
            }
        )  # extend conversation with function response

        print("Messages in second request:")
        for message in messages:
            print(message)
        print()

        second_response = client.chat.completions.create(
            messages=messages,
            model=model_name
        )  # get a new response from GPT where it can see the function response

        return second_response
    return response

# 目标文件夹路径
target_folder = "/tmp/upload/"
latest_file = []

def add_text(history, text, img):
    if img is not None:
        history += add_file(history, img)
    
    if len(text.strip()) > 0:
        history = history + [(text, None)]
    return history, gr.Textbox(value="", interactive=False)

def add_file(history, file):
    history = history + [((file,), None)]
    # 获取文件后缀名
    source_file = file
    file_extension = os.path.splitext(source_file)[1]
    # 生成UUID作为新文件名
    new_filename = str(uuid.uuid4()) + file_extension
    # 判断目标文件夹是否存在，如果不存在则创建
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    target_file = os.path.join(target_folder, new_filename)
    # 复制文件并重命名
    shutil.copy(source_file, target_file)
    latest_file.append(target_file)
    return history

messages = [] 
def bot(history):
    if len(messages) == 0:
        messages.append( {
            "role": "system",
            "content": """Assistant is a helpful assistant that helps users get answers to questions.
             Assistant has access to several tools and sometimes you may need to call multiple tools in sequence to get answers for your users.
            若进行了图片识别，以json格式输出答案。
            用中文回答。
            """,
            })
    
    content = None
    if len(history) > 0:
        if os.path.isfile(history[-1][0][0]):
            # 只发送了图片
            history[-1][1] = "如果您有具体的问题或者需要帮助处理图片，请告诉我您的需求"
            return history
        else:
            content = history[-1][0]
    if len(latest_file) > 0:
        content = f"{content} filepath={latest_file[0]}" if content else f"filepath={latest_file[0]}"
    if content:
        messages.append({
            "role": "user",
            "content": content
        })
        assistant_response = run_conversation(messages, tools, available_functions)
        history[-1][1] = assistant_response.choices[0].message.content

    latest_file.clear()
    return history

def clear_history(history, *args):
    history = []
    messages.clear()
    print("新会话")
    return history, gr.Textbox(interactive=True), None

if __name__ == '__main__':
    with gr.Blocks() as demo:
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            bubble_full_width=False,
            avatar_images=(None, (os.path.join(os.path.dirname(__file__), "avatar.jpg"))),
        )

        with gr.Row():
            txt = gr.Textbox(
                scale=4,
                show_label=False,
                placeholder="输入文本，或上传图像",
                container=False,
            )
            submit_button = gr.Button(value="提交", variant="primary")
            clear = gr.ClearButton([chatbot, txt],value="新会话")

        btn = gr.Image(elem_id="img", type="filepath", label="上传图像", height=300)
    
        txt_msg = submit_button.click(add_text, [chatbot, txt, btn], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot, api_name="bot_response"
        )
        # 清理image组件图片
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False).then(
            lambda: gr.update(elem_id="img", value=None), None, [btn], queue=False
        )
        clear.click(clear_history, [chatbot, txt, btn], [chatbot, txt, btn], queue=False)
    demo.queue().launch(share=True)



