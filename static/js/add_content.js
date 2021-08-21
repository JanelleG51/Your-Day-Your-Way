// credit to https://github.com/Brianconn71/ms3-recipedia/blob/master/static/js/add_recipe.js
/*jshint esversion: 6 */

let ingred = 1;
let max_ingred = 15;

$(".add_ingredient").click(function (e) {
    e.preventDefault();
    if (ingred < max_ingred) {
        ingred++;
        $(".ingredient_list").append(`
        <div class="input-field col s12">
        <i class=""></i>
        <input id="ingredients${ingred}" name="ingredients" minlength="2" maxlength="60" type="text" class="validate" required>
        <label for="ingredients${ingred}">Ingredient ${ingred}:</label>
        <a type="button" class="btn-small red darken-4 remove_ingredient"><i class=""></i>Remove</a></div>`);
    }
});

let step = 1;
let max_steps = 15

$(".add_step").click(function (e) {
    e.preventDefault();
    if (step < max_steps) {
        step++;
        $(".method_list").append(`
        <div class="input-field col s12">
        <i class=""></i>
        <input id="method${step}" name="method" minlength="3" maxlength="500" type="text" class="validate" required>
        <label for="method${step}">Step ${step}:</label>
        <a class="btn-small red darken-4 remove_step"><i class=""></i>Remove</a></div>`);
        $(".workout_list").append(`
        <div class="input-field col s12">
        <i class=""></i>
        <input id="workout_steps${step}" name="workout_steps" minlength="3" maxlength="500" type="text" class="validate" required>
        <label for="workout_steps${step}">Step ${step}:</label>
        <a class="btn-small red darken-4 remove_step"><i class=""></i>Remove</a></div>`);
    }
});

$("body").on('click', ".remove_ingredient", function () {
    $(this).parent('div').remove();
    ingred--;
});

$("body").on('click', ".remove_step", function () {
    $(this).parent('div').remove();
    step--;
});