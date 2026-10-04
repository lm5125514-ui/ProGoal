import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models import Product, ProductImage, Admin


load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не найден.")

DATABASE_URL = DATABASE_URL.replace(
    "postgres://",
    "postgresql://",
    1
)


# ==========================================
# SQLITE
# ==========================================

sqlite_engine = create_engine(
    "sqlite:///instance/progoal.db"
)

SQLiteSession = sessionmaker(bind=sqlite_engine)
sqlite_session = SQLiteSession()


# ==========================================
# POSTGRESQL
# ==========================================

postgres_engine = create_engine(DATABASE_URL)

PostgresSession = sessionmaker(bind=postgres_engine)
postgres_session = PostgresSession()


print("Подключаемся к PostgreSQL...")

with postgres_engine.connect() as connection:
    connection.execute(text("SELECT 1"))

print("Подключение успешно!")


# ==========================================
# СОЗДАНИЕ ТАБЛИЦ
# ==========================================

print("Создаём таблицы PostgreSQL...")

Product.metadata.create_all(postgres_engine)

print("Таблицы созданы.")


# ==========================================
# ОЧИСТКА ТОВАРОВ И АДМИНА
# ==========================================

print()
print("Очищаем товары и администраторов PostgreSQL...")

postgres_session.query(ProductImage).delete()
postgres_session.query(Product).delete()
postgres_session.query(Admin).delete()

postgres_session.commit()

print("Готово.")


# ==========================================
# ТОВАРЫ
# ==========================================

print()
print("Переносим товары...")

products = sqlite_session.query(Product).order_by(Product.id).all()

print(f"Найдено товаров: {len(products)}")

for old_product in products:

    new_product = Product(
        id=old_product.id,
        name=old_product.name,
        category=old_product.category,
        brand=old_product.brand,
        price=old_product.price,
        description=old_product.description,
        image=old_product.image
    )

    postgres_session.add(new_product)

    print(
        f"  [{old_product.id}] "
        f"{old_product.name}"
    )

postgres_session.commit()


# ==========================================
# ФОТОГРАФИИ
# ==========================================

print()
print("Переносим фотографии...")

images = sqlite_session.query(ProductImage).order_by(
    ProductImage.id
).all()

print(f"Найдено фотографий: {len(images)}")

for old_image in images:

    new_image = ProductImage(
        id=old_image.id,
        product_id=old_image.product_id,
        filename=old_image.filename,
        is_main=old_image.is_main
    )

    postgres_session.add(new_image)

postgres_session.commit()


# ==========================================
# АДМИНИСТРАТОРЫ
# ==========================================

print()
print("Переносим администраторов...")

admins = sqlite_session.query(Admin).order_by(Admin.id).all()

print(f"Найдено администраторов: {len(admins)}")

for old_admin in admins:

    new_admin = Admin(
        id=old_admin.id,
        username=old_admin.username,
        password=old_admin.password
    )

    postgres_session.add(new_admin)

    print(
        f"  [{old_admin.id}] "
        f"{old_admin.username}"
    )

postgres_session.commit()


# ==========================================
# ПРОВЕРКА
# ==========================================

print()
print("=" * 50)
print("ПРОВЕРКА МИГРАЦИИ")
print("=" * 50)

print(
    f"Товаров: "
    f"{postgres_session.query(Product).count()}"
)

print(
    f"Фотографий: "
    f"{postgres_session.query(ProductImage).count()}"
)

print(
    f"Администраторов: "
    f"{postgres_session.query(Admin).count()}"
)

print(
    f"Заказов: 0"
)

print(
    f"Позиций заказов: 0"
)

print("=" * 50)
print("МИГРАЦИЯ ЗАВЕРШЕНА!")


sqlite_session.close()
postgres_session.close()