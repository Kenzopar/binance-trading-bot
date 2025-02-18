from calculate import Calculate
from binance.enums import *
from binance.client import Client
import json, config

from werkzeug.utils import redirect
from flask import Flask, request, render_template
import datetime
from binance.client import Client

calculate = Calculate()
client = Client(config.API_KEY, config.API_SECRET)

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def welcome():
    calculate.update_current_profit()
    current_profit = calculate.get_total_current_profit()
    current_year = datetime.datetime.now().year
    running_trades = calculate.get_running_trades()
    all_trades = calculate.get_all_trades()
    total_profit = int(calculate.get_total_profit())
    usdt_balance = calculate.get_usdt_balance()

    if request.method == "POST":
        data = request.form
        password = data["password"]

        if password == config.WEBHOOK_PASSWORD:
            calculate.append_running_trades(data["coinpair"], int(data["interval"]), float(data["quantity"]),
                                            data["portion_size"], data["side"],
                                            sl_id="manual trades, No SL could be set")

            return redirect('/')
        else:
            return redirect('/')
    return render_template('index.html', current_profit=current_profit, usdt_balance=usdt_balance,
                           all_trades=all_trades, total_profit=total_profit, current_year=current_year,
                           running_trades=running_trades)


if __name__ == "__main__":
    app.run(host='0.0.0.0')


@app.route('/webhook', methods=['POST'])
def webhook():
    data = {}
    try:
        data = json.loads(request.data)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return {"code": "error",
                "message": "Unable to read webhook"}

    if data['passphrase'] != config.WEBHOOK_PASSWORD:
        return {
            "code": "error",
            "message": "Nice try, invalid passphrase"
        }

    interval = data['interval']
    coin_pair = data['ticker']
    signal = data['signal']
    stop_price = 0
    if signal == "ENTRY LONG" or signal == "ENTRY SHORT":
        stop_price = data['stopprice']
        entry_price = data['entryprice']
        usdt_balance = calculate.get_usdt_balance()
        if signal == "ENTRY LONG":

            sl_percent = round((1 - (stop_price / entry_price)), 4)
            portion_size = calculate.portion_size(
                usdt_balance, sl_percent)

            quantity = calculate.convert_portion_size_to_quantity(
                coin_pair, portion_size)
            side = "BUY"
            order_response = calculate.order(side, quantity,
                                             coin_pair, interval, portion_size, stop_price)

        elif signal == "ENTRY SHORT":

            sl_percent = round(((stop_price / entry_price) - 1), 4)
            portion_size = calculate.portion_size(
                usdt_balance, sl_percent)

            quantity = calculate.convert_portion_size_to_quantity(
                coin_pair, portion_size)

            print("SL ", sl_percent, "portionS ", portion_size, "Q ", quantity)
            side = "SELL"
            order_response = calculate.short_order(side, quantity,
                                                   coin_pair, interval, portion_size, stop_price)

    elif signal == "EXIT LONG":
        side = "SELL"
        quantity = 0
        portion_size = 0
        order_response = calculate.order(side, quantity,
                                         coin_pair, interval, portion_size, stop_price)

    elif signal == "EXIT SHORT":
        side = "BUY"
        quantity = 0
        portion_size = 0
        order_response = calculate.short_order(side, quantity,
                                               coin_pair, interval, portion_size, stop_price)
    else:
        return "An error occured, can read the signal"

    if order_response:
        return {
            "code": "success",
            "message": "order executed"
        }
    else:
        print("order failed")

        return {
            "code": "error",
            "message": "order failed"

        }
