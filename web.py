import os
import inspect
import json
import gradio as gr
from openai import AzureOpenAI
from recognizeTextSample import get_ocr_text

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
            "description": "OCR统一识别接口支持识别多种图片类型",
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
]
available_functions = {
    "get_ocr_text": get_ocr_text
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


def captioner(image):
    print(image)
    return image, "faker result"

demo = gr.Interface(fn=captioner,
                inputs=[gr.Image(label="Upload image", type="pil")],
                outputs=[gr.Image(type="pil"), gr.Textbox(label="识别结果")],
                title="文字识别OCR",
                description="识别上传的图片中的文字",
                allow_flagging="never")

if __name__ == '__main__':
    # messages = [
    #  {
    #     "role": "system",
    #     "content": "Assistant is a helpful assistant that helps users get answers to questions. Assistant has access to several tools and sometimes you may need to call multiple tools in sequence to get answers for your users.用中文回答",
    #     }
    # ]    
    # messages.append({"role": "user", "content": "请描述这张图片:url=https://gimg2.baidu.com/image_search/src=http%3A%2F%2Fsafe-img.xhscdn.com%2Fbw1%2F227bb9d7-99ac-490f-9172-3e332677f6bf%3FimageView2%2F2%2Fw%2F1080%2Fformat%2Fjpg&refer=http%3A%2F%2Fsafe-img.xhscdn.com&app=2002&size=f9999,10000&q=a80&n=0&g=0n&fmt=auto?sec=1711779614&t=2041c9d3969f147f293f1d7218503d36"})
    # print("Final Response:")
    # assistant_response = run_conversation(messages, tools, available_functions)
    # print(assistant_response.choices[0].message)

   

    demo.launch(share=True)



