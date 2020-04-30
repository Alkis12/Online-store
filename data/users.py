import datetime
import sqlalchemy
import sqlalchemy.orm as orm
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    email = sqlalchemy.Column(sqlalchemy.String,
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    money = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    bonuses = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    basket = sqlalchemy.Column(sqlalchemy.String)
    is_provider = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    is_vip = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    products = orm.relation('Products')

    def bonus(self):
        return self.bonuses

    def __repr__(self):
        # return f'<User> {self.email} {self.name} {self.surname} {self.money} рублей; {self.bonuses} бонусов'
        return 'real'

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
