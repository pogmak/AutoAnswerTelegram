from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.errors import SlowModeWaitError, FloodWaitError, ChatWriteForbiddenError
from loguru import logger
import asyncio
import json
from random import randint
from time import sleep

#api_id = 2922111
#api_hash = '4e17120aa94db32afb51e17a405106d8'
#phone_number = '+79991399680'
api_id = 3465320
api_hash = '47581ba0537e10f91f67136268f5f098'
phone_number = '+79034331901'
exclude_chats_for_flood = []
queue = 0
queue_chats = []
piar_chats = []

client = TelegramClient('session_test', api_id, api_hash)

# Получаем чаты из файла
with open('chats.txt', 'r', encoding='utf-8') as f:
    chats = f.readlines()
chats_to_join = []

async def join_to_chats(client, chats: list):
    #Вступаем в чаты
    for i, chat in enumerate(chats):
        try:
            await client(JoinChannelRequest(chat))
            logger.info(f"[{i+1}] Successful join to {chat}")
            sleep_time = randint(60, 120)
            logger.info(f"Засыпаем на {sleep_time} секунд!")
            await asyncio.sleep(sleep_time)
        except ValueError:
            logger.error(f"{chat} not found!")
        finally:
            chats.__delitem__(i)

@logger.catch()
async def main():
    global piar_chats, chats_to_join
    await client.connect()
    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        me = await client.sign_in(phone_number, input("Enter code:"))
    my_dialogs = [x.entity.username for x in (await client.get_dialogs())]
    chats_to_join = [x.strip() for x in chats if x.strip() not in my_dialogs]
    #Загружаем ответы
    with open('answers.json', encoding='utf-8') as f:
        answers = json.load(f)
    answers = answers['answers']

    piar_chats = [x.strip() for x in chats if x.strip() in my_dialogs]
    logger.info(f"Запускаем автоответчик на {piar_chats.__len__()} чатов: {piar_chats}")

    @client.on(events.NewMessage(chats=tuple(piar_chats),incoming=True))
    async def my_event_handler(event):
        global queue, exclude_chats_for_flood, queue_chats
        chat_name = (await event.get_chat()).username
        # Охлаждаем пыл кучи Events. Усыпляем их на входе на рандомное время, иначе проверку дальше все одновременно
        # проскакивают
        await asyncio.sleep(randint(1, 5))
        # queue - ограничение на количество чатов в очереди, queue_chats - чтобы не спамить в один и тот же чат
        if queue >= 16 or chat_name in queue_chats:
            return 0
        #Отвечаем через радномное время от 60 сек до 300
        sleep_async = randint(60, 300)
        queue += 1
        queue_chats.append(chat_name)
        logger.info(f"Получили сообщение из чата: {chat_name} засыпаем на {sleep_async}. В очереди: {queue}")
        await asyncio.sleep(sleep_async)
        if chat_name not in exclude_chats_for_flood:
            try:
                await event.reply(answers[randint(0, len(answers)-1)])
            except SlowModeWaitError:
                exclude_chats_for_flood.append(chat_name)
                logger.error(f"Исключаем чат {chat_name} из-за ошибки флуда!\n"
                             f"Всего исключено:{exclude_chats_for_flood.__len__()}")
                return 0
            except FloodWaitError as e:
                logger.error(f"Жестокая ошибка флуда: {e}. Засыпаем на 300 секунд")
                sleep(300)
                return 0
            except ChatWriteForbiddenError:
                exclude_chats_for_flood.append(chat_name)
                logger.error(f"Исключаем чат {chat_name} из-за того, что нам запретили там писать сообщения!\n"
                             f"Всего исключено:{exclude_chats_for_flood.__len__()}")
            logger.info(f"Ответили в чате:{chat_name}")
            queue_chats = [x for x in queue_chats if x != chat_name]
            queue -= 1
            piar_chats = [x.strip() for x in chats if x.strip() in my_dialogs]
            return 0

    await client.start()
    await client.run_until_disconnected()


def repeat(coro, loop):
    asyncio.ensure_future(coro(client, [chats_to_join[randint(0, len(chats_to_join)-1)]]), loop=loop)
    loop.call_later(60 * 10, repeat, join_to_chats, loop)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.call_later(60*10, repeat, join_to_chats, loop)
    loop.run_until_complete(main())