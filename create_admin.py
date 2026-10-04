from flask import Flask
from werkzeug.security import generate_password_hash
from getpass import getpass

from database import db
from models import Admin


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///progoal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


with app.app_context():

    db.create_all()

    existing_admin = Admin.query.filter_by(
        username="admin"
    ).first()

    if existing_admin:

        print("Администратор уже существует.")

    else:

        password = getpass(
            "Введите пароль администратора: "
        )

        if len(password) < 8:

            print(
                "Ошибка: пароль должен содержать "
                "минимум 8 символов."
            )

        else:

            admin = Admin(
                username="admin",
                password=generate_password_hash(password)
            )

            db.session.add(admin)
            db.session.commit()

            print("Администратор успешно создан!")
            print("Логин: admin")