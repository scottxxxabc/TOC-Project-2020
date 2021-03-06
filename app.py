import os
import sys

from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, PostbackEvent

from fsm import TocMachine
from utils import send_text_message

load_dotenv()


machine = TocMachine(
    states=["user", "starburstpolice", "starburst", "meme", "help", "wordmanage", "fsm"],
    transitions=[
        {
            "trigger": "advance",
            "source": "user",
            "dest": "starburstpolice",
            "conditions": "is_going_to_starburstpolice",
        },
        {
            "trigger": "exitstarburst",
            "source": "starburstpolice",
            "dest": "user",
            "conditions": "exit_starburstpolice",
        },
        {
            "trigger": "check",
            "source": "starburstpolice",
            "dest": "starburst",
            "conditions": "is_going_to_starburst",
        },
        {"trigger": "check_end", "source": "starburstpolice", "dest": "user"},
        {"trigger": "starburst_end", "source": "starburst", "dest": "starburstpolice"},
        {"trigger": "manage_end", "source": "wordmanage", "dest": "user"},
        {
            "trigger": "advance",
            "source": "user",
            "dest": "meme",
            "conditions": "is_going_to_meme",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "wordmanage",
            "conditions": "is_going_to_wordmanage",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "help",
            "conditions": "is_going_to_help",
        },
        {
            "trigger": "advance",
            "source": "user",
            "dest": "fsm",
            "conditions": "is_going_to_fsm",
        },
        {"trigger": "go_back", "source": ["meme", "help", "fsm"], "dest": "user"},
        {"trigger": "go_fsm", "source": "user", "dest": "fsm"},

    ],
    initial="user",
    auto_transitions=False,
    show_conditions=True,
)

app = Flask(__name__, static_url_path="")


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=event.message.text)
        )

    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if isinstance(event, PostbackEvent):
            machine.test(event)
            continue
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        if not isinstance(event.message.text, str):
            continue
        print(f"\nFSM STATE: {machine.state}")
        print(f"REQUEST BODY: \n{body}")
        
        machine.test(event)
        
    
    return "OK"


@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    machine.get_graph().draw("./fsm.svg", prog="dot", format="svg")
    return send_file("./fsm.svg", mimetype="image/svg")


if __name__ == "__main__":
    port = os.environ.get("PORT", 8000)
    app.run(host="0.0.0.0", port=port, debug=True)
