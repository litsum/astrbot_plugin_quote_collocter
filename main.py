import os
import random
import time
import asyncio
import json
import yaml
from astrbot.core.message.components import Image
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from astrbot.api.all import *



@register("quote_collocter", "浅夏旧入梦", "发送“语录投稿+图片”来存储群友的黑历史！bot会在被戳一戳时随机发送一张语录", "1.0")
class AnswerBookPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.quotes_data_path = os.path.join('data', "quotes_data")
        self.admins = self._load_admins()  # 加载管理员列表
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
    #region 权限管理
    def _load_admins(self):
        """加载管理员列表"""
        try:
            with open(os.path.join('data', 'cmd_config.json'), 'r', encoding='utf-8-sig') as f:
                config = json.load(f)
                return config.get('admins_id', [])
        except Exception as e:
            self.context.logger.error(f"加载管理员出错: {str(e)}")
            return []

    def is_admin(self, user_id):
        return str(user_id) in self.admins
    def _create_admin_settings_file(self):
        """创建模式文件"""
        try:
            default_data = {'mode': 0}  # 默认初始化mode为0
            with open(self.admin_settings_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_data, f)
        except Exception as e:
            self.context.logger.error(f"创建模式文件失败: {str(e)}")

    def _load_admin_settings(self):
        """加载模式数据"""    
        try:
            with open(self.admin_settings_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            return data
        except Exception as e:
            self.context.logger.error(f"加载模式数据失败: {str(e)}")
            return {}
    def _save_admin_settings(self):
        """保存模式数据"""
        try:
            with open(self.admin_settings_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.admin_settings, f, allow_unicode=True)
        except Exception as e:
            self.context.logger.error(f"保存模式数据失败: {str(e)}")
    def gain_mode(self, event):
        """解析消息文本中的数值"""
        value = None
        msg = event.message_str.strip()
        if msg:
            import re
            match = re.search(r"[-+]?\d*\.?\d+", msg)
            if match:
                value = match.group()    
        return value

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
        user_id = str(event.get_sender_id())
        message_obj = event.message_obj
        raw_message = message_obj.raw_message
        msg = event.message_str.strip()
        group_folder_path = os.path.join(self.quotes_data_path, group_id)
        if not os.path.exists(group_folder_path):
            self.create_group_folder(group_id)
        self.admin_settings_path = os.path.join(group_folder_path, 'admin_settings.yml') 
        if not os.path.exists(self.admin_settings_path):
            self._create_admin_settings_file()
        self.admin_settings=self._load_admin_settings()
        # region 投稿系统
        if msg.startswith("投稿权限"):
            if not self.is_admin(user_id):
                yield event.plain_result("权限不足，仅可由bot管理员设置")
                return
            set_mode=self.gain_mode(event)
            if not set_mode:
                yield event.plain_result(f"⭐请输入“投稿权限+数字”来设置\n  0：关闭投稿系统\n  1：仅管理员可投稿\n  2：全体成员均可投稿\n当前群聊权限设置为：{self.admin_settings['mode']}")
            else:
                if set_mode not in ["0","1","2"]:
                    yield event.plain_result("⭐模式数字范围出错！请输入正确的模式\n  0：关闭投稿系统\n  1：仅管理员可投稿\n  2：全体成员均可投稿")
                    return
                self.admin_settings['mode'] = int(set_mode)
                self._save_admin_settings()
                texts=f"⭐投稿权限设置成功，当前状态为："
                if self.admin_settings['mode'] == 0:
                    texts+="\n  0：关闭投稿系统"
                elif self.admin_settings['mode'] == 1:
                    texts+="\n  1：仅管理员可投稿"
                elif self.admin_settings['mode'] == 2:
                    texts+="\n  2：全体成员均可投稿"
                yield event.plain_result(texts)

        elif msg.startswith("语录投稿"):

            print("投稿系统模式：",self.admin_settings['mode'])
            if self.admin_settings['mode'] == 0:
                yield event.plain_result("⭐投稿系统未开启，请联系bot管理员发送“投稿权限”来设置")
                return
            if self.admin_settings['mode'] == 1:
                if not self.is_admin(user_id):
                    yield event.plain_result("⭐权限不足，当前权限设置为“仅管理员可投稿”\n可由bot管理员发送“投稿权限”来设置")
                    return
            messages = event.get_messages()
            image = next((msg for msg in messages if isinstance(msg, Image)), None)
            if not image:
                chain = [
                    At(qq=user_id),
                    Plain(text=" 你是不是忘发图啦？")
                    ]
                yield event.chain_result(chain)
                return
                            
            try:
                # 获取图片file_id
                file_id = image.file
                self.create_group_folder(group_id)

                if not file_id:
                    yield event.plain_result("获取图片id失败")
                    return
                 # 下载并保存图片
                try:
                    await self.download_image(event,file_id,group_id)
                    msg_id = str(event.message_obj.message_id)
                    chain = [
                        Reply(id=msg_id),
                        Plain(text="⭐语录投稿成功！")
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
                    #85%概率发送语录
                    if random.random() < 0.85:
                        group_folder_path = os.path.join(self.quotes_data_path, group_id)
                        if not os.path.exists(group_folder_path):
                           yield event.plain_result("⭐本群还没有群友语录哦~\n请发送“语录投稿+图片”进行添加！")
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
