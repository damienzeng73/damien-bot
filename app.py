import requests, random
from bs4 import BeautifulSoup

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)

line_bot_api = LineBotApi('YOUR_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('YOUR_CHANNEL_SECRET')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def apple_news():
    target_url = 'https://tw.appledaily.com/new/realtime'
    res = requests.get(target_url)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('.rtddt a'), 0):
        if index == 10:
            return content

        heading = data.select_one('h1').text
        link = data['href']

        content += "{}\n{}\n\n".format(heading, link)


def movie_thisweek():
    target_url = 'https://tw.movies.yahoo.com/movie_thisweek.html'
    res = requests.get(target_url)
    soup = BeautifulSoup(res.text, 'html.parser')
    pages = len(soup.select_one('.page_numbox').find_all('li')) - 4
    content = ""

    for i in range(pages):
        if i == 0:
            pass
        else:
            target_url = 'https://tw.movies.yahoo.com/movie_thisweek.html?page={}'.format(str(i + 1))
            res = requests.get(target_url)
            soup = BeautifulSoup(res.text, 'html.parser')

        for data in soup.select('.release_info_text'):
            heading = data.find('div', attrs={'class': 'release_movie_name'}).find('a', attrs={'class': 'gabtn'}, href=True)
            name = heading.text.strip()
            link = heading['href']
            time = data.find('div', attrs={'class': 'release_movie_time'}).text.split('：')[1].strip()
            expectancy = data.find('div', attrs={'class': 'leveltext'}).select_one('span').text

            content += "{}\n{}\n期待度: {}\n{}\n\n".format(name, time, expectancy, link)

    return content


def movie_intheaters():
    target_url = 'https://tw.movies.yahoo.com/movie_intheaters.html'
    req = requests.get(target_url)
    res = BeautifulSoup(req.text, 'html.parser')
    content = ""

    for data in res.select('.release_info_text'):
        heading = data.find('div', attrs={'class': 'release_movie_name'}).find('a', attrs={'class': 'gabtn'}, href=True)
        name = heading.text.strip()
        link = heading['href']
        time = data.find('div', attrs={'class': 'release_movie_time'}).text.split('：')[1].strip()
        expectancy = data.find('div', attrs={'class': 'leveltext'}).select_one('span').text
        rate = data.find('div', attrs={'class': 'starwithnum'}).select_one('span')['data-num']

        content += "{}\n{}\n期待度: {}\n滿意度: {} 星\n{}\n\n".format(name, time, expectancy, rate, link)

    return content


def crawl_ptt(res, board, session=None):
    soup = BeautifulSoup(res.text, 'html.parser')
    content = []

    while (len(content) < 10):
        for data in soup.select('.r-ent'):
            if len(content) == 10:
                break

            if board == 'Gossiping':
                title = data.find('a', href=True)
                heading = title.text
                link = 'https://www.ptt.cc' + title['href']

                if '公告' in heading:
                    continue

                content.append("{}\n{}\n".format(heading, link))

            elif board == 'Beauty':
                pushes = data.select_one('.nrec').text
                if pushes == '爆' or (pushes != '' and 'X' not in pushes and int(pushes) > 10):
                    title = data.find('a', href=True)
                    heading = title.text
                    link = 'https://www.ptt.cc' + title['href']

                    if '公告' in heading:
                        continue

                    content.append("[{}推] {}\n{}\n".format(pushes, heading, link))

        last_page_url = 'https://www.ptt.cc' + soup.select('.btn.wide')[1]['href']
        if session is not None:
            res = session.get(last_page_url, verify=False)
        else:
            res = requests.get(last_page_url)

        soup = BeautifulSoup(res.text, 'html.parser')

    return content


def ptt_gossiping():
    rs = requests.session()
    data = {
        'from': '/bbs/Gossiping/index.html',
        'yes': 'yes'
    }

    res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=data)
    content = crawl_ptt(res, 'Gossiping', rs)

    return "\n".join(content)


def ptt_beauty():
    target_url = 'https://www.ptt.cc/bbs/Beauty/index.html'
    res = requests.get(target_url)
    content = crawl_ptt(res, 'Beauty')

    return "\n".join(content)


def ptt_random_pic():
    target_url = 'https://www.ptt.cc/bbs/Beauty/index.html'
    res = requests.get(target_url)
    soup = BeautifulSoup(res.text, 'html.parser')
    pic_urls = []

    while (len(pic_urls) < 1):
        for data in soup.select('.r-ent'):
            pushes = data.select_one('.nrec').text
            if pushes == '爆' or (pushes != '' and 'X' not in pushes and int(pushes) > 50):
                title = data.find('a', href=True)
                heading = title.text
                link = 'https://www.ptt.cc' + title['href']

                if '公告' in heading:
                    continue

                res2 = requests.get(link)
                soup2 = BeautifulSoup(res2.text, 'html.parser')

                for data2 in soup2.select_one('#main-content').find_all('a', href=True):
                    if 'https://i.imgur.com' in data2['href']:
                        pic_urls.append(data2['href'])

                break

        last_page_url = 'https://www.ptt.cc' + soup.select('.btn.wide')[1]['href']
        res = requests.get(last_page_url)
        soup = BeautifulSoup(res.text, 'html.parser')

    return random.choice(pic_urls)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == 'Apple news':
        content = apple_news()
    elif event.message.text == 'Movie thisweek':
        content = movie_thisweek()
    elif event.message.text == 'Movie intheaters':
        content = movie_intheaters()
    elif event.message.text == 'PTT Gossiping':
        content = ptt_gossiping()
    elif event.message.text == 'PTT Beauty':
        content = ptt_beauty()
    elif event.message.text == 'PTT random picture':
        content = ptt_random_pic()
        image_message = ImageSendMessage(
            original_content_url=content,
            preview_image_url=content
        )

        line_bot_api.reply_message(
            event.reply_token,
            image_message
        )

        return
    elif event.message.text == 'Yahoo movies':
        buttons_template = TemplateSendMessage(
            alt_text='目錄 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='本週新片',
                        text='Movie thisweek'
                    ),
                    MessageTemplateAction(
                        label='上映中',
                        text='Movie intheaters'
                    )
                ]
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            buttons_template
        )

        return
    elif event.message.text == 'PTT':
        buttons_template = TemplateSendMessage(
            alt_text='目錄 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='PTT八卦板最新文章',
                        text='PTT Gossiping'
                    ),
                    MessageTemplateAction(
                        label='PTT表特板大於10推文章',
                        text='PTT Beauty'
                    ),
                    MessageTemplateAction(
                        label='隨機一張表特正妹圖片',
                        text='PTT random picture'
                    )
                ]
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            buttons_template
        )

        return
    else:
        buttons_template = TemplateSendMessage(
            alt_text='目錄 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                actions=[
                    MessageTemplateAction(
                        label='即時新聞',
                        text='Apple news'
                    ),
                    MessageTemplateAction(
                        label='Yahoo奇摩電影',
                        text='Yahoo movies'
                    ),
                    MessageTemplateAction(
                        label='PTT',
                        text='PTT'
                    ),
                    URITemplateAction(
                        label='查看原始碼',
                        uri='https://github.com/damnee562/Damien-bot'
                    )
                ]
            )
        )

        line_bot_api.reply_message(
            event.reply_token,
            buttons_template
        )

        return

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=content)
    )


if __name__ == "__main__":
    app.run()
