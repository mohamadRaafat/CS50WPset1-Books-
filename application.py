import os

from flask import Flask, session, render_template, flash, request, abort, redirect, url_for
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
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

loggedIn = False


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
    return render_template("home.html")


# @app.route("/welcome")
# def welcome():
#     if loggedIn == False:
#         flash("you must login to proceed")
#         return redirect(url_for("index"))
#     return render_template("welcome.html")


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

        return redirect(url_for("index"))
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
                flash("Logged in successfuly")
                flash(f"Welcome {session['user']}")
                return redirect(url_for("index"))
            else:
                session["bad_alert"] = True
                flash("Username or password aren't correct")
                return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    global loggedIn
    if loggedIn == False:
        session["bad_alert"] = True
        flash("you must login to proceed")
    else:
        loggedIn = False
        session["user"] = None
        session["bad_alert"] = False
        flash("You logged out")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)

