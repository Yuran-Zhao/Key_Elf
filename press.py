# -*- coding: utf-8 -*
import sqlite3
from flask import Flask, request, render_template, jsonify, redirect
import datetime

flaskapp = Flask(__name__)
# use `app` instead in this file
app = flaskapp

""" configure used to test """
app.config.update(dict(
    DATABASE='./press.db',
    DEBUG=True,
))


"""
# initial the database used to test
"""
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

"""
# connect to database `count.db`
# this database will be created in the current file
"""
def get_db():
    """
    Connect to the test database
    db = sqlite3.connect('./press.db')
    """
    db = sqlite3.connect('./count.db')

    # so can use name to manipulate the results returned
    db.row_factory = sqlite3.Row
    return db


"""
# flag `one`: return one result or all of them
"""
def query_db(query, args=(), one=False):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    result = cur.fetchall()
    db.close()
    return (result[0] if result else None) if one else result


# in case that user visit 127.0.0.1:5000
@app.route('/', methods=['GET'])
def redirect_to_entrance():
    return redirect('/entrance')


# entrance of the report
@app.route('/entrance', methods=['GET'])
def get_entrance():
    return render_template('entrance.html')


# haven't pressed any key
@app.route('/no_data', methods=['GET'])
def find_no_data():
    return render_template('no_data.html')


# statistic data mainly revealed in this page
@app.route('/main_report', methods=['GET'])
def get_main_report():
    try:
        # the date and hour that the first record was inserted
        begin_date = query_db('SELECT P_DATE, HOUR FROM DAY_HOUR ORDER BY P_DATE asc, HOUR asc', (), True)
        # record current date and hour
        cur_date = int(datetime.date.today().strftime('%y%m%d'))
        cur_hour = int(datetime.datetime.now().hour)
        # calculate the total hour that software has run
        total_hour = 24 - begin_date['HOUR'] + (cur_date - begin_date['P_DATE'] - 1) * 24 + cur_hour + 1

        # the total of pressing
        number = query_db('SELECT SUM(COUNTS) AS TOTAL_SUM FROM KEY_COUNT', (), True)['TOTAL_SUM']

        # the most frequently pressed key
        love_key = query_db("SELECT KEY_NAME FROM KEY_COUNT order by COUNTS desc", (), True)['KEY_NAME']

        # frequent_hour_begin -- frequent_hour_end
        # the period of the most frequently pressing
        frequent_hour_begin = int(query_db('SELECT HOUR FROM (SELECT SUM(COUNTS) as s, HOUR FROM DAY_HOUR GROUP BY HOUR) order by s desc', (), True)['HOUR'])
        frequent_hour_end = frequent_hour_begin + 1
        return render_template('main_report.html', time=str(total_hour), num=str(number), key=str(love_key), period_begin=str(frequent_hour_begin), period_end=str(frequent_hour_end))
    except:
        return redirect('/no_data')


# get the data to draw the histogram
@app.route('/hours_pic', methods=['GET'])
def get_hours_pic():
    if request.method == 'GET':
        # record the counts in every hour
        hour_counts = []
        hours = []
        for i in range(0, 24):
            hour_counts.append(query_db("SELECT SUM(COUNTS) AS HOUR_SUM FROM DAY_HOUR WHERE HOUR=?", (str(i),), True)['HOUR_SUM'])
            hours.append(str(i) + ':00')
        return jsonify(
            hours=hours,
            counts=hour_counts
        )


# reveal the TOP 10 mostly pressed key
@app.route('/top_10', methods=['GET'])
def get_top_10():
    return render_template('top_10.html')


# get the data to draw the pie chart
@app.route('/top_10_pic', methods=['GET'])
def get_top_10_pic():
    if request.method == 'GET':
        # get the top 10 pressed key
        key_list = query_db('select * from KEY_COUNT order by COUNTS desc LIMIT 10')
        # total of the pressing
        total_num = query_db('SELECT SUM(COUNTS) AS TOTAL_SUM FROM KEY_COUNT', (), True)['TOTAL_SUM']

        # transfer the key to uppercase letter
        key_name = [x['KEY_NAME'] for x in key_list]
        key_count = [x['COUNTS'] for x in key_list]

        # record the total of TOP 10 pressed key
        top10_num = 0
        for i in range(0, len(key_count)):
            top10_num += key_count[i]

        # calculate the pressing counts of other keys
        other_num = total_num - top10_num
        key_name.append('Others')
        key_count.append(other_num)
        return jsonify(
            key=key_name,
            count=key_count
        )


# reveal the Day_report
@app.route('/day_report', methods=['GET'])
def get_day_report():
    if request.method == 'GET':
        return render_template('day_report.html')


# get the data to draw the line chart
@app.route('/day_report_pic', methods=['GET'])
def get_day_report_pic():
    if request.method == 'GET':
        # get the date and its total of press
        res_list = query_db('SELECT P_DATE, SUM(COUNTS) AS DAY_SUM FROM DAY_HOUR GROUP BY P_DATE ORDER BY P_DATE')
        # just transfer the form of date to `xx.xx.xx`
        day_list = [str(x['P_DATE'])[0:2] + '.' + str(x['P_DATE'])[2:4] + '.' + str(x['P_DATE'])[4:] for x in res_list]
        count_list = [x['DAY_SUM'] for x in res_list]
        return jsonify(
            date=day_list,
            counts=count_list
        )


# if the user haven't had input after 0:00 ever
@app.route('/no_night_data', methods=['GET'])
def if_no_night_data():
    return render_template('no_night_data.html')


# assume that normal users will not press the key before 6:00
# if they don't stay up late
# reveal the sum of days that have input between 0:00 and 6:00
@app.route('/night_report', methods=['GET'])
def night_num():
    if request.method == 'GET':
        try:
            # get the total of days that have input between 0:00 and 6:00
            day_num = query_db('SELECT COUNT(*) AS NIGHT_NUM FROM (SELECT * FROM DAY_HOUR WHERE HOUR>=0 AND HOUR<=6 GROUP BY P_DATE HAVING SUM(COUNTS)>0)', (), True)['NIGHT_NUM']
            # get the earliest time that pressing ever occurs
            earliest = query_db('SELECT P_DATE, HOUR FROM (SELECT * FROM DAY_HOUR WHERE HOUR>=0 AND HOUR<=6 GROUP BY P_DATE, HOUR HAVING SUM(COUNTS)>0) ORDER BY P_DATE asc, HOUR desc', (), True)

            # transfer the form of date to 20xx.xx.xx
            # assume that this software is mainly used in 21 century
            press_date = str(20) + str(earliest['P_DATE'])[0:2] + '.' + str(earliest['P_DATE'])[2:4] + '.' + str(earliest['P_DATE'])[4:]
            # TODO: this time is not accurate
            # transfer the form of hour to xx:00
            press_time = str(earliest['HOUR']) + ':00'
            return render_template('night_report.html', date=press_date, time=press_time, num=day_num)

        # if query returns error
        except:
            return redirect('./no_night_data')  # render_template('night_error.html')


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


# shutdown the server
@app.route('/shutdown', methods=['GET'])
def shutdown():
    shutdown_server()
    return 'Server is shutting down...'


# the test data of KEY_COUNT
def init_key_count():
    db = get_db()
    keys = [('BACKSPACE', 1123),
            ('ENTER', 234),
            ('w', 1255),
            ('E', 1935,),
            ('N', 1875),
            ('O', 1245),
            ('R', 993),
            ('Q', 773),
            ('M', 908),
            ('U',90),
            ('T', 128)
            ]
    db.executemany('INSERT INTO KEY_COUNT VALUES (?, ?)', keys)
    db.commit()
    db.close()


"""
# the test data of DAY_HOUR
"""
def init_day_hour():
    db = get_db()
    days_hours = [(190401, 0, 0),
            (190401, 1, 0),
            (190401, 2, 0),
            (190401, 3, 0),
            (190401, 4, 0),
            (190401, 5, 0),
            (190401, 6, 0),
            (190401, 7, 123),
            (190401, 8, 980),
            (190401, 9, 800),
            (190401, 10, 773),
            (190401, 11, 630),
            (190401, 12, 60),
            (190401, 13, 30),
            (190401, 14, 703),
            (190401, 15, 515),
            (190401, 16, 245),
            (190401, 17, 983),
            (190401, 18, 75),
            (190401, 19, 415),
            (190401, 20, 173),
            (190401, 21, 555),
            (190401, 22, 455),
            (190401, 23, 125),
            (190402, 0, 0),
            (190402, 1, 0),
            (190402, 2, 0),
            (190402, 3, 0),
            (190402, 4, 0),
            (190402, 5, 0),
            (190402, 6, 0),
            (190402, 7, 23),
            (190402, 8, 80),
            (190402, 9, 430),
            (190402, 10, 153),
            (190402, 11, 60),
            (190402, 12, 10),
            (190402, 13, 5),
            (190402, 14, 223),
            (190402, 15, 157),
            (190402, 16, 245),
            (190402, 17, 123),
            (190402, 18, 75),
            (190402, 19, 115),
            (190402, 20, 173),
            (190402, 21, 255),
            (190402, 22, 275),
            (190402, 23, 135),
            (190403, 0, 0),
            (190403, 1, 0),
            (190403, 2, 0),
            (190403, 3, 0),
            (190403, 4, 0),
            (190403, 5, 0),
            (190403, 6, 0),
            (190403, 7, 123),
            (190403, 8, 230),
            (190403, 9, 75),
            (190403, 10, 133),
            (190403, 11, 68),
            (190403, 12, 76),
            (190403, 13, 53),
            (190403, 14, 163),
            (190403, 15, 175),
            (190403, 16, 257),
            (190403, 17, 289),
            (190403, 18, 44),
            (190403, 19, 100),
            (190403, 20, 153),
            (190403, 21, 212),
            (190403, 22, 298),
            (190403, 23, 25),
            ]
    db.executemany('INSERT INTO DAY_HOUR VALUES (?, ?, ?)', days_hours)
    db.commit()
    db.close()


if __name__ == '__main__':
    # init_db()
    # init_key_count()
    # init_day_hour()
    app.run()
