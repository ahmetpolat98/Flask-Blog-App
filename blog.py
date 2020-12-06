from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, BooleanField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import datetime



app = Flask(__name__)

app.secret_key = "polatblog"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////...../blog.db'

db = SQLAlchemy(app)


#Login control decorator / loginrequired / check login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("You must be login to view this page.", "warning")
            return redirect(url_for("login"))

    return decorated_function



#########
# Database classes
#########

#articles database class
class blogPost(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(50))
    subtitle = db.Column(db.String(50))
    author = db.Column(db.String(30))
    username = db.Column(db.String(80))
    date_posted = db.Column(db.DateTime)
    content = db.Column(db.Text)

#users database
class Users(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(80))
    password = db.Column(db.String(80))


##########
#   FORMS
##########

#register form
class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(min=3, max=25)])
    email = StringField('Email Address', [validators.Length(min=6, max=35)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')
    accept_tos = BooleanField("I'm not robot", [validators.DataRequired()])

#login form
class LoginForm(Form):
    username = StringField('Username')
    password = PasswordField('Password')

#add article form
class addArticleForm(Form):
    title = StringField("Title", [validators.Length(min = 3, max = 100)])
    subtitle = StringField("Subtitle", [validators.Length(min = 3, max = 100)])
    author = StringField("Author", [validators.Length(min = 3, max = 100)])
    content = TextAreaField("Blog content", [validators.Length(min = 10)])


#############

#index-home page  / show all posts
@app.route("/")
def index():
    posts = blogPost.query.all()
    if posts != 0:
        return render_template("index.html", posts = posts)
    
    return render_template("index.html")


#register
@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegistrationForm(request.form)
    
    if request.method == 'POST' and form.validate():
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        existing_user = Users.query.filter_by(username = username).first()
        #check user is created before?
        if existing_user is None:
            #user create and save db
            user = Users(username = username, email = email, password = password)
            db.session.add(user)
            db.session.commit()
        
            flash("Thanks for registering", "success")
            return redirect(url_for('index'))

        flash("This username is already registered", "danger")

    return render_template("register.html", form = form)


#login
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data

        user = Users.query.filter_by(username = username).first()
        if user and sha256_crypt.verify(password, user.password):
            #bilgileri kaydet
            session["logged_in"] = True
            session["username"] = user.username
            session["email"] = user.email
            ###
            
            flash_string = "Welcome " + user.username
            flash(flash_string, "success")
            return redirect(url_for("index"))
       
        flash("Username or password is wrong", "danger")
        #return redirect(url_for("login"))
    
    return render_template("login.html", form = form)


#logout
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logout success","info")
    return redirect(url_for("index"))


#dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    posts = blogPost.query.filter_by(username = session["username"]).all()
    return render_template("dashboard.html", posts = posts)


#add article
@app.route("/addarticle", methods = ["GET", "POST"])
@login_required
def addarticle():
    form = addArticleForm(request.form)

    if request.method == 'POST' and form.validate():
        author = form.author.data
        title = form.title.data
        subtitle = form.subtitle.data
        content = form.content.data
        date_posted = datetime.now()
        username = session["username"]

        #blog adding db
        post = blogPost(title = title, subtitle = subtitle, author = author, username = username, date_posted = date_posted, content = content)
        db.session.add(post)
        db.session.commit()
        
        flash("Article is added", "success")
        return redirect(url_for('index'))

    return render_template("addarticle.html", form = form)


@app.route("/articles")
def articles():
    return render_template("articles.html")


#each post pages
@app.route("/post/<int:post_id>")
def post(post_id):
    post = blogPost.query.filter_by(id = post_id).first()
    if post: 
        return render_template("post.html", post = post)

    return render_template("post.html")


#delete post
@app.route("/delete/<int:post_id>")
@login_required
def deletePost(post_id):
    post = blogPost.query.filter_by(username = session["username"], id = post_id).first()
    if post:
        db.session.delete(post)
        db.session.commit()
        flash("Delete is success", "success")
        return redirect(url_for('dashboard'))

    flash("You are not authorized for this", "danger")
    return redirect(url_for('index'))


#edit post
@app.route("/edit/<int:post_id>",methods = ["GET","POST"])
@login_required
def editPost(post_id):
    post = blogPost.query.filter_by(username = session["username"], id = post_id).first()
    #get request
    if request.method == "GET":
        if post:
            form = addArticleForm()

            form.title.data = post.title
            form.subtitle.data = post.subtitle
            form.author.data = post.author
            form.content.data = post.content

            return render_template("edit.html", form = form)

        #not found or not own post
        else:
            flash("You are not authorized for this", "danger")
            return redirect(url_for('index'))

    #post request
    else:
        form = addArticleForm(request.form)

        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.author = form.author.data
        post.content = form.content.data

        db.session.commit()

        flash("Edit is success", "success")
        return redirect(url_for('dashboard'))


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
