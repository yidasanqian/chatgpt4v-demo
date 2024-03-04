# chatgpt4v-demo

## 环境搭建
```
git clone https://github.com/yidasanqian/chatgpt4v-demo.git
conda create -n chatgpt4v python=3.10
conda activate chatgpt4v
cd chatgpt4v-demo
pip install -r requirements.txt
```

### 阿里云的ocr接口

https://api.aliyun.com/document/ocr-api/2021-07-07/RecognizeAllText

### 阿里云的AccessKey

https://help.aliyun.com/zh/ram/user-guide/create-an-accesskey-pair

### 环境变量
`chatgpt4v-demo`目录下创建文件`.env`，内容如下：
```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
# 阿里云的AccessKey及Secret
ALIBABA_CLOUD_ACCESS_KEY_ID=
ALIBABA_CLOUD_ACCESS_KEY_SECRET=
```

### 本地运行
```
gradio app.py
```

### ModelScope在线运行
[复制chatgpt4v-demo](https://modelscope.cn/studios/fork?target=yidasanqian/chatgpt4v-demo)