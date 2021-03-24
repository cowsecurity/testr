#!/usr/bin/python3 
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import db_utils
import subprocess
import hashlib

app = Flask(__name__)
app.secret_key = '42'

@app.route('/')
def index():
    if session.get('logged_in') != True:
        return redirect('login')
    else:
        return redirect('editor')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        sha256_password = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        params = (request.form['email'], sha256_password,)

        con = db_utils.db_con()
        cur = con.cursor()
        result = cur.execute('SELECT * FROM users WHERE email = ? AND password = ?', params)
        rows = result.fetchall()
        con.close()

        if len(rows) > 0:
            if rows[0][2] == 1:
                session['logged_in'] = True
                session['user'] = list(rows[0])
                return redirect('editor')
            else:
                flash("Account is awaiting approval.", 'error')
                return render_template('login.html')
        else:
            flash("Incorrect Username/Password.", 'error')
            return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out!", 'success')
    return redirect('login')

@app.route('/reset',methods=['POST'])
def reset():
    email = request.form['email']
    phrase = request.form['secret_phrase']
    password = request.form['password']
    password2 = request.form['password2']
    if email and phrase and password and password2:
        if password == password2:
            con = db_utils.db_con()
            cur = con.cursor()

            sha256_phrase = hashlib.sha256(phrase.encode('utf-8')).hexdigest()
            params = (email, sha256_phrase)
            result = cur.execute('SELECT * FROM users WHERE email = ? AND secret_phrase = ?', params)
            if len(result.fetchall()) > 0:
                sha256_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
                params = (sha256_password, email)

                cur.execute('UPDATE users SET password = ? WHERE email = ?', params)
                con.commit()
                con.close()

                flash("Password changed!", 'success')
                return redirect('/login')
            else:
                flash("Incorrect secret/email", 'error')
                return redirect('/login')
        else:
            flash("Passwords don't match.", 'error')
            return redirect('/login')
    else:
        flash("Please fill out all fields.", 'error')
        return redirect('/login')


@app.route('/apply',methods=['POST'])
def apply():
    name = request.form['name']
    email = request.form['email']
    phrase = request.form['secret_phrase']
    password = request.form['password']
    password2 = request.form['password2']

    if name and email and phrase and password and password2:
        if password == password2:
            con = db_utils.db_con()
            cur = con.cursor()
            params = (email,)
            result = cur.execute('SELECT * FROM users WHERE email = ?', params)
            if len(result.fetchall()) == 0:
                sha256_phrase = hashlib.sha256(phrase.encode('utf-8')).hexdigest()
                sha256_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
                params = (email, None, None, name, sha256_password, sha256_phrase)
                cur.execute('INSERT INTO users VALUES (?,?,?,?,?,?)', params)
                con.commit()
                con.close()
                flash("Application sent!",'success')
                return redirect('/login')
            else:
                con.close()
                flash("Email already taken",'error')
                return redirect('/login')
        else:
            con.close()
            flash("Passwords don't match.",'error')
            return redirect('/login')
    else:
        con.close()
        flash("Please fill out all fields.",'error')
        return redirect('/login')

@app.route('/api')
def api():
    return render_template('api.html')

@app.route('/update_details',methods=['POST'])
def update_details():
    if session.get('logged_in') != True:
        return redirect('login')
    else:
        name = request.form['name']
        params = (name,session['user'][0])
        con = db_utils.db_con()
        cur = con.cursor()
        cur.execute('UPDATE users SET name = ? WHERE email = ?', params)
        con.commit()
        con.close()
        session['user'][3] = name
        flash("Successfully updated details!",'success')
        return redirect('/editor')

@app.route('/change_password',methods=['POST'])
def change_password():
    if session.get('logged_in') != True:
        return redirect('login')
    else:
        phrase = request.form['secret_phrase']
        password = request.form['password']
        password2 =  request.form['password2']
        if phrase and password and password2:
            if password == password2:
                sha256_phrase = hashlib.sha256(phrase.encode('utf-8')).hexdigest()
                params = (session['user'][0], sha256_phrase)
                con = db_utils.db_con()
                cur = con.cursor()
                result = cur.execute('SELECT * FROM users WHERE email = ? AND secret_phrase = ?', params)
                if len(result.fetchall()) > 0:
                    sha256_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
                    params = (sha256_password,session['user'][0])
                    cur.execute('UPDATE users SET password = ? WHERE email = ?', params)
                    con.commit()
                    con.close()
                    flash("Successfully changed password!",'success')
                    return redirect('/editor')
                else:
                    flash("Secret phrase is incorrect.",'error')
                    return redirect('/editor')
            else:
                flash("Passwords don't match.",'error')
                return redirect('/editor')
        else:
            flash("Please fill out all fields",'error')
            return redirect('/editor')

@app.route('/change_secret_phrase',methods=['POST'])
def change_secret_phrase():
    if session.get('logged_in') != True:
        return redirect('login')
    else:
        phrase = request.form['secret_phrase']
        phrase2 = request.form['secret_phrase2']

        if phrase and phrase2:
            if phrase == phrase2:
                sha256_phrase = hashlib.sha256(phrase.encode('utf-8')).hexdigest()
                params = (sha256_phrase,session['user'][0])
                con = db_utils.db_con()
                cur = con.cursor()
                cur.execute('UPDATE users SET secret_phrase = ? WHERE email = ?', params)
                con.commit()
                con.close()
                flash("Successfully changed secret phrase!",'success')
                return redirect('/editor')
            else:
                flash("Secret phrases don't match.",'error')
                return redirect('/editor')
        else:
            flash("Please fill out all fields",'error')
            return redirect('/editor')

@app.route('/editor', methods=['GET','POST'])
def editor():
    if session.get('logged_in') != True:
        return redirect('login')
    else:
        if request.method == 'GET':
            return render_template('editor.html', code='', out='')

        elif request.method == 'POST':
            code = request.form['code']
            try:
                # TODO Filters, blacklist, regex, etc...
                output = subprocess.check_output(['python3','-c',code], stderr=subprocess.STDOUT)
                output = output.decode('utf-8')
            except subprocess.CalledProcessError as exc:
                return render_template('editor.html', code=code, out="%s"%exc.output.decode('utf-8'))
            else:
                return render_template('editor.html', code=code, out=output)

if __name__ == '__main__':
    db_utils.seed_db()
    app.run(host='0.0.0.0',port='5000')