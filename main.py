import os
import random
import time
import asyncio
from astrbot.core.message.components import Image
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.api.all import *



@register("quote_collocter", "浅夏旧入梦", "发送“语录投稿+图片”来存储群友的黑历史！bot会在被戳一戳时随机发送一张语录", "1.0")
class AnswerBookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.quotes_data_path = os.path.join('data', "quotes_data")
    #region 数据管理
	#创建主数据文件夹
    def create_main_folder(self):
        target_folder = os.path.join('data', "quotes_data")
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

    #为每个群单独创建文件夹
    def create_group_folder(self, group_id):
        group_id = str(group_id)
        if not os.path.exists(self.quotes_data_path):
            self.create_main_folder()
        group_folder_path = os.path.join(self.quotes_data_path, group_id)
        if not os.path.exists(group_folder_path):
            os.makedirs(group_folder_path)

	#随机从指定群聊的文件夹选择一张图片		
    def random_image_from_folder(self,folder_path):
        # 获取文件夹中所有文件
        files = os.listdir(folder_path)
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        images = [file for file in files if os.path.splitext(file)[1].lower() in image_extensions]
        # 随机选择一张图片
        random_image = random.choice(images)
        return os.path.join(folder_path, random_image)

    #region 下载语录图片
    #下载图片并保存到本地
    async def download_image(self, event: AstrMessageEvent, file_id: str,group_id) -> bytes:
        try:
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            payloads = {
                "file_id": file_id
            }
            
            # 调用获取图片消息API
            result = await client.api.call_action('get_image', **payloads)            

            # 从本地缓存文件读取
            file_path = result.get('file')
            if file_path:
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                        filename = f"image_{int(time.time() * 1000)}.jpg"
                        file_path = os.path.join("data", "quotes_data",group_id, filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        # 保存图片到本地
                        with open(file_path, 'wb') as f:
                            f.write(data)
                            print(f"图片已保存到 {file_path}")
                        return file_path
                except Exception as e:
                    file_error = str(e)
                    print(f"在读取本地图片时遇到问题: {file_error}")
        except Exception as e:
            raise Exception(f"获取图片数据失败: {str(e)}")

    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):

        group_id = str(event.message_obj.group_id)
        message_obj = event.message_obj
        raw_message = message_obj.raw_message
        msg = event.message_str.strip()

        # region 投稿系统
        if msg.startswith("语录投稿"):
            messages = event.get_messages()
            image = next((msg for msg in messages if isinstance(msg, Image)), None)
            if not image:
                return
                            
            try:
                # 获取图片file_id
                file_id = image.file
                self.create_group_folder(group_id)
                group_folder_path = os.path.join(self.quotes_data_path, group_id)
                if not file_id:
                    yield event.plain_result("获取图片id失败")
                    return
                 # 下载并保存图片
                try:
                    await self.download_image(event,file_id,group_id)
                    msg_id = str(event.message_obj.message_id)
                    chain = [
                        Reply(id=msg_id),
                        Plain(text="语录投稿成功！")
                        ]
                    yield event.chain_result(chain)
                except Exception as e:
                    print(f"保存图片失败: {e}")

            except Exception as e:
                # 创建错误提示
                yield (event.make_result().message(f"\n错误信息：{str(e)}"))
                

        #region 戳一戳检测
        if raw_message.get('post_type') == 'notice' and \
                raw_message.get('notice_type') == 'notify' and \
                raw_message.get('sub_type') == 'poke':
            bot_id = raw_message.get('self_id')
            sender_id = raw_message.get('user_id')
            target_id = raw_message.get('target_id')

            if bot_id and sender_id and target_id:
                if str(target_id) == str(bot_id):
                    #80%概率发送语录
                    if random.random() < 0.80:
                        group_folder_path = os.path.join(self.quotes_data_path, group_id)
                        if not os.path.exists(group_folder_path):
                           yield event.plain_result("本群还没有群友语录哦~\n请发送“语录投稿+图片”进行添加！")
                           return
                        selected_image_path = self.random_image_from_folder(group_folder_path)
                        yield event.image_result(selected_image_path)
                    #发送文案
                    else:                   
                        texts = [
                            " 再戳的话......说不定下一张就是你的！",
                            " 我会一直一直看着你👀",
                            " 给我出列！",
                        ]
                        # 随机选择一个文案
                        selected_text = random.choice(texts)
                        chain = [
                            At(qq=sender_id),
                            Plain(text=selected_text)
                        ]
                        yield event.chain_result(chain)
