import pymysql
import os
from dotenv import load_dotenv

class Backtest_Engine:

    def __init__(self, table, time_frame, market):
        print('Backtest_Engine Running...')

        # 2천만원
        self.initial_capital = 20000000.0
        self.available_capital = self.initial_capital

        # Final Result
        self.end_capital = None

        # Boolean for whether stock is being held or not
        self.stock_held = False
        self.stock_held_percentage = 0.0

        # Number of stocks bought
        self.num_bought = 0
        # Amount of stocks bought in won value
        self.amount_bought = 0.0

        # Commission fees default to 1%
        self.commission_fee = 0.01
        # self.start_date = None
        # self.end_date = datetime.datetime.now()

        # For checking number of trades
        self.cnt = 0

        self.temp_buy_date = None
        self.temp_buy_date_price = None
        self.temp_sell_date = None
        self.temp_sell_date_price = None

        # Used to show results

        # 복리 수익률
        self.cagr = 0
        # 수익금
        self.total_gains_dollar = 0
        # 수익률
        self.total_gains_percentage = 0
        # 거래별 승리 횟수
        self.wins = 0
        # 거래별 실패 횟수
        self.losses = 0
        # 거래별 동점 횟수
        self.ties = 0
        # 승률
        self.win_rate = 0
        # 거래별 수익률
        self.trades = []
        # 손익비
        self.pl_ratio = 0
        self.mdd = 0

        load_dotenv()

        AUTHENTICATION_PASSWORD = os.environ.get('AUTHENTICATION_PASSWORD')

        conn = pymysql.connect(host='127.0.0.1', user='root', password=AUTHENTICATION_PASSWORD, db='{}_{}'.format(market, time_frame), charset='utf8')

        try:
            curs = conn.cursor()
            query_text = 'SELECT * FROM {}'.format(table)
            curs.execute(query_text)
            self.rs = curs.fetchall()

        finally:
            conn.close()

        self.Strategy()


    def get_SMA(self, SMA_list, size):
        i = len(SMA_list)
        window = SMA_list[i-size:]

        return sum(window) / size


    def Strategy(self):
        start = False
        yesterday_price = 0
        SMA_3_list = []
        SMA_5_list = []
        SMA_10_list = []
        SMA_20_list = []
        SMA_3 = 0
        SMA_5 = 0
        SMA_10 = 0
        SMA_20 = 0

        for row in self.rs:
            curr_price = row[1]
            # row(1) is the closing price (가격)
            SMA_3_list.append(row[1])
            SMA_5_list.append(row[1])
            SMA_10_list.append(row[1])
            SMA_20_list.append(row[1])

            # Maintains list size according to SMA
            if len(SMA_3_list) > 3:
                del SMA_3_list[0]
            if len(SMA_5_list) > 5:
                del SMA_5_list[0]
            if len(SMA_10_list) > 10:
                del SMA_10_list[0]
            if len(SMA_20_list) > 20:
                del SMA_20_list[0]

            # Calculate SMAs
            if len(SMA_3_list) == 3:
                SMA_3 = self.get_SMA(SMA_20_list, 3)
            if len(SMA_5_list) == 5:
                SMA_5 = self.get_SMA(SMA_20_list, 5)
            if len(SMA_10_list) == 10:
                SMA_10 = self.get_SMA(SMA_20_list, 10)
            if len(SMA_20_list) == 20:
                SMA_20 = self.get_SMA(SMA_20_list, 20)

            if yesterday_price != 0:
                percentage_change = round((-1.0 + (row[1] / yesterday_price)), 2)

            # While stock is being held...
            if self.stock_held == True:
                # percentage_change is 등락률 or % change for the day
                self.stock_held_percentage += (percentage_change)
                # print("당일등락률: {}".format(percentage_change))
                # print("보유종목등락률: {}".format(self.stock_held_percentage))

            # Buy Condition
            if (SMA_3 != 0) and (self.stock_held == False) and (curr_price >= float(SMA_20)) and ((curr_price > float(SMA_3)) or (curr_price > float(SMA_5)) or (curr_price > float(SMA_10))):
                # if available cash is less than current price
                if self.available_capital < row[1]:
                    continue
                else:
                    self.stock_held = True
                    self.num_bought = int(self.available_capital // row[1]) # row[1] is price
                    self.amount_bought = round(self.num_bought * row[1])
                    self.available_capital -= round(self.amount_bought * (1.0 - self.commission_fee))
                    # print('--------------------')
                    # print('BOUGHT: {}'.format(row[0]))
                    # print("available_capital: {}".format(self.available_capital))
                    # print("num_bought: {}".format(self.num_bought))
                    # print("amount_bought: {}".format(self.amount_bought))

                    self.temp_buy_date = row[0]
                    self.temp_buy_date_price = row[1]

            # Sell Condition
            # if (self.stock_held == True) and ((curr_price <= float(SMA_3)) and (curr_price <= float(SMA_5)) and (curr_price <= float(SMA_10))):
            if (self.stock_held == True) and ((curr_price <= float(SMA_20))):

                self.stock_held = False

                gain = round(self.amount_bought * (1 + self.stock_held_percentage))
                self.available_capital += gain
                self.num_bought = 0
                self.amount_bought = 0.0
                # print('--------------------')
                # print('SOLD: {}'.format(row[0]))
                # print("available_capital: {}".format(self.available_capital))
                # print("stock_held_percentage: {}".format(self.stock_held_percentage))
                # print("gain: {}".format(gain))
                # print("num_bought: {}".format(self.num_bought))
                # print("amount_bought: {}".format(self.amount_bought))

                self.temp_sell_date = row[0]
                self.temp_sell_date_price = row[1]

                if self.stock_held_percentage > 0: # if profit increment number of wins
                    self.wins += 1
                elif self.stock_held_percentage < 0: # if loss increment number of losses
                    self.losses += 1
                else:
                    self.ties += 1

                tuple_val = (self.temp_buy_date, self.temp_buy_date_price, self.temp_sell_date, self.temp_sell_date_price, self.stock_held_percentage)
                self.trades.append(tuple_val)

                self.stock_held_percentage = 0.0

                self.cnt+=1

            yesterday_price = row[1]



        print('--------------------')
        print('FINAL: {}'.format(row[0]))
        gain = round(self.amount_bought * (1 + self.stock_held_percentage))
        self.available_capital += gain
        print("Total profit: {}".format(self.available_capital))
        print("stock_held_percentage: {}".format(self.stock_held_percentage))
        print("num_bought: {}".format(self.num_bought))
        # print("amount_bought: {}".format(self.amount_bought))
        print("Number of Trades: {}".format(self.cnt))
        print(reducefract(self.wins, self.losses))
        print(self.trades)

def reducefract(n, d):
    '''Reduces fractions. n is the numerator and d the denominator.'''
    def gcd(n, d):
        while d != 0:
            t = d
            d = n%d
            n = t
        return n
    assert d!=0, "integer division by zero"
    assert isinstance(d, int), "must be int"
    assert isinstance(n, int), "must be int"
    greatest=gcd(n,d)
    n/=greatest
    d/=greatest
    print('{}/{}'.format(n, d))
    return round((n/d),3)
