import requests
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


def yahoo_movies():
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


def crawl_ptt(res):
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('.r-ent'), 0):
        pushes = data.select_one('.nrec').text
        if pushes == '爆' or (pushes != '' and 'X' not in pushes and int(pushes) > 10):
            title = data.find('a', href=True)
            heading = title.text
            link = 'https://www.ptt.cc' + title['href']

            content += "{}\n{}\n\n".format(heading, link)

    return content


def ptt_gossiping():
    rs = requests.session()
    data = {
        'from': '/bbs/Gossiping/index.html',
        'yes': 'yes'
    }

    res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=data)
    soup = BeautifulSoup(res.text, 'html.parser')
    last_page_url = 'https://www.ptt.cc' + soup.select('.btn.wide')[1]['href']
    content = ""

    while (len(content.split('https')) - 1) < 10:
        current_page_index = last_page_url.split('index')[1].split('.html')[0]
        last_page_url = 'https://www.ptt.cc' + '/bbs/Gossiping/index{}.html'.format(str(int(current_page_index) - 1))

        res = rs.get(last_page_url, verify=False)
        content += crawl_ptt(res)

    return content


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == 'Apple news':
        content = apple_news()
    elif event.message.text == 'Yahoo movies':
        content = yahoo_movies()
    elif event.message.text == 'PTT Gossiping':
        content = ptt_gossiping()
    else:
        content = event.message.text

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
                        label='本週上映電影',
                        text='Yahoo movies'
                    ),
                    MessageTemplateAction(
                        label='PTT八卦板大於10推文章',
                        text='PTT Gossiping'
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
