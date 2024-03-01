import os
import inspect
import json
import shutil
import uuid
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

 
def add_text(history, text):
    history = history + [(text, None)]
    return history, gr.Textbox(value="", interactive=False)

# 目标文件夹路径
target_folder = "/tmp/upload/"
latest_file = []

def add_file(history, file):
    history = history + [((file.name,), None)]
    # 获取文件后缀名
    source_file = file.name
    file_extension = os.path.splitext(source_file)[1]
    # 生成UUID作为新文件名
    new_filename = str(uuid.uuid4()) + file_extension
    # 目标文件路径
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
            "content": "Assistant is a helpful assistant that helps users get answers to questions. Assistant has access to several tools and sometimes you may need to call multiple tools in sequence to get answers for your users.用中文回答",
            })
 
    
    messages.append({
        "role": "user",
        "content": f"识别图片filepath={latest_file[0]}" if len(latest_file)>0 else history[-1][0]
    })
    assistant_response = run_conversation(messages, tools, available_functions)
    latest_file.clear();
    history[-1][1] = assistant_response.choices[0].message.content;
    return history

def clear_history(history, *args):
    history = []
    messages.clear()
    print("新会话")
    return history, gr.Textbox(value="")

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
                placeholder="输入文本并按回车键，或上传图像",
                container=False,
            )
            btn = gr.UploadButton("📁", file_types=["image"])
            clear = gr.ClearButton([chatbot, txt])

        txt_msg = txt.submit(add_text, [chatbot, txt], [chatbot, txt], queue=False).then(
            bot, chatbot, chatbot, api_name="bot_response"
        )
        txt_msg.then(lambda: gr.Textbox(interactive=True), None, [txt], queue=False)
        file_msg = btn.upload(add_file, [chatbot, btn], [chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        clear.click(clear_history, [chatbot, txt], [chatbot, txt], queue=False)
    demo.queue().launch(share=True)



