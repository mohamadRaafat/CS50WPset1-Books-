import os
import requests
import time

from difflib import get_close_matches
from flask import Flask, session, render_template, flash, request, redirect, url_for, jsonify
from flask_session import Session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash

# haget el db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


# getting the databse url from the env variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# getting the secret key from the env variable
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")

app = Flask(__name__)

# Configure session to use filesystem
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

loggedIn = False

# storing all the book data
all_books = list(db.execute("SELECT * FROM books"))
books_isbns = []
books_titles = []
books_authors = []
for book in all_books:
    books_isbns.append(book[0])
    books_titles.append(book[1])
    books_authors.append(book[2])

# fetching the book data from goodreads api
def api_fetch_book(isbn):
    try:
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                            params={"key": "6a1AQly86mn3u4gLvajIuw", "isbns": isbn})
        data = res.json()
        data = data["books"][0]
    except:
        data = []
    
    return data

############################## FORM MODELS ##########################################

# Register form
class RegistrationForm(FlaskForm):
    username = StringField("Please enter your name",
                           validators=[DataRequired()])
    password = PasswordField("Please enter your password", validators=[DataRequired()])
    pass_confirm = PasswordField(
        "Confirm your password", validators=[DataRequired()])
    register = SubmitField("Register")


# Login Form
class LoginForm(FlaskForm):
    username = StringField("Please enter your username",
                           validators=[DataRequired()])
    password = PasswordField(
        "Please enter your password", validators=[DataRequired()])
    login = SubmitField("Login")

#####################################################################################


@app.route("/")
def index():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if not form.password.data == form.pass_confirm.data:
            session["bad_alert"] = True
            flash("Passwords do not match!")
            return redirect(url_for("register"))
        # Grab data
        username = form.username.data
        password = form.password.data
        password_hash = generate_password_hash(password)
        # check if the name is already taken
        check = db.execute("SELECT username FROM users WHERE username =:username",
                             {"username": username}).rowcount
        if check != 0:
            session["bad_alert"] = True
            flash("This username is already taken, please choose another one")
            return redirect(url_for("register"))
        # Add user to the db
        new_user = db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {
                              "username": username, "password": password_hash})
        db.commit()
        # logging in the user
        session["bad_alert"] = False
        flash(f"Welcome {username}! Thanks for registering")
        session["user"] = username
        global loggedIn
        loggedIn = True
        return redirect(url_for("search"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = db.execute("SELECT username, password FROM users WHERE username =:username;", {
                          "username": username}).fetchone()
        if not user:
            session["bad_alert"] = True
            flash("No user exists with such username")
            return redirect(url_for("login"))
        else:
            if check_password_hash(user[1], password):
                session["user"] = user[0]
                global loggedIn
                loggedIn = True
                session["bad_alert"] = False
                flash(f"Welcome {session['user']}")
                return redirect(url_for("search"))
            else:
                session["bad_alert"] = True
                flash("Username or password aren't correct")
                return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    # make sure the user is logged in
    if loggedIn == False or session["user"] == None:
        session["bad_alert"] = True
        flash("You must login to proceed")
        return redirect(url_for("login"))

    loggedIn = False
    session["user"] = None
    session["bad_alert"] = False
    flash("You logged out")
    return redirect(url_for("login"))

@app.route("/profile")
def profile():
    # make sure the user is logged in
    if loggedIn == False or session["user"] == None:
        session["bad_alert"] = True
        flash("You must login to proceed")
        return redirect(url_for("login"))

    number_of_reviews = db.execute("SELECT count(reviews.review) FROM reviews, users WHERE users.id = reviews.user_id AND username= :username",
                                    {"username": session["user"]}).fetchone()[0]
    return render_template("profile.html", number_of_reviews=number_of_reviews)


@app.route("/search")
def search():
    # make sure the user is logged in
    if loggedIn == False or session["user"] == None:
        session["bad_alert"] = True
        flash("You must login to proceed")
        return redirect(url_for("login"))

    if request.args.get("search"):
        # retrieving search input
        search = request.args.get("search")

        # capitalize the first letter in each word
        search = search.split(" ")
        new_search = []
        for word in search:
            new_search.append(word.capitalize())
        search = " ".join(new_search)
        # remove any extra spaces if any "zy   dah      keda :D"
        search = " ".join(search.split())

        matches = []

        def get_index_matches_then_append(where_to_search):
            mts = get_close_matches(search, where_to_search)
            for m in mts:
                # getting the index of the 'matche' book
                index = where_to_search.index(m)
                # appending the book to the matches list using this indes :D
                matches.append(all_books[index])


        # getting closest matches to the search string
        if get_close_matches(search, books_isbns):
            get_index_matches_then_append(books_isbns)
        if get_close_matches(search, books_titles):
           get_index_matches_then_append(books_titles)
        if get_close_matches(search, books_authors):
            get_index_matches_then_append(books_authors)

        # getting all matches from a substr
        for book in all_books:
            if search in book[0]:
                matches.append(book)
            if search in book[1]:
                matches.append(book)
            if search in book[2]:
                matches.append(book)

        # awel item beteb2a list fa bafokaha
        if matches:
            if type(matches[0]) == list:
                matches.extend(matches[0])
                matches[0] = []
                matches = [match for match in matches if match != []]

        # remove duplicates from the list, my solution :D
        items = []
        for match in matches:
            if match in items:
                continue
            else:
                items.append(match)
        matches = items

        # limiting the results to 50 per page    
        if len(matches) > 50:
            matches = matches[:50]

        if not matches :
            session["bad_alert"] = True
            flash("No matches found! Try again...")
        return render_template("search.html", books=matches, books_titles=books_titles, books_authors=books_authors)
    return render_template("search.html",  books_titles=books_titles, books_authors=books_authors)

@app.route("/search/<string:isbn>", methods=["GET", "POST"])
def book_page(isbn):
    # make sure the user is logged in
    if loggedIn == False or session["user"] == None:
        session["bad_alert"] = True
        flash("You must login to proceed")
        return redirect(url_for("login"))

    data = api_fetch_book(isbn)

    # fetching the book from the db
    book = db.execute(
        "SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if not book:
        flash("No book found!")
        return redirect(url_for('search'))

    # fetching the id of the logged in user
    user_id = db.execute("SELECT id FROM users WHERE username = :username",
                         {"username": session["user"]}).fetchone()[0]
    book_isbn = isbn

    if request.method == "GET":
        if loggedIn == False or session["user"] == None:
            session["bad_alert"] = True
            flash("You must login to proceed")
            return redirect(url_for("login"))

        # making sure this user have no recent reviews for this specific book
        if db.execute("SELECT user_id, book_isbn FROM reviews WHERE user_id = :user_id AND book_isbn = :book_isbn",
                  {"user_id": user_id, "book_isbn": book_isbn}).rowcount == 0:
            no_previous_reviews = True
        else:
            no_previous_reviews = False 

        # fetching all reviews for this specific book
        all_reviews = db.execute("SELECT users.username, reviews.review, reviews.stars, reviews.date FROM reviews, users WHERE users.id=reviews.user_id AND book_isbn= :book_isbn",
                                    {"book_isbn": book_isbn}).fetchall()
        return render_template("book.html", book=book, data=data, no_previous_reviews=no_previous_reviews, all_reviews=all_reviews)

    else:
        review = request.form.get("review")
        stars = request.form.get("rating")
        date = time.strftime("%d/%m/%Y")
        db.execute("INSERT INTO reviews (user_id, book_isbn, review, stars, date) VALUES (:user_id, :book_isbn, :review, :stars, :date)",
                                {"user_id": user_id, "book_isbn": book_isbn, "review": review, "stars": stars, "date": date})
        db.commit()
        return redirect(f"/search/{book_isbn}")


@app.route("/api/<string:isbn>")
def api(isbn):
    book = db.execute("SELECT title, author, year, isbn FROM books WHERE isbn = :isbn", 
                        {"isbn": isbn}).fetchone()
    if not book:
        return  jsonify({
            "error": 404
        })
        
    data = api_fetch_book(isbn)
    return jsonify({
        "title": book[0],
        "author": book[1],
        "year": book[2],
        "isbn": book[3],
        "review_count": data["reviews_count"],
        "average_score": data["average_rating"]
    })


@app.errorhandler(404)
def error(err):
    return render_template("errors.html", err=err)


if __name__ == "__main__":
    app.run(debug=True)

