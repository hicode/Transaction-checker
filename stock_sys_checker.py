# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 19:48:17 2019

@author: krzysztof.oporowski
"""

import pickle
import numbers
from datetime import date
import quandl
import pandas as pd
import matplotlib.pyplot as plt


def get_own_data(equity_name, quandl_api_token):
    '''
    Function read data of the signle quity using the Quandl. It requires the
    Quandl API to be provided, to make sure that more than 50 queries are
    allowed. Function returns the Pandas Panel data structure.
    Parameters:
    -----------
    equity_names:     String, used for polish stocks. On the Quandl
                      platform polish stocks are listed under the 'WSE/'
                      subfolder (Warsaw Stock Exchnage). Equity_names needs to
                      be the list of strings without the 'WSE/' (which is added
                      by the function).
    quandl_API_token: string, representing the Quandl API token. For more
                      details refer to the http://quandl.com
    Returns:
    --------
    currently Pandas DataFrame with one entitie's data
    '''
    todays_date = str(date.today())
    file_name = 'Data/' + equity_name + '-' + todays_date + '.pickle'
    try:
        with open(file_name, 'rb') as opened_file:
            data = pickle.load(opened_file)
        print('data from file {} used'.format(opened_file))
    except:
        quandl.ApiConfig.api_key = quandl_api_token
        # for equity_name in equity_names:
        quandl_query = 'WSE/' + equity_name
        data = quandl.get(quandl_query)
        data.drop(
                  ['%Change', '# of Trades', 'Turnover (1000)'],
                  axis=1, inplace=True
                 )
        data.columns = ['open', 'high', 'low', 'close', 'volume']
        data.index.names = ['date']
        # data = data[equity_name].resample('1d').mean()
        data.fillna(method='ffill', inplace=True)
        print('Data for {} collected'.format(quandl_query))
        # save data to avoid downloading again today
        with open(file_name, 'wb') as opened_file:
            pickle.dump(data, opened_file)
        print('Data from Quandl downloaded')
    return data


def define_gl(gl):
    '''
    Function returns Pandas dataframe where all transactions are stored
    '''
    cols = ['id', 'open_date', 'stocks_number', 'open_price', 'open_value',
            'open_commission', 'open_total', 'SL_date', 'SL', 'close_date',
            'close_price', 'close_value', 'close_commission', 'close_total',
            'trans_result']
    transactions = pd.DataFrame(gl, columns=cols)
    return transactions

class Budget:
    '''
    Class used to store data with regard to the money avaialbe for trading
    as well as some methods to manage the free_margin
    '''
    def __init__(self, amount=1000):
        '''
        Parameters:
        ----------
        equity - to store the budget based on closed transactions
        '''
        self.equity = amount
        self.free_margin = amount

    def manage_amount(self, change_amount):
        '''
        Method used to manage the equity changes as new transactions appears.
        The idea is to deal as follows:
            negative change_amount - transaction is opened and consumes equity
            positivit change_amount - transaction was closed and returns the
                                      equity
        '''
        self.equity = self.equity + change_amount

class Transaction:
    '''
    Class used to store transaction data and provide methods to manage all
    transactions
    '''

    def __init__(self, trans_numb, transaction_gl, comm=0.0039):
        '''
        Parameters:
        -----------
        comm - broker's commision. Default value for DM mBank
        trans_numb - externally provided transaction ID
        transation_gl - list to store transactions
        '''
        # pylint: disable=too-many-instance-attributes

        self.stocks_number = 0 # number of stocks bought
        self.open_price = 0 # price for opening the transaction
        self.open_date = '' # stores the open date of transaction
        self.close_price = 0 # price for closing the transaction
        self.close_date = '' # stores the close date
        self.comm_rate = comm # broker's commision
        self.open_value = 0 # worth of transaction without commission
        self.close_value = 0
        self.comm_open_value = 0 # commision for opening the transaction
        self.comm_close_value = 0 # commision for closing the transaction
        self.open_total = 0 # total value of the stocks price + commision
        self.close_total = 0
        self.trans_result = 0
        self.SL = 0 # if below this value, stocks are sold Stop Loss
        self.stop_loss_date = '' # stores the stop loss date
        self.trans_id = trans_numb # ID of the transaction
        # self.trans_number = self.trans_number + 1 # ID for next transaction
        self.in_transaction = False # transaction indicator
        self.gl = transaction_gl

    def how_many_stocks(self, price, budget):
        '''
        Function returns how many stocks you can buy
        '''
        number = int((budget - budget * self.comm_rate) / price)
        return number
    
    def open_transaction(self, number, price, date):
        '''
        Method to buy stocks.
        Parameters:
        -----------
        numb      - number of stocks bought in single transaction
        buy_price - stock's buy price
        date      - date and time of open
        '''
        if not self.in_transaction:
            self.stocks_number = number
            self.open_price = price
            self.open_value = self.stocks_number * self.open_price
            self.comm_open_value = self.open_value * self.comm_rate
            if self.comm_open_value < 3:
                self.comm_open_value = 3
            self.open_total = self.open_value + self.comm_open_value
            self.in_transaction = True
            self.open_date = date
            self.register_transaction()

    def set_sl(self, sl_type, sl_factor, price, date):
        '''
        Functions sets the SL on the price.
        Parameters:
        -----------
        sl_type   - string, 2 possibilities
                      - atr - stop loss based on ATR calculations
                      - percent - stop loss based on the percentage slippage
        sl_factor - float, if sl_type = 'atr', than is the ATR value,
                    if sl_type = 'percent' it is just the value of the
                    percent, between 0 and 100
        price     - current price
        date      - date time of SL
        '''
        if sl_type not in ['atr', 'percent']:
            print('Value {} of sl_type is not appropriate. Use "atr" or \
                  "percent" only. Setting SL to 0'.format(sl_type))
            self.SL = 0
        elif not isinstance(sl_factor, numbers.Number):
            print('number of type int or float is expected, not {}'.
                  format(type(sl_factor)))
        else:
            if sl_type == 'atr':
                pass
            else:
                if sl_factor < 0 or sl_factor > 100:
                    print('sl_factor in percent mode must be 0 -100 value. \
                          Setting SL to 0 PLN.')
                    self.SL = 0
                else:
                    new_sl = price - price * (sl_factor / 100)
                    if new_sl > self.SL:
                        self.SL = new_sl
                        #print('SL set to {}'.format(self.SL))
                        self.stop_loss_date = date
                        self.register_transaction()

    def close_transaction(self, price, date):
        '''
        Method to close the transaction
        '''
        if self.in_transaction:
            self.close_price = price
            self.close_value = self.close_price * self.stocks_number
            self.comm_close_value = self.close_value * self.comm_rate
            if self.comm_close_value < 3:
                self.comm_close_value = 3
            self.close_total = self.close_value - self.comm_close_value
            self.trans_result = self.close_total - self.open_total
            self.close_date = date
            self.register_transaction()
            #self.reset_values()

    def reset_values(self):
        '''
        Function resets all values after the transaction is closed
        '''
        self.stocks_number = 0
        self.open_price = 0
        self.open_date = ''
        self.close_price = 0
        self.close_date = ''
        self.open_value = 0
        self.close_value = 0
        self.comm_open_value = 0
        self.comm_close_value = 0
        self.open_total = 0
        self.close_total = 0
        self.trans_result = 0
        self.SL = 0
        self.stop_loss_date = ''
        self.in_transaction = False
        self.trans_id = self.trans_id + 1

    def register_transaction(self):
        '''
        Function registers the transaction details in the general ledger.
        '''
        print('''
              Transakcja numer: {}, data otwarcia: {} ilosc akcji: {},
              cena otwarcia {}, wartosc otwarcia: {}, prowizja otwarcia: {},
              koszt otwarcia {}, data stopa: {}, SL: {}, data zamknięcia: {},
              cena zamkn: {}, wartosc zamkn: {}, prowizja zamkn: {}, 
              koszt_zamkn: {}
              '''.format(self.trans_id, self.open_date, self.stocks_number,
                         self.open_price, self.open_value, 
                         self.comm_open_value, self.open_total,
                         self.stop_loss_date, self.SL,
                         self.close_date, self.close_price, self.close_value,
                         self.comm_close_value, self.close_total
                         )
              )
        row = [
               self.trans_id, self.open_date, self.stocks_number, 
               self.open_price, self.open_value, self.comm_open_value,
               self.open_total, self.stop_loss_date, self.SL,
               self.close_date, self.close_price, self.close_value,
               self.comm_close_value, self.close_total, self.trans_result
               ]
        self.gl.append(row)

def get_date_only(row):
    '''
    To process index date/time value from Quandl to get date only
    '''
    date_time = row.name
    date_time = pd.to_datetime(date_time)
    date_only = date_time.date()
    return date_only

def process_data(row):
    '''
    Define algo to be applied to the DataFrame
    '''
    global BUDZET
    global GL
    global trans_id
    global trans
    global count
    
    if not trans.in_transaction:
        if row['fast_ma'] > row['slow_ma']:
            #trans.in_transaction = True
            if row['open'] != 0:
                if BUDZET.equity > 3:
                    stock_number = trans.how_many_stocks(row['open'],
                                                         BUDZET.equity)
                    if stock_number > 0:
                        trans.open_transaction(stock_number, row['open'],
                                               date=get_date_only(row))
                        BUDZET.manage_amount(-trans.open_total)
                        trans.set_sl(sl_type='percent', sl_factor=10,
                                     price=row['open'], date=get_date_only(row))
                        '''
                        trans_date = get_date_only(row)
                        print(
                                '{}: fast_ma={}, slow_ma={}'.format(
                                        trans_date, row['fast_ma'], row['slow_ma']
                                        )
                              )
                        print(trans_id)
                        '''
                        trans_id = trans_id + 1
                else:
                    print('kupiłbym ale pieniadze sie skonczyły')
    else:
        #print('in transaction')
        if row['fast_ma'] < row['slow_ma']:
            '''print('fast_ma {} lower than slow_ma {}, closing'.format(
                    row['fast_ma'], row['slow_ma']))'''
        if trans.SL > row['low']:
            '''print('price {} lower than sl {}, closing'.format(
                    row['low'], trans.SL))'''
            trans.close_transaction(price=trans.SL, date=get_date_only(row))
            BUDZET.manage_amount(trans.close_total)
            trans.reset_values()
            print('budzet po zamknieciu transakcji: {}'.format(BUDZET.equity))
        else:
            #print('checking if rise sl')
            trans.set_sl(sl_type='percent', sl_factor=10,
                         price=row['close'], date=get_date_only(row))
    

# test of Budget and Transactions working
BUDZET = Budget()
GL = []
trans_id = 0
count = 0
trans = Transaction(trans_id, GL)
'''
for i in range(0, 3):
    trans = Transaction(i, GL)

    trans.open_transaction(5, 127) # pretending to buy 5 stocks per 127
    if i == 0:
        trans.set_sl(sl_type='percent', sl_factor=10, price=trans.open_price)
    BUDZET.manage_amount(-trans.open_total)
    print('moj BUDZET to: {}'.format(BUDZET.equity))
    trans.close_transaction(125) # pretending to sell 5 stocks per 125
    BUDZET.manage_amount(trans.close_total)
    print('moj budzet to: {}'.format(BUDZET.equity))
TRANSACTIONS = define_gl(GL)
print(TRANSACTIONS)
'''
# test of get_own_data working
DATA = get_own_data('Amica', '8zKzKFh-8eePuNy9wpuP')  # , 'Pekao'
DATA['fast_ma'] = DATA['close'].rolling(10).mean()
DATA['slow_ma'] = DATA['close'].rolling(30).mean()
DATA.dropna()


# apply algo to the stock (DataFrame)
DATA.apply(process_data, axis=1)

transactions = define_gl(GL)
print('wynik zabaway: {}'.format(transactions['trans_result'].sum()))
#print('trans_id = {}'.format(trans_id))
#DATA['close'].loc['2019-01-03':].plot()
#DATA['fast_ma'].loc['2019-01-03':].plot()
#DATA['slow_ma'].loc['2019-01-03':].plot()
#plt.show()
