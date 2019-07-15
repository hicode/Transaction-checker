# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 19:48:17 2019

@author: krzysztof.oporowski
"""

import quandl
import pickle
import pandas as pd
from datetime import date


def get_own_data(equity_name, quandl_API_token):
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
        quandl.ApiConfig.api_key = quandl_API_token
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
    cols = ['id', 'stocks_number', 'open_price', 'open_value', 
            'open_commission', 'open_total', 'close_price', 'close_value',
            'close_commission', 'close_total']
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
    #trans_number = 0
    
    def __init__(self, trans_numb, transaction_gl, comm=0.0039):
        '''
        Parameters:
        -----------
        comm - broker's commision. Default value for DM mBank
        transation_gl - list to store transactions
        
        '''
        self.stocks_number = 0 # number of stocks bought
        self.open_price = 0 # price for opening the transaction
        self.close_price = 0 # price for closing the transaction
        self.comm_rate = comm # broker's commision
        self.open_value = 0 # worth of transaction without commission
        self.close_value = 0 
        self.comm_open_value = 0 # commision for opening the transaction
        self.comm_close_value = 0 # commision for closing the transaction
        self.open_total = 0 # total value of the stocks price + commision
        self.close_total = 0
        self.trans_id = trans_numb # ID of the transaction
        # self.trans_number = self.trans_number + 1 # ID for next transaction
        self.in_transaction = False # transaction indicator
        self.gl = transaction_gl
    
    def open_transaction(self, number, price):
        '''
        Method to buy stocks.
        Parameters:
        -----------
        numb      - number of stocks bought in single transaction
        buy_price - stock's buy price
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
        
    def close_transaction(self, price):
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
            self.in_transaction = False
            self.register_transaction()
            
    def register_transaction(self):
        print('''
              Transakcja numer: {}, ilosc: {}, cena otwarcia {},
              wartosc otwarcia: {}, prowizja otwarcia: {}, koszt otwarcia {},
              cena zamkn: {}, wartosc zamkn: {}, prowizja zamkn: {}, 
              koszt_zamkn: {}
              '''.format(self.trans_id, self.stocks_number,
                         self.open_price, self.open_value, 
                         self.comm_open_value, self.open_total,
                         self.close_price, self.close_value, 
                         self.comm_close_value, self.close_total
                         )
              )
        '''
        row = {'id':self.trans_id, 
               'stocks_number':self.stocks_number,
               'open_price':self.open_price, 
               'open_value':self.open_value, 
               'open_commission':self.comm_open_value, 
               'open_total':self.open_total,
               'close_price':self.close_price, 
               'close_value':self.close_value, 
               'close_commission':self.comm_close_value, 
               'close_total':self.close_total
               }
        self.gl = self.gl.append(row, ignore_index=True)
        
        #= df.append(row, ignore_index=True)
        '''
        row = [
               self.trans_id, self.stocks_number, self.open_price, 
               self.open_value, self.comm_open_value, self.open_total,
               self.close_price, self.close_value, self.comm_close_value, 
               self.close_total
               ]
        self.gl.append(row)


# test of Budget and Transactions working
budzet = Budget()
gl = []
for i in range(0,3):
    trans = Transaction(i, gl)
    trans.open_transaction(5, 127) # pretending to buy 5 stocks per 127
    budzet.manage_amount(-trans.open_total)
    print('moj budzet to: {}'.format(budzet.equity))
    trans.close_transaction(125) # pretending to sell 5 stocks per 125
    budzet.manage_amount(trans.close_total)
    print('moj budzet to: {}'.format(budzet.equity))
transactions = define_gl(gl)
print(transactions)

# test of get_own_data working
data = get_own_data('Amica', '8zKzKFh-8eePuNy9wpuP')  # , 'Pekao'
data['fast_ma'] = data['close'].rolling(10).mean()
data['slow_ma'] = data['close'].rolling(30).mean()
data['close'].loc['2019-01-03':].plot()
data['fast_ma'].loc['2019-01-03':].plot()
data['slow_ma'].loc['2019-01-03':].plot()

