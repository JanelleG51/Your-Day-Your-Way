import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import cloudinary.api
if os.path.exists("env.py"):
    import env


app = Flask(__name__)
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")

cloudinary_url = (
    'https://res.cloudinary.com/your-day-your-way/image/upload/user_images')

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")


mongo = PyMongo(app)

# Login Required Decorator
# Credit: https://flask.palletsprojects.com/en/2.0.x/patterns/viewdecorators/#login-required-decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please login to access this content")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@app.route("/landing")
def landing_page():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(register)

        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome back, {}".format(request.form.get("username")))
                return redirect(url_for("planner", username=session["user"]))
            else:
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/planner")
@login_required
def planner():
    meals = mongo.db.meals.find().sort("_id", -1).limit(3)
    workouts = mongo.db.workouts.find().sort("_id", -1).limit(1)
    return render_template("planner.html", meals=meals, workouts=workouts)


@app.route("/meals")
@login_required
def meals():
    meals = list(mongo.db.meals.find())
    return render_template("meals.html", meals=meals)


@app.route("/search", methods=["GET", "POST"])
def search_meals():
    query = request.form.get("query")
    meals = list(mongo.db.meals.find({"$text": {"$search": query}}))
    return render_template("meals.html", meals=meals)


@app.route("/workouts")
@login_required
def workouts():
    workouts = list(mongo.db.workouts.find())
    return render_template("workouts.html", workouts=workouts)


@app.route("/search", methods=["GET", "POST"])
def search_workouts():
    query = request.form.get("query")
    workouts = list(mongo.db.workouts.find({"$text": {"$search": query}}))
    return render_template("workouts.html", workouts=workouts)


@app.route("/logout")
@login_required
def logout():
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/profile/<username>", methods=["GET", "POST"])
@login_required
def profile(username):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    if session["user"]:
        return render_template("profile.html", username=username)

    return redirect(url_for("login"))


@app.route("/add_meal", methods=["GET", "POST"])
@login_required
def add_meal():
    if request.method == "POST":
        ingredients = request.form.getlist("ingredients")
        ingredients_list = []
        for ingredient in ingredients:
            ingredients_list.append(ingredient)
        method = request.form.getlist("method")
        method_list = []
        for step in method:
            method_list.append(step)
        meal = {
            "meal_category": request.form.get("meal_category"),
            "image_url": request.form.get("image_url"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_url": request.form.get("recipe_url"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "servings": request.form.get("servings"),
            "ingredients": ingredients_list,
            "method": method_list,
            "created_by": session["user"]
        }

        mongo.db.meals.insert_one(meal)
        flash("Meal Sucessfully Added")
        return redirect(url_for("meals"))

    meal_categories = mongo.db.meal_categories.find().sort("meal_category", 1)
    return render_template("add_meal.html", meal_categories=meal_categories)


@app.route("/add_workout", methods=["GET", "POST"])
@login_required
def add_workout():
    if request.method == "POST":
        workout_steps = request.form.getlist("workout_steps")
        workout_list = []
        for step in workout_steps:
            workout_list.append(step)
        workout = {
            "workout_category": request.form.get("workout_category"),
            "wo_image_url": request.form.get("wo_image_url"),
            "workout_title": request.form.get("workout_title"),
            "workout_url": request.form.get("workout_url"),
            "workout_level": request.form.get("workout_level"),
            "workout_location": request.form.get("workout_location"),
            "workout_duration": request.form.get("workout_duration"),
            "sets": request.form.get("sets"),
            "workout_steps": workout_list,
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


@app.route("/edit_meal/<meal_id>", methods=["GET", "POST"])
@login_required
def edit_meal(meal_id):
    if request.method == "POST":
        submit = {
            "meal_category": request.form.get("meal_category"),
            "image_url": request.form.get("image_url"),
            "recipe_name": request.form.get("recipe_name"),
            "recipe_url": request.form.get("recipe_url"),
            "prep_time": request.form.get("prep_time"),
            "cook_time": request.form.get("cook_time"),
            "servings": request.form.get("servings"),
            "ingredients": request.form.get("ingredients"),
            "method": request.form.getlist("method"),
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
    if request.method == "POST":
        submit_wo = {
            "workout_category": request.form.get("workout_category"),
            "wo_image_url": request.form.get("wo_image_url"),
            "workout_title": request.form.get("workout_title"),
            "workout_url": request.form.get("workout_url"),
            "workout_level": request.form.get("workout_level"),
            "workout_location": request.form.get("workout_location"),
            "workout_duration": request.form.get("workout_duration"),
            "sets": request.form.get("sets"),
            "workout_steps": request.form.getlist("workout_steps"),
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
    mongo.db.meals.remove({"_id": ObjectId(meal_id)})
    flash("Meal Sucessfully Deleted")
    return redirect(url_for("meals"))


@app.route("/delete_workout/<workout_id>")
@login_required
def delete_workout(workout_id):
    mongo.db.workouts.remove({"_id": ObjectId(workout_id)})
    flash("Workout Sucessfully Deleted")
    return redirect(url_for("workouts"))


@app.route("/full_recipe/<meal_id>")
def full_recipe(meal_id):
    meal = mongo.db.meals.find_one({"_id": ObjectId(meal_id)})
    return render_template("full_recipe.html", meal=meal)


@app.route("/full_workout/<workout_id>")
def full_workout(workout_id):
    workout = mongo.db.workouts.find_one({"_id": ObjectId(workout_id)})
    return render_template("full_workout.html", workout=workout)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
