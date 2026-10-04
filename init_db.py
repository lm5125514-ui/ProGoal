from flask import Flask

from database import db
from models import Product


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///progoal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


products = [
    Product(
        name="Форма ProGoal Elite",
        category="Футбольная форма",
        brand="ProGoal",
        price=4990,
        description="Футболка и шорты для тренировок и матчей."
    ),

    Product(
        name="Форма Team 2026",
        category="Футбольная форма",
        brand="ProGoal",
        price=6990,
        description="Современный комплект футбольной формы."
    ),

    Product(
        name="Бутсы Speed X",
        category="Бутсы",
        brand="Adidas",
        price=9990,
        description="Лёгкие бутсы для быстрого футбола."
    ),

    Product(
        name="Бутсы Phantom Pro",
        category="Бутсы",
        brand="Nike",
        price=12490,
        description="Профессиональная модель для игроков."
    ),

    Product(
        name="Мяч Pro Match",
        category="Мячи",
        brand="Adidas",
        price=5490,
        description="Мяч для тренировок и соревнований."
    ),

    Product(
        name="Мяч ProGoal Competition",
        category="Мячи",
        brand="ProGoal",
        price=3990,
        description="Универсальный футбольный мяч."
    ),

    Product(
        name="Перчатки GK Pro",
        category="Вратарская экипировка",
        brand="ProGoal",
        price=4490,
        description="Вратарские перчатки с усиленной защитой."
    ),

    Product(
        name="Щитки Football Guard",
        category="Аксессуары",
        brand="Adidas",
        price=2490,
        description="Лёгкие защитные щитки."
    ),

    Product(
        name="Сумка ProGoal",
        category="Аксессуары",
        brand="ProGoal",
        price=4290,
        description="Вместительная спортивная сумка."
    )
]


with app.app_context():

    db.create_all()

    existing_products = Product.query.count()

    if existing_products == 0:
        db.session.add_all(products)
        db.session.commit()

        print("Товары успешно добавлены!")

    else:
        print("Товары уже существуют в базе данных.")