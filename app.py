import requests
from bs4 import BeautifulSoup

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

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
    req = requests.get(target_url)
    soup = BeautifulSoup(req.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('.rtddt a'), 0):
        if index == 10:
            return content

        url = data['href']
        req = requests.get(url)
        soup = BeautifulSoup(req.text, 'html.parser')
        heading = soup.find('article', attrs={'class': 'ndArticle_leftColumn'}).find('h1').text
        link = data['href']

        content += "{}\n{}\n\n".format(heading, link)


def yahoo_movies():
    target_url = 'https://tw.movies.yahoo.com/movie_thisweek.html'
    req = requests.get(target_url)
    soup = BeautifulSoup(req.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('.release_info_text'), 0):
        heading = data.find('div', attrs={'class': 'release_movie_name'}).find('a', attrs={'class': 'gabtn'}, href=True)
        name = heading.text.strip()
        link = heading['href']
        time = data.find('div', attrs={'class': 'release_movie_time'}).text.split('：')[1].strip()

        content += "{}\n{}\n{}\n\n".format(name, time, link)

    return content


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.message.text == 'Apple news':
        content = apple_news()
    elif event.message.text == 'Yahoo movies':
        content = yahoo_movies()
    else:
        content = event.message.text

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=content)
    )


if __name__ == "__main__":
    app.run()
