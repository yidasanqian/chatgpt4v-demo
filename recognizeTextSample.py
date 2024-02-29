
import os
import json
from alibabacloud_ocr_api20210707.client import Client as ocr_api20210707Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707 import models as ocr_api_20210707_models
from alibabacloud_tea_util.client import Client as UtilClient
from alibabacloud_tea_util import models as util_models

access_key = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
access_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')

def create_client(
        access_key_id: str,
        access_key_secret: str,
    ) -> ocr_api20210707Client:
        """
        使用AK&SK初始化账号Client
        @param access_key_id:
        @param access_key_secret:
        @return: Client
        @throws Exception
        """
        config = open_api_models.Config(
            # 必填，您的 AccessKey ID,
            access_key_id=access_key_id,
            # 必填，您的 AccessKey Secret,
            access_key_secret=access_key_secret
        )
        # Endpoint 请参考 https://api.aliyun.com/product/ocr-api
        config.endpoint = f'ocr-api.cn-hangzhou.aliyuncs.com'
        return ocr_api20210707Client(config)

def get_ocr_text(url):
    client = create_client(access_key, access_secret)
    recognize_all_text_request = ocr_api_20210707_models.RecognizeAllTextRequest(
            type='General',
            output_figure=True,
            output_coordinate=UtilClient.to_bytes('points'),
            url=url
        )
    runtime = util_models.RuntimeOptions()
    try:
        # 复制代码运行请自行打印 API 的返回值
        resp = client.recognize_all_text_with_options(recognize_all_text_request, runtime)
        return str(resp.body)
    except Exception as error:
        # 错误 message
        print(error.message)
        # 诊断地址
        print(error.data.get("Recommend"))
        UtilClient.assert_as_string(error.message)

if __name__ == '__main__':
    url = "https://gimg2.baidu.com/image_search/src=http%3A%2F%2Fsafe-img.xhscdn.com%2Fbw1%2F227bb9d7-99ac-490f-9172-3e332677f6bf%3FimageView2%2F2%2Fw%2F1080%2Fformat%2Fjpg&refer=http%3A%2F%2Fsafe-img.xhscdn.com&app=2002&size=f9999,10000&q=a80&n=0&g=0n&fmt=auto?sec=1711779614&t=2041c9d3969f147f293f1d7218503d36"
    text = get_ocr_text(url)
    print(f"resp:{text}")      