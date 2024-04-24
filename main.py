from flask import (
    Flask,
    render_template,
    url_for,
    request,
    Blueprint,
    flash,
    g,
    redirect,
    session,
)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from werkzeug.exceptions import abort
import os
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditorField, CKEditor
from functools import wraps
import pytz
import datetimeformat
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from sqlalchemy.orm import exc

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI", "sqlite:///site.db")
db = SQLAlchemy(app)
Bootstrap5(app)
ckeditor = CKEditor(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


class CreatePostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    bg_img = StringField("Background Image URL", validators=[DataRequired()])
    content = CKEditorField("Content", validators=[DataRequired()])
    submit = SubmitField("Submit")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    ### Columns
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    username = db.Column(db.String(100))
    ### Relationships
    posts = db.relationship("Post", back_populates="author")
    comments = db.relationship("Comment", back_populates="comment_author")


class Post(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    ### Columns
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date_posted = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(tz=pytz.timezone("Asia/Ho_Chi_Minh")),
    )
    content = db.Column(db.Text, nullable=False)
    bg_img = db.Column(db.String(250), nullable=False)
    ### ForeignKey
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    ### Relationships
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    ### Columns
    text = db.Column(db.Text, nullable=False)
    date_posted = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(tz=pytz.timezone("Asia/Ho_Chi_Minh")),
    )
    ### ForeignKey
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    ### Relationships
    comment_author = db.relationship("User", back_populates="comments")
    parent_post = db.relationship("Post", back_populates="comments")


with app.app_context():
    db.create_all()  # this create the site.db


@app.before_request
def load_user():
    if "user_id" in session:
        user = User.query.filter_by(id=session["user_id"]).first()
    else:
        session.pop("user_id", None)  # Remove user_id from session
        user = None  # Set current user to None

    g.user = user


@app.route("/")
def index():
    return render_template("index.html", current_user=g.user)


@app.route("/login", methods=["GET", "POST"])
def login():
    load_user()
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Login successful
            session["user_id"] = user.id  # Set the user id in the session
            g.user = user  # Update g.user with the logged-in user
            all_posts = Post.query.all()
            num_posts = Post.query.count()  # Count the number of posts in the database
            return render_template(
                "home.html", current_user=g.user, posts=all_posts, num_posts=num_posts
            )
        else:
            flash("Invalid email or password")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        # Check if the email or username already exists in the database
        existing_user = User.query.filter(
            (User.username == name) | (User.email == email)
        ).first()
        if existing_user:
            # If an existing user is found with the same email or username, flash a message
            flash("An account with this email or username already exists.")
            return render_template("register.html")
        if password != confirm_password:
            flash("The password confirmation does not match.")
        else:
            ### Hash
            hashed_password = generate_password_hash(password)
            ### Save to database
            new_user = User(username=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("register.html", current_user=g.user)


@app.route("/home")
@login_required
def home():
    print(g.user)
    all_posts = Post.query.all()
    num_posts = Post.query.count()  # Count the number of posts in the database
    return render_template(
        "home.html", current_user=g.user, posts=all_posts, num_posts=num_posts
    )


@app.route("/about")
@login_required
def about():
    print(g.user)
    return render_template("about.html", current_user=g.user)


@app.route("/contact")
@login_required
def contact():
    print(g.user)
    return render_template("contact.html", current_user=g.user)


@app.route("/create-blog", methods=["GET", "POST"])
@login_required
def create_blog():
    print(g.user)
    form = CreatePostForm()
    if form.validate_on_submit():
        title = form.title.data
        subtitle = form.subtitle.data
        bg_img = form.bg_img.data
        content = form.content.data
        new_post = Post(
            title=title,
            subtitle=subtitle,
            bg_img=bg_img,
            content=content,
            author_id=g.user.id,
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("create_blog.html", form=form, current_user=g.user)


@app.route("/logout")
@login_required
def logout():
    session.pop("user_id", None)  # Remove user_id from session
    g.user = None  # Set current user to None
    flash("Logged out successfully.")
    return redirect(url_for("login"))


@app.route("/blog/<id>", methods=["GET", "POST"])
@login_required
def view_blog(id):
    # Fetch the post with the specified ID from the database
    post = Post.query.get(id)
    # Fetch all comments associated with the post
    comments = Comment.query.filter_by(post_id=id).all()
    if request.method == "POST":
        # Assuming you have a current user available (e.g., from Flask-Login)
        current_user = g.user
        # Extract comment details from the form
        text = request.form["comment"]
        # Create a new Comment object
        new_comment = Comment(text=text, comment_author=current_user, parent_post=post)
        # Add the new comment to the database session
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("view_blog", id=id))

    return render_template(
        "blog.html", current_user=g.user, post=post, comments=comments
    )


@app.route("/delete/<id>")
@login_required
def delete_blog(id):
    # Fetch the post with the specified ID from the database
    post = Post.query.get(id)
    if post:
        # Retrieve all comments associated with the post
        comments = Comment.query.filter_by(post_id=post.id).all()
        try:
            # Delete each comment
            for comment in comments:
                db.session.delete(comment)
            # Delete the post
            db.session.delete(post)
            # Commit the changes
            db.session.commit()
        except exc.FlushError:
            # Handle any potential errors
            db.session.rollback()
    return redirect(url_for("home"))


@app.route("/edit/<id>", methods=["GET", "POST"])
@login_required
def edit_blog(id):
    # Fetch the post with the specified ID from the database
    post = Post.query.get(id)
    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        bg_img=post.bg_img,
        content=post.content,
    )

    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.bg_img = form.bg_img.data
        post.content = form.content.data
        db.session.commit()  # Update the post in the database
        return redirect(url_for("home"))
    return render_template("edit.html", current_user=g.user, form=form)


if __name__ == "__main__":
    app.run(debug=True)
