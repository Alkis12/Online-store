from flask import Flask, render_template, redirect, request, make_response, session, abort
from flask_login import LoginManager, logout_user, login_required, login_user, current_user # импортируем всякие нужные штуки из Фласк
from data import db_session
from data.products import Products
from data.users import User # импортируем классы Пользователя и Продуктов
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, BooleanField, FloatField, FileField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired  # импортируем валидаторы

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app) # все необходимые операции с секретным ключом


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    is_provider = BooleanField('Поставщик')
    submit = SubmitField('Войти') # класс формы регистрации


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти') # класс формы входа


class ProductsForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    price = FloatField('Цена', validators=[DataRequired()])
    description = TextAreaField("Описание")
    submit = SubmitField('Применить') # класс добавления/редактирования продукта


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id) # загрузка пользователя


@app.route("/account")
def account():
    return render_template("account.html") # страница пользователя (его аккаунт)


@app.route("/")
def index():
    session = db_session.create_session()
    products = session.query(Products)
    return render_template("index.html", products=products) # переход на Главную с импортом списка продуктов


@app.route("/basket") # функция перехода в корзину; подсчет цены всех заказанных товаров и цены с бонусами
def basket():
    session = db_session.create_session()
    products = session.query(Products)
    if current_user.is_authenticated:
        if current_user.basket:
            basket_ = [int(i) for i in current_user.basket.split()] # список товаров в корзине
        else:
            basket_ = []
        price = 0
        for i in basket_:
            price += session.query(Products).filter(Products.id == i).first().price # суммируем цену
        if current_user.is_vip: # учитываем вип
            price *= 0.8
        if current_user.bonuses >= 500: # расчет бонуса от бонусов :)
            price_ = 0.5 * price
        else:
            price_ = (1 - current_user.bonuses / 1000) * price
    else:
        basket_ = '' # ну а иначе ничего нет, просто чтобы не ломалось
        price = 0
        price_ = 0
    return render_template("basket.html", products=products, basket=basket_, price=price, price_=price_)


@app.route("/clicker")
def clicker():
    if str(current_user) == 'real': # только если пользователь вошел в аккаунт!!!
        session = db_session.create_session()
        current_user.bonuses += 0.1 # каждый вход на эту страницу добавляет 0.1 бонус
        session.merge(current_user)
        session.commit()
    return render_template("bot.html")


@app.route("/money") # чит-функция, +50 рублей. Ну что тут еще сказать
def money():
    session = db_session.create_session()
    current_user.money += 50
    session.merge(current_user)
    session.commit()
    return redirect('/account')


@app.route("/basket_buy")
def buy(): # функция обработки покупки из корзины БЕЗ бонусов
    session = db_session.create_session()
    products = session.query(Products)
    if str(current_user) != 'real': # если пользователь не в аккаунте, протокол "Взлом через поисковую строку"
        return render_template("troll.html")
    basket_ = [int(i) for i in current_user.basket.split()]
    price = 0
    for i in basket_: # генерируем цену
        price += session.query(Products).filter(Products.id == i).first().price
    if current_user.is_vip:
        price *= 0.8
    if price > current_user.money: # нет денег
        return redirect('/not_enough')
    current_user.money -= price
    current_user.basket = ''
    session.merge(current_user)
    session.commit()
    return render_template("buy.html", products=products, flag=True) # успешная покупка


@app.route("/basket_buy_with_bonuses")
def buy_with_bonuses(): # все как в прошлой функции но с бонусами
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
def vip(): # просто покупка ВИПа за 500 рублей
    session = db_session.create_session()
    if str(current_user) != 'real': # если пользователь не в аккаунте, протокол "Взлом через поисковую строку"
        return render_template("troll.html")
    if current_user.money >= 500:
        current_user.money -= 500
        current_user.is_vip = True
    else:
        return redirect('/not_enough')
    session.merge(current_user)
    session.commit()
    return redirect('/account')


@app.route("/not_enough")
def not_enough(): # нет денег(
    return render_template('not_enough.html')


@app.route('/register', methods=['GET', 'POST'])
def reqister(): # страница регистрации, проверка паролей, неинтересно
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
                                   message="Такой пользователь уже есть") # все видно по сообщениям
        user = User( # создаем пользователя
            email=form.email.data,
            name=form.name.data,
            surname=form.surname.data,
            is_provider=form.is_provider.data
        )
        user.set_password(form.password.data)
        session.add(user) # добавляем его в базу и живем счастливо
        session.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login(): # вход в аккаунт, проверка пользователя, неинтересно
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
    return render_template('login.html', title='Авторизация', form=form) # пароли, логины, сверяем с БД и все


@app.route('/logout')
@login_required
def logout(): # выход из аккаунта
    session = db_session.create_session()
    logout_user()
    return redirect("/")


@app.route('/products', methods=['GET', 'POST'])
@login_required
def add_products(): # добавление продукта в список продуктов
    form = ProductsForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        products = Products()
        products.title = form.title.data
        products.price = form.price.data
        products.description = form.description.data # все поля класса
        products.user = current_user
        current_user.products.append(products)
        session.merge(current_user)
        session.commit()
        return redirect('/')
    return render_template('products.html', title='Добавление товара',
                           form=form)


@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_products(id): # редактирование продукта
    form = ProductsForm()
    if request.method == "GET": # если запрос ГЕТ...
        session = db_session.create_session()
        products = session.query(Products).filter(Products.id == id,
                                                  Products.user == current_user).first()
        if products:
            products.title = form.title.data
            products.price = form.price.data # все поля класса
            products.description = form.description.data
        else:
            abort(404) # нет продуктов, а редактируют..... что-то не так!!!
    if form.validate_on_submit(): # ...или после согласия валидаторов
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
def products(id): # добавление продукта в корзину!!!
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
def product_delete(id): # удаление продукта отовсюду
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
def basket_delete(id): # удаление продукта из корзины
    session = db_session.create_session()
    s = current_user.basket.split()
    if str(id) in s:
        s.remove(str(id))
        current_user.basket = ' '.join(s)
    session.merge(current_user)
    session.commit()
    return redirect('/basket')


if __name__ == '__main__': # ну это и так ясно
    db_session.global_init("db/online-store.sqlite")
    app.run(port=8080, host='127.0.0.1')
