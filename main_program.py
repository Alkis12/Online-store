from flask import Flask, render_template, redirect, request, make_response, session, abort
from flask_login import LoginManager, logout_user, login_required, login_user, current_user
from data import db_session
from data.products import Products
from data.users import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, FloatField, FileField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    is_provider = BooleanField('Поставщик')
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class ProductsForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired()])
    description = TextAreaField("Описание")
    submit = SubmitField('Применить')


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route("/account")
def account():
    return render_template("account.html")


@app.route("/")
def index():
    session = db_session.create_session()
    products = session.query(Products)
    return render_template("index.html", products=products)


@app.route("/basket")
def basket():
    session = db_session.create_session()
    products = session.query(Products)
    if current_user.is_authenticated:
        if current_user.basket:
            basket_ = [int(i) for i in current_user.basket.split()]
        else:
            basket_ = []
        price = 0
        for i in basket_:
            price += session.query(Products).filter(Products.id == i).first().price
        if current_user.is_vip:
            price *= 0.8
        if current_user.bonuses >= 500:
            price_ = 0.5 * price
        else:
            price_ = (1 - current_user.bonuses / 1000) * price
    else:
        basket_ = ''
        price = 0
        price_ = 0
    return render_template("basket.html", products=products, basket=basket_, price=price, price_=price_)


@app.route("/clicker")
def clicker():
    if str(current_user) == 'real':
        session = db_session.create_session()
        current_user.bonuses += 0.1
        session.merge(current_user)
        session.commit()
    return render_template("bot.html")


@app.route("/money")
def money():
    session = db_session.create_session()
    current_user.money += 50
    session.merge(current_user)
    session.commit()
    return redirect('/account')


@app.route("/basket_buy")
def buy():
    session = db_session.create_session()
    products = session.query(Products)
    if str(current_user) != 'real':
        return render_template("troll.html")
    basket_ = [int(i) for i in current_user.basket.split()]
    price = 0
    for i in basket_:
        price += session.query(Products).filter(Products.id == i).first().price
    if current_user.is_vip:
        price *= 0.8
    if price > current_user.money:
        return redirect('/not_enough')
    current_user.money -= price
    current_user.basket = ''
    session.merge(current_user)
    session.commit()
    return render_template("buy.html", products=products, flag=True)


@app.route("/basket_buy_with_bonuses")
def buy_with_bonuses():
    session = db_session.create_session()
    basket_ = [int(i) for i in current_user.basket.split()]
    price = 0
    for i in basket_:
        price += session.query(Products).filter(Products.id == i).first().price
    p = price
    if current_user.is_vip:
        price -= 0.2 * p
    if current_user.bonuses >= 500:
        current_user.bonuses -= 500
        price -= 0.5 * p
        if price > current_user.money:
            current_user.bonuses += 500
    else:
        price -= current_user.bonuses / 1000 * p
        if price >= current_user.money:
            current_user.bonuses = 0
    if price > current_user.money:
        return redirect('/not_enough')
    current_user.money -= price
    current_user.basket = ''
    session.merge(current_user)
    session.commit()
    return render_template("buy.html", basket=basket_)


@app.route("/vip")
def vip():
    session = db_session.create_session()
    if current_user.money >= 500:
        current_user.money -= 500
        current_user.is_vip = True
    else:
        return redirect('/not_enough')
    session.merge(current_user)
    session.commit()
    return redirect('/account')


@app.route("/not_enough")
def not_enough():
    return render_template('not_enough.html')


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            email=form.email.data,
            name=form.name.data,
            surname=form.surname.data,
            is_provider=form.is_provider.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    session = db_session.create_session()
    if form.validate_on_submit():
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    session = db_session.create_session()
    logout_user()
    return redirect("/")


@app.route('/products', methods=['GET', 'POST'])
@login_required
def add_products():
    form = ProductsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        products = Products()
        products.title = form.title.data
        products.price = form.price.data
        products.description = form.description.data
        products.user = current_user
        current_user.products.append(products)
        session.merge(current_user)
        session.commit()
        return redirect('/')
    return render_template('products.html', title='Добавление товара',
                           form=form)


@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_products(id):
    form = ProductsForm()
    if request.method == "GET":
        session = db_session.create_session()
        products = session.query(Products).filter(Products.id == id,
                                                  Products.user == current_user).first()
        if products:
            products.title = form.title.data
            products.price = form.price.data
            products.description = form.description.data
        else:
            abort(404)
    if form.validate_on_submit():
        session = db_session.create_session()
        products = session.query(Products).filter(Products.id == id,
                                                  Products.user == current_user).first()
        if products:
            products.title = form.title.data
            products.price = form.price.data
            session.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('products.html', title='Редактирование товара', form=form)


@app.route('/product/<int:id>', methods=['GET', 'POST'])
@login_required
def products(id):
    session = db_session.create_session()
    products = session.query(Products).filter(Products.id == id).first()
    if str(products.id) not in str(current_user.basket).split():
        if current_user.basket:
            current_user.basket = str(current_user.basket) + ' ' + str(products.id)
        else:
            current_user.basket = str(products.id)
    session.merge(current_user)
    session.commit()
    return redirect('/')


@app.route('/product_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def product_delete(id):
    session = db_session.create_session()
    products = session.query(Products).filter(Products.id == id,
                                              Products.user == current_user).first()
    if products:
        s = str(current_user.basket).split()
        if str(id) in s:
            s.remove(str(id))
            current_user.basket = ' '.join(s)
        session.delete(products)
        session.merge(current_user)
        session.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/basket_del/<int:id>', methods=['GET', 'POST'])
@login_required
def basket_delete(id):
    session = db_session.create_session()
    s = current_user.basket.split()
    s.remove(str(id))
    current_user.basket = ' '.join(s)
    session.merge(current_user)
    session.commit()
    return redirect('/basket')


if __name__ == '__main__':
    db_session.global_init("db/online-store.sqlite")
    app.run(port=8080, host='127.0.0.1')
