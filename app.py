import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from datetime import datetime
from flask_mail import Mail, Message
from bson.objectid import ObjectId
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import cloudinary.api
if os.path.exists("env.py"):
    import env


app = Flask(__name__)


app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")


mongo = PyMongo(app)


cloudinary.config(
    cloud_name=os.environ.get("CLOUD_NAME"),
    api_key=os.environ.get("API_KEY"),
    api_secret=os.environ.get("API_SECRET")
)


app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT')
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)
site_email = "ydywplanner@gmail.com"


# Login Required Decorator Credit:
# https://flask.palletsprojects.com/en/2.0.x/patterns/viewdecorators/login-required-decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please login to access this content")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@app.route("/home")
def home():
    """
    Grab current date and time and display on the home screen.
    Displays 3 workouts and 3 meals from the DB.
    Only registered users can edit or delete but all can rate.
    """
    date = datetime.today().strftime('%A - %D')
    workouts = mongo.db.workouts.find().sort("_id", -1).limit(3)
    meals = mongo.db.meals.find().sort("_id", -1).limit(3)
    return render_template("home.html", workouts=workouts,
                           meals=meals, date=date)


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Checks DB to see if there are any existing users or passwords.
    If yes, user are notified they must select another.
    On pass, user is entered in to DB and a session cookie.

    """
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "email": request.form.get("email").lower(),
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),

        }

        mongo.db.users.insert_one(register)

        session["user"] = request.form.get("username").lower()
        flash("Success! Why not begin adding some content?!")
        return redirect(url_for("meals"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Check the database for existing username and password.
    Validates the two match, if yes, user is logged into site.
    If either one is incorrect the user is notified that either
    or are incorrect.
    """
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome back, {}".format(request.form.get("username")))
                return redirect(url_for("profile", username=session["user"]))
            else:
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/meals")
@login_required
def meals():
    """
    Gets the list of all meals in the DB and render them on screen.
    Takes index of meals and accessed the ratings field,
    divides the ratings by number in arrays and returns the average
    """
    meals = list(mongo.db.meals.find())

    for i in range(len(meals)):
        meals[i]['ratings'] = round(
            sum(meals[i]['ratings']) / len(meals[i]['ratings']), 2)
    return render_template("meals.html", meals=meals)


@app.route("/search", methods=["GET", "POST"])
def search_meals():
    """
    Accesses the defined text indexes through the search
    and returns all results containing the search term
    """
    query = request.form.get("query")
    meals = list(mongo.db.meals.find({"$text": {"$search": query}}))
    return render_template("meals.html", meals=meals)


@app.route("/workouts")
@login_required
def workouts():
    """
    Gets the list of all meals in the DB and render them on screen.
    Takes index of meals and accessed the ratings field,
    divides the ratings by number in arrays and returns the average
    """
    workouts = list(mongo.db.workouts.find())

    for i in range(len(workouts)):
        workouts[i]['ratings'] = round(
            sum(workouts[i]['ratings']) / len(workouts[i]['ratings']), 2)
    return render_template("workouts.html", workouts=workouts)


@app.route("/logout")
@login_required
def logout():
    """
    When requested, using the log out button,
    the user is removed from their cookie session

    """
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/profile/<username>", methods=["GET", "POST"])
@login_required
def profile(username):
    """
    Renders the day and date to the users profile
    along with all of their DB entries
    """
    date = datetime.today().strftime('%A - %D')
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    meals = list(mongo.db.meals.find())
    workouts = list(mongo.db.workouts.find())

    if session["user"]:
        return render_template("profile.html", username=username, meals=meals,
                               workouts=workouts, date=date)

    return redirect(url_for("login"))


@app.route("/add_meal", methods=["GET", "POST"])
@login_required
def add_meal():
    """
    Allows users to add all meal information as well as
    upload their own images using Cloudinary API
    and add ratings to all meals.
    The instance is then inserted into the DB
    """
    if request.method == "POST":
        ingredients = request.form.getlist("ingredients")
        ingredients_list = []
        for ingredient in ingredients:
            ingredients_list.append(ingredient)
        method = request.form.getlist("method")
        method_list = []
        for step in method:
            method_list.append(step)
        image = request.files['image_url']
        image_upload = cloudinary.uploader.upload(image)
        meal = {
            "meal_category": request.form.get("meal_category"),
            "image_url": image_upload['secure_url'],
            "recipe_name": request.form.get("recipe_name"),
            "recipe_url": request.form.get("recipe_url"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "servings": request.form.get("servings"),
            "ingredients": ingredients_list,
            "method": method_list,
            "ratings": [int(request.form.get('ratings'))],
            "created_by": session["user"]
        }

        mongo.db.meals.insert_one(meal)
        flash("Meal Sucessfully Added")
        return redirect(url_for("meals"))

    meal_categories = mongo.db.meal_categories.find().sort("meal_category", 1)
    return render_template("add_meal.html", meal_categories=meal_categories)


@app.route("/rate_meal/<meal_id>", methods=["GET", "POST"])
def rate_meal(meal_id):
    """
    Once a meal has been added with the user's intial rating,
    others are then able to rate each meal which is then
    added to that specific objectid in the DB
    and the rating score is updated
    """

    if request.method == "POST":
        meal = mongo.db.meals.find_one({"_id": ObjectId(meal_id)})
        meal['ratings'].append(int(request.form.get("add_rating")))

        mongo.db.meals.update_one({"_id": ObjectId(meal_id)},
                                  {"$set": meal})
    return redirect(url_for("meals"))


@app.route("/add_workout", methods=["GET", "POST"])
@login_required
def add_workout():
    """
    Allows users to add all workout information as well as
    upload their own images using Cloudinary API
    and add ratings to all workouts.
    The instance is then inserted into the DB
    """
    if request.method == "POST":
        workout_steps = request.form.getlist("workout_steps")
        workout_list = []
        for step in workout_steps:
            workout_list.append(step)
        image = request.files['wo_image_url']
        image_upload = cloudinary.uploader.upload(image)
        workout = {
            "workout_category": request.form.get("workout_category"),
            "wo_image_url": image_upload['secure_url'],
            "workout_title": request.form.get("workout_title"),
            "workout_url": request.form.get("workout_url"),
            "workout_level": request.form.get("workout_level"),
            "workout_location": request.form.get("workout_location"),
            "workout_duration": request.form.get("workout_duration"),
            "sets": request.form.get("sets"),
            "workout_steps": workout_list,
            "ratings": [int(request.form.get('ratings'))],
            "created_by": session["user"]
        }

        mongo.db.workouts.insert_one(workout)
        flash("Workout Sucessfully Added")
        return redirect(url_for("workouts"))

    workout_categories = mongo.db.workout_categories.find().sort(
        "workout_category", 1)
    workout_levels = mongo.db.workout_levels.find().sort("workout_level", 1)
    workout_locations = mongo.db.workout_locations.find().sort(
        "workout_location", 1)
    return render_template(
        "add_workout.html", workout_categories=workout_categories,
        workout_levels=workout_levels, workout_locations=workout_locations)


@app.route("/rate_workout/<workout_id>", methods=["GET", "POST"])
def rate_workout(workout_id):
    """
    Once a workout has been added with the user's intial rating,
    others are then able to rate each workout which is then
    added to that specific objectid in the DB
    and the rating score is updated
    """

    if request.method == "POST":
        workout = mongo.db.workouts.find_one({"_id": ObjectId(workout_id)})
        workout['ratings'].append(int(request.form.get("add_rating")))

        mongo.db.workouts.update_one({"_id": ObjectId(workout_id)},
                                     {"$set": workout})
    return redirect(url_for("workouts"))


@app.route("/edit_meal/<meal_id>", methods=["GET", "POST"])
@login_required
def edit_meal(meal_id):
    """
    Accesses the existing entry in the DB and sends any update
    request the user makes
    """
    if request.method == "POST":
        ingredients = request.form.getlist("ingredients")
        ingredients_list = []
        for ingredient in ingredients:
            ingredients_list.append(ingredient)
        method = request.form.getlist("method")
        method_list = []
        for step in method:
            method_list.append(step)
        submit = {
            "meal_category": request.form.get("meal_category"),
            "image_url": request.form.get("image_url"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_url": request.form.get("recipe_url"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "servings": request.form.get("servings"),
            "ingredients": ingredients_list,
            "method": method_list,
            "ratings": [int(request.form.get('ratings'))],
            "created_by": session["user"]
        }

        mongo.db.meals.update({"_id": ObjectId(meal_id)}, submit)
        flash("Meal Sucessfully Updated")

    meal = mongo.db.meals.find_one({"_id": ObjectId(meal_id)})
    meal_categories = mongo.db.meal_categories.find().sort("meal_category", 1)
    return render_template(
        "edit_meal.html", meal=meal, meal_categories=meal_categories)


@app.route("/edit_workout/<workout_id>", methods=["GET", "POST"])
@login_required
def edit_workout(workout_id):
    """
    Accesses the existing entry in the DB and sends any update
    request the user makes
    """
    if request.method == "POST":
        workout_steps = request.form.getlist("workout_steps")
        workout_list = []
        for step in workout_steps:
            workout_list.append(step)
        submit_wo = {
            "workout_category": request.form.get("workout_category"),
            "wo_image_url": request.form.get("wo_image_url"),
            "workout_title": request.form.get("workout_title"),
            "workout_url": request.form.get("workout_url"),
            "workout_level": request.form.get("workout_level"),
            "workout_location": request.form.get("workout_location"),
            "workout_duration": request.form.get("workout_duration"),
            "sets": request.form.get("sets"),
            "workout_steps": workout_list,
            "ratings": [int(request.form.get('ratings'))],
            "created_by": session["user"]
        }

        mongo.db.workouts.update({"_id": ObjectId(workout_id)}, submit_wo)
        flash("Workout Sucessfully Updated")
        return redirect(url_for("workouts"))

    workout = mongo.db.workouts.find_one({"_id": ObjectId(workout_id)})
    workout_categories = mongo.db.workout_categories.find().sort(
        "workout_category", 1)
    workout_levels = mongo.db.workout_levels.find().sort("workout_level", 1)
    workout_locations = mongo.db.workout_locations.find().sort(
        "workout_location", 1)
    return render_template(
        "edit_workout.html", workout=workout,
        workout_categories=workout_categories,
        workout_levels=workout_levels, workout_locations=workout_locations)


@app.route("/delete_meal/<meal_id>")
@login_required
def delete_meal(meal_id):
    """
    Accesses the objectid the user would like to delete
    and on confirmation, removes the item from the DB
    """
    mongo.db.meals.remove({"_id": ObjectId(meal_id)})
    flash("Meal Sucessfully Deleted")
    return redirect(url_for("meals"))


@app.route("/delete_workout/<workout_id>")
@login_required
def delete_workout(workout_id):
    """
    Accesses the objectid the user would like to delete
    and on confirmation, removes the item from the DB
    """
    mongo.db.workouts.remove({"_id": ObjectId(workout_id)})
    flash("Workout Sucessfully Deleted")
    return redirect(url_for("workouts"))


@app.route("/full_recipe/<meal_id>")
def full_recipe(meal_id):
    """
    While display cards only show limited information 
    the full recipe link displays all contect and 
    associated actions for the meal
    """
    meal = mongo.db.meals.find_one({"_id": ObjectId(meal_id)})
    return render_template("full_recipe.html", meal=meal)


@app.route("/full_workout/<workout_id>")
def full_workout(workout_id):
    """
    While display cards only show limited information, 
    the full workout link displays all contect and 
    associated actions for the meal
    """
    workout = mongo.db.workouts.find_one({"_id": ObjectId(workout_id)})
    return render_template("full_workout.html", workout=workout)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    When a user contacts the site using the conact form
    an email is sent from Flak Mail to both the admin
    and the user with the users message displayed 
    in the body of the email 
    """
    if request.method == "POST":
        email = request.form.get("email")
        message_field = request.form.get("message-field")
        msg = Message('We have your message!',
                      html=('<p> Thank you for reaching out to us '
                            'with your message: </p>'
                            '<br>'
                            '<p> %s </p>'
                            '<br>'
                            '<p>We will get back to you as soon as we can.</p>'
                            '<br>'
                            '<p>We hope you are enjoying your day!</p>'
                            '<br>'
                            '<p>The Team at Your Day Your Way'
                            % message_field),
                      sender=site_email,
                      cc=[email],
                      recipients=[site_email])
        mail.send(msg)

        flash("Thank you for contacting us. Your message is on its way!")
    return render_template("contact.html")


"""
Site error handlers to ensure
any errors are graciously dealt with 
"""


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
